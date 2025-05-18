"""
과거에 테스트용으로 남겨둔 카프카 기반 스트리밍 제미나이 2.5 지원으로 공식 모드로 개선

250518 송인용


"""

# kafka_streamer.py
import threading
import gi
import logging
import time
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject
from kafka import KafkaProducer
import signal
import os


logger = logging.getLogger(__name__)

class KafkaStreamer(threading.Thread):
    def __init__(self):
        super().__init__()
        self.topic = os.environ.get('KAFKA_TOPIC', 'default_topic')
        raw_bootstrap_servers = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.bootstrap_servers = [s.strip() for s in raw_bootstrap_servers.split(',')] # 콤마로 구분된 서버 리스트 처리

        try:
            self.frame_rate = int(os.environ.get('CAMERA_FPS', os.environ.get('FRAME_RATE', 15))) # CAMERA_FPS 우선, 없으면 FRAME_RATE
            resolution_str = os.environ.get('CAMERA_RESOLUTION', f"{os.environ.get('IMAGE_WIDTH', 640)}x{os.environ.get('IMAGE_HEIGHT', 480)}")
            self.image_width, self.image_height = map(int, resolution_str.split('x'))
        except ValueError:
            logger.error(f"Invalid resolution/FPS environment variables. Using defaults.")
            self.frame_rate = 15
            self.image_width = 640
            self.image_height = 480
        
        self.device = os.environ.get('CAMERA_DEVICE', '/dev/video0')
        self.pipeline_str_format = f"""
            v4l2src device={self.device} !
            videorate ! video/x-raw,framerate={self.frame_rate}/1 !
            videoconvert ! video/x-raw,format=BGR,width={self.image_width},height={self.image_height} !
            appsink name=sink emit-signals=true max-buffers=1 drop=true
        """ # 기존 BGR 포맷 유지

        self.running = False
        self.pipeline = None
        self.producer = None
        self.loop = None
        self._thread = None # 내부 스레드 변수명 변경 (외부에서 직접 접근 방지)
        self._stop_event = threading.Event()

        # 깔끔한 shutdown을 위한 시그널 핸들러 등록
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum, frame):
        logger.warning(f"Signal {signum} received, initiating shutdown...")
        self.stop_stream()

    def start_stream(self): # device 파라미터 제거 (초기화 시 환경 변수에서 로드)
        if self.is_alive():
            logger.warning("KafkaStreamer thread is already running.")
            return False

        self._stop_event.clear() # 스레드 시작 전 이벤트 초기화
        self._thread = threading.Thread(target=self._run_loop, daemon=True) # 데몬 스레드로 변경 고려
        self._thread.start()
        logger.info(f"KafkaStreamer thread started for device {self.device} sending to topic {self.topic}.")
        return True

    def _run_loop(self): # 실제 스레드에서 실행될 메소드 (이름 변경)
        Gst.init(None)
        logger.info("GStreamer And Kafka initializing...")
        self.loop = GObject.MainLoop()
        
        if not self.initialize_producer(): # Producer 초기화 실패 시 종료
            logger.error("Failed to initialize Kafka producer. Stopping stream.")
            return

        pipeline_str = self.pipeline_str_format # 현재 설정으로 파이프라인 문자열 생성
        logger.info(f"GStreamer pipeline: {pipeline_str}")
        
        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
        except Exception as e:
            logger.error(f"Failed to create GStreamer pipeline: {e}")
            if self.producer: self.producer.close()
            return
        
        appsink = self.pipeline.get_by_name('sink')
        if not appsink:
            logger.error("Failed to get 'sink' from pipeline. Stopping stream.")
            self.pipeline.set_state(Gst.State.NULL)
            if self.producer: self.producer.close()
            return
        appsink.connect('new-sample', self.on_new_sample)

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        self.pipeline.set_state(Gst.State.PLAYING)
        # 상태 변경 확인 (약간의 타임아웃 허용)
        state_change_result = self.pipeline.get_state(timeout=5 * Gst.SECOND)[1] # Gst.CLOCK_TIME_NONE 대신 타임아웃
        if state_change_result != Gst.State.PLAYING:
            logger.error(f"Failed to set pipeline to PLAYING state. Current state: {state_change_result}")
        else:
            logger.info("GStreamer pipeline set to PLAYING state.")
            self.running = True # 파이프라인이 실제로 PLAYING 상태가 되면 running을 True로
        
        try:
            while not self._stop_event.is_set(): # 이벤트 플래그 확인
                 # GLib 메인 루프 컨텍스트를 주기적으로 반복하여 GStreamer 메시지 및 앱 싱크 콜백 처리
                context = self.loop.get_context()
                context.iteration(may_block=False) # Non-blocking iteration
                time.sleep(0.01) # CPU 사용량 줄이기 위해 짧은 sleep
            logger.info("Stop event received, exiting run loop.")
        except Exception as e:
            logger.error(f"Error running main loop: {e}")
        finally:
            self.running = False
            if self.pipeline:
                logger.info("Setting pipeline to NULL state.")
                self.pipeline.set_state(Gst.State.NULL)
            if self.producer:
                logger.info("Closing Kafka producer.")
                self.producer.close()
            if self.loop and self.loop.is_running(): # 루프가 실행 중일 때만 quit 호출
                 self.loop.quit()
            logger.info("KafkaStreamer run loop finished.")


    def initialize_producer(self): # 성공 여부 반환
        try:
            # 이전 producer가 있다면 명시적으로 닫기
            if self.producer:
                self.producer.close()
                logger.info("Closed existing KafkaProducer before reinitialization.")

            # Frame 크기 계산
            current_frame_size = self.image_width * self.image_height * 3
            producer_max_request_size = max(current_frame_size + 1024, 5 * 1024 * 1024) # 최소 5MB
            logger.info(f"KafkaStreamer [{self.device}]: Calculated current_frame_size: {current_frame_size} bytes")
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                retries=5, # Kafka 전송 재시도 횟수
                retry_backoff_ms=1000, # 재시도 간격
                # api_version_auto_timeout_ms=10000, # Kafka 브로커 버전 자동 감지 타임아웃 (필요시)
                # request_timeout_ms=30000, # 요청 타임아웃 (필요시)
                # linger_ms=10, # 배치 전송을 위한 대기 시간 (처리량 향상 목적)
                max_request_size=producer_max_request_size
            )
            logger.info(f"KafkaProducer created for servers: {self.bootstrap_servers}")
            return True
        except Exception as e:
            logger.error(f"Failed to create KafkaProducer: {e}")
            self.producer = None
            return False

    # def reinitialize_producer(self): # initialize_producer로 통합 가능
    #     logger.info("Reinitializing KafkaProducer...")
    #     return self.initialize_producer()

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"GStreamer Error: {err}, Debug: {debug}")
            self._stop_event.set() # 오류 발생 시 스레드 종료 이벤트 설정
        elif t == Gst.MessageType.EOS:
            logger.info("GStreamer End-Of-Stream reached.")
            self._stop_event.set() # EOS 도달 시 스레드 종료 이벤트 설정
        elif t == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            logger.warning(f"GStreamer Warning: {err}, Debug: {debug}")
        # else:
            # logger.debug(f"GStreamer message type: {t}") # 너무 많은 로그를 유발할 수 있음
        return True # 핸들러 계속 유지

    def on_new_sample(self, sink):
        # logger.debug("on_new_sample called.") # 너무 자주 호출될 수 있으므로 주의
        if not self.producer or not self.running: # 프로듀서가 없거나, 실행 중이 아니면 무시
            # logger.warning("Kafka producer not available or streamer not running. Skipping sample.")
            return Gst.FlowReturn.OK 
        
        try:
            sample = sink.emit('pull-sample')
            if not sample:
                logger.warning("Failed to pull sample from appsink.")
                return Gst.FlowReturn.ERROR # 샘플 가져오기 실패 시 에러 반환

            buf = sample.get_buffer()
            result, map_info = buf.map(Gst.MapFlags.READ)
            if not result:
                logger.error("Failed to map buffer for reading.")
                return Gst.FlowReturn.ERROR
            
            data_to_send = map_info.data # 바이트 데이터
            # logger.info(f"Extracted frame of size {len(data_to_send)} bytes.") # 너무 많은 로그 생성 가능

            try:
                future = self.producer.send(self.topic, data_to_send)
                # future.get(timeout=1.0) # 동기 전송 및 결과 확인 (성능에 영향 줄 수 있음, 비동기가 기본)
                                        # 타임아웃을 짧게 주거나, 콜백 기반으로 변경 고려
                logger.debug(f"Sent frame to Kafka topic {self.topic} (size: {len(data_to_send)})")
            except Exception as e: # Kafka 전송 중 예외 발생 (네트워크 문제 등)
                logger.error(f"Failed to send frame to Kafka: {e}. Attempting to reinitialize producer.")
                # 프로듀서 재초기화 시도 (연결 문제일 수 있으므로)
                # 너무 자주 재초기화하는 것을 방지하기 위해 카운터나 시간 제한 둘 수 있음
                if not self.initialize_producer(): # 재초기화 실패하면 더 이상 진행 어려움
                    self._stop_event.set() # 스레드 종료
                    return Gst.FlowReturn.ERROR

            finally:
                buf.unmap(map_info) # 항상 버퍼 unmap

        except Exception as e:
            logger.error(f"Error in on_new_sample: {e}")
            # 여기서 Gst.FlowReturn.ERROR를 반환하면 파이프라인이 멈출 수 있음
            # 상황에 따라 OK를 반환하고 에러 카운팅 후 특정 임계값 초과 시 스레드 종료 등의 로직도 가능

        return Gst.FlowReturn.OK

    def stop_stream(self):
        logger.info("Attempting to stop KafkaStreamer...")
        self._stop_event.set() # 스레드 루프 종료 요청

        if self._thread and self._thread.is_alive():
            logger.info("Waiting for KafkaStreamer thread to join...")
            self._thread.join(timeout=10.0) # 스레드 종료 대기 (타임아웃 설정)
            if self._thread.is_alive():
                logger.warning("KafkaStreamer thread did not join in time.")
            else:
                logger.info("KafkaStreamer thread joined successfully.")
        self._thread = None
        self.running = False # 명시적으로 running 상태 변경
        logger.info("KafkaStreamer stopped.")

    def is_alive(self):
        return self._thread is not None and self._thread.is_alive()
