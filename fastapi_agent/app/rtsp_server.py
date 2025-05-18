"""

gstreamer 기반반 rtsp 서버 스트리밍 제공하는 모듈

최근 작성일 240930 송인용

"""

# app/rtsp_server.py
import gi
import threading
gi.require_version('Gst', '1.0')
gi.require_version('GstRtsp', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GLib, GstRtsp
import logging
import socket
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 외부에 연결하여 호스트의 IP 주소를 가져오는 방법
        s.connect(('8.8.8.8', 80))
        ip_address = s.getsockname()[0]
    except Exception:
        ip_address = '127.0.0.1'
    finally:
        s.close()
    return ip_address

# Gstreamer의 CustomRTSPMediaFactory를 상속받아 파이프라인 제어를 동적으로 수행
class CustomRTSPMediaFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, device, **properties):
        super(CustomRTSPMediaFactory, self).__init__(**properties)
        self.device = device
        self.media = None
        self.pipeline = None

    def do_create_element(self, url):
        pipeline_str = f"( v4l2src device={self.device} ! videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! h264parse ! rtph264pay name=pay0 pt=96 config-interval=1 )"
        logger.info(f"Creating pipeline: {pipeline_str}")
        pipeline = Gst.parse_launch(pipeline_str)
        
        # 파이프라인 상태 변경 콜백 추가
        #bus = pipeline.get_bus()
        #bus.add_signal_watch()
        #bus.connect("message", self._on_bus_message)
        return pipeline
    
    # 파이프라인 상태 변경 이벤트 처리
    def _on_bus_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"RTSP GST Pipeline Error for device {self.device}: {err}, Debug: {debug}")
            # 필요시 파이프라인 중지 또는 재시작 로직
        elif t == Gst.MessageType.EOS:
            logger.info(f"RTSP GST Pipeline EOS for device {self.device}.")
        elif t == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline: # 파이프라인 전체의 상태 변경만 로깅
                old, new, pending = message.parse_state_changed()
                logger.info(f"RTSP GST Pipeline state changed for device {self.device}: {old.value_nick} -> {new.value_nick}")
                if new == Gst.State.PLAYING:
                    logger.info(f"RTSP GST Pipeline for {self.device} is NOW PLAYING.")
                elif new == Gst.State.NULL and old == Gst.State.PLAYING:
                    logger.info(f"RTSP GST Pipeline for {self.device} has stopped.")
        return True

    def do_media_configure(self, rtsp_media):
        logger.info("do_media_configure called.")
        # 인터리브 모드 활성화 (TCP 기반 전송)
        rtsp_media.set_protocols(GstRtsp.RTSPLowerTrans.TCP)
        #rtsp_media.set_protocols(GstRtsp.RTSPLowerTrans.HTTP)
        logger.info("RTSP media configured to use TCP interleaved mode.")
        self.media = rtsp_media
        # media에서 파이프라인 요소 가져오기
        self.pipeline = rtsp_media.get_element()
        self.set_shared(True)
        self.set_eos_shutdown(False)
        try:
            self.set_permissions(None)  # 모든 클라이언트 허용
        except AttributeError:
            logger.warning("Permissions setup not available")

    def stop(self):
        if self.pipeline:
            # 파이프라인의 상태를 NULL로 변경하여 스트리밍 중지
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
        if self.media:
            self.media = None

    def _handle_pipeline_error(self):
        logger.error("Handling pipeline error.")
        # 파이프라인 중지 또는 재시작 로직 추가
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            logger.info("Pipeline state set to NULL due to error.")
    
    def _handle_eos(self):
        logger.info("Handling end of stream (EOS).")
        # EOS 발생 시 필요한 로직 추가 (예: 파이프라인 재시작)
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            logger.info("Pipeline state set to NULL due to EOS.")

class RTSPServer(threading.Thread):
    def __init__(self, port=8554, mount_point="/test"):
        super(RTSPServer, self).__init__()
        Gst.init(None)
        self.server = GstRtspServer.RTSPServer()
        self.server.props.address = '0.0.0.0'
        self.server.props.service = str(port)

        self.mount_point = mount_point
        self.factory = None
        self.is_streaming = False
        self.loop = GLib.MainLoop()
        self.mounts = self.server.get_mount_points()
        self.external_ip = os.getenv('EXTERNAL_IP', get_ip_address())
        self.external_port = int(os.getenv('EXTERNAL_PORT', port))
        
        logger.info(f"RTSP Server initialized on port {port} with mount point {mount_point}")
        logger.info(f"RTSP Server is accessible at rtsp://{self.external_ip}:{self.external_port}{mount_point}")
        
    def get_full_stream_uri(self):
        """외부에서 접속 가능한 전체 RTSP URI를 반환"""
        return f"rtsp://{self.external_ip}:{self.external_port}{self.mount_point}"

    def run(self):
        self.server.attach(None)
        logger.info("RTSP server started.")
        self.loop.run()

    def start_server(self):
        self.start()

    def stop_server(self):
        if self.loop.is_running():
            self.loop.quit()
            logger.info("RTSP server stopped.")

    def start_stream(self, device='/dev/video0'):
        if self.is_streaming:
            logger.info("Streaming is already in progress.")
            return

        if not os.path.exists(device):
            logger.error(f"Device {device} not found")
            return False
            
        try:
            self.factory = CustomRTSPMediaFactory(device)
            self.factory.set_shared(True)
            self.mounts.add_factory(self.mount_point, self.factory)
            self.is_streaming = True
            logger.info("Streaming started successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to start streaming: {str(e)}")
            return False

    def stop_stream(self):
        if not self.is_streaming:
            logger.info("Stream is not active.")
            return

        if self.factory:
            self.factory.stop()
            self.mounts.remove_factory(self.mount_point)
            self.factory = None
            logger.info("Streaming stopped.")

        self.is_streaming = False
