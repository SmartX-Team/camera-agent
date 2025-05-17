# kafka_streamer.py
import threading
import gi
import logging
import time
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject
from kafka import KafkaProducer

logger = logging.getLogger(__name__)

class KafkaStreamer(threading.Thread):
    def __init__(self, topic, bootstrap_servers, frame_rate, image_width, image_height):
        super().__init__()
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        self.frame_rate = frame_rate
        self.image_width = image_width
        self.image_height = image_height
        self.running = False
        self.pipeline = None
        self.producer = None
        self.device = None
        self.loop = None
        self.thread = None


    def start_stream(self, device='/dev/video0'):
        self.device = device
        self.running = True
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self.run)
            self.thread.start()
            logger.info("KafkaStreamer thread started.")
        else:
            logger.warning("KafkaStreamer thread is already running.")

    def run(self):
        Gst.init(None)
        logger.info("GStreamer And Kafka initialized.")
        self.loop = GObject.MainLoop()
        self.initialize_producer()
        # GStreamer 파이프라인 구성
        pipeline_str = f"""
            v4l2src device={self.device} !
            videorate !
            video/x-raw,framerate={self.frame_rate}/1 !
            videoconvert !
            video/x-raw,format=BGR,width={self.image_width},height={self.image_height} !
            appsink name=sink emit-signals=true max-buffers=1 drop=true
        """

        logger.info(f"GStreamer pipeline: {pipeline_str}")
        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
        except Exception as e:
            logger.error(f"Failed to create GStreamer pipeline: {e}")
            return
        
        appsink = self.pipeline.get_by_name('sink')
        appsink.connect('new-sample', self.on_new_sample)

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        self.pipeline.set_state(Gst.State.PLAYING)
        ret, state, pending = self.pipeline.get_state(timeout=Gst.CLOCK_TIME_NONE)
        if state != Gst.State.PLAYING:
            logger.error(f"Failed to set pipeline to PLAYING state. Current state: {state}")
        else:
            logger.info("GStreamer pipeline set to PLAYING state.")
            
        try:
            self.loop.run()
        except Exception as e:
            logger.error(f"Error running main loop: {e}")
        finally:
            self.pipeline.set_state(Gst.State.NULL)
            if self.producer:
                self.producer.close()
            logger.info("KafkaStreamer stopped.")

    # 카프카 재연결 위해 만듬
    def initialize_producer(self):
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                retries=5,
                retry_backoff_ms=1000
            )
            logger.info("KafkaProducer created.")
        except Exception as e:
            logger.error(f"Failed to create KafkaProducer: {e}")
            self.producer = None

    def reinitialize_producer(self):
        try:
            if self.producer is not None:
                self.producer.close()
                logger.info("Closed existing KafkaProducer.")
            self.initialize_producer()
        except Exception as e:
            logger.error(f"Failed to reinitialize KafkaProducer: {e}")

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"GStreamer Error: {err}, {debug}")
            self.loop.quit()
        elif t == Gst.MessageType.EOS:
            logger.info("GStreamer End-Of-Stream reached")
            self.loop.quit()
        elif t == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            logger.warning(f"GStreamer Warning: {err}, {debug}")
        else:
            logger.debug(f"GStreamer message: {t}")
        return True

    def on_new_sample(self, sink):
        logger.debug("on_new_sample called.")
        try:
            sample = sink.emit('pull-sample')
            buf = sample.get_buffer()
            result, info = buf.map(Gst.MapFlags.READ)
            if result:
                data = info.data  # 바이트 데이터
                buf.unmap(info)
                logger.info(f"Extracted frame of size {len(data)} bytes.")
                # Kafka로 데이터 전송
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        future = self.producer.send(self.topic, data)
                        result = future.get(timeout=5.0)
                        logger.info(f"Sent frame to Kafka topic {self.topic}, result: {result}")
                        break  # 전송 성공 시 루프 탈출
                    except Exception as e:
                        logger.error(f"Failed to send frame to Kafka on attempt {attempt + 1}: {e}")
                        time.sleep(1)  # 재시도 전 대기
                        if attempt == max_retries - 1:
                            logger.info("Reinitializing KafkaProducer...")
                            self.reinitialize_producer()
                else:
                    logger.error("Exceeded maximum retries. Dropping frame.")
            else:
                logger.error("Failed to map buffer")
        except Exception as e:
            logger.error(f"Error in on_new_sample: {e}")
        return Gst.FlowReturn.OK


    def stop_stream(self):
        self.running = False
        if self.pipeline:
            self.pipeline.send_event(Gst.Event.new_eos())
            logger.info("Sent EOS event to pipeline.")
        if self.loop:
            self.loop.quit()
            logger.info("GObject MainLoop quit.")
        if self.thread:
            self.thread.join()
            logger.info("KafkaStreamer thread joined.")
            self.thread = None
