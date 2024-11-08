# kafka_streamer.py
import threading
import gi
import logging
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
        self.producer = KafkaProducer(bootstrap_servers=self.bootstrap_servers)
        self.device = None

    def start_stream(self, device='/dev/video0'):
        self.device = device
        self.running = True
        self.start()

    def run(self):
        Gst.init(None)
        # GStreamer 파이프라인 구성
        pipeline_str = f"""
            v4l2src device={self.device} !
            video/x-raw,framerate={self.frame_rate}/1,width={self.image_width},height={self.image_height} !
            jpegenc !
            appsink name=sink emit-signals=true max-buffers=1 drop=true
        """

        self.pipeline = Gst.parse_launch(pipeline_str)
        appsink = self.pipeline.get_by_name('sink')
        appsink.connect('new-sample', self.on_new_sample)

        self.pipeline.set_state(Gst.State.PLAYING)
        bus = self.pipeline.get_bus()

        while self.running:
            msg = bus.timed_pop_filtered(100 * Gst.MSECOND, Gst.MessageType.ERROR | Gst.MessageType.EOS)
            if msg:
                t = msg.type
                if t == Gst.MessageType.ERROR:
                    err, debug = msg.parse_error()
                    logger.error(f"Error: {err}, Debug info: {debug}")
                    self.running = False
                elif t == Gst.MessageType.EOS:
                    logger.info("End of stream")
                    self.running = False
                    break

        self.pipeline.set_state(Gst.State.NULL)

    def on_new_sample(self, sink):
        sample = sink.emit('pull-sample')
        buf = sample.get_buffer()
        data = buf.extract_dup(0, buf.get_size())
        # Kafka로 데이터 전송
        self.producer.send(self.topic, data)
        return Gst.FlowReturn.OK

    def stop_stream(self):
        self.running = False
        if self.pipeline:
            self.pipeline.send_event(Gst.Event.new_eos())
