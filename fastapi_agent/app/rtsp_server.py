"""

gstreamer 로 rtsp 서버 개방하도록 하는 코드

최근 작성일 240930 송인용

"""


# app/rtsp_server.py
import gi
import threading
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GObject


# Gstreamer 의 CustomRTSPMediaFactory 상속 받아서 유저가 동적으로 API 호출하여 파이프라인 제어
class CustomRTSPMediaFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, device, **properties):
        super(CustomRTSPMediaFactory, self).__init__(**properties)
        self.device = device
        self.pipeline = None

    def do_create_element(self, url):
        pipeline_str = f"( v4l2src device={self.device} ! videoconvert ! x264enc ! rtph264pay name=pay0 pt=96 )"
        self.pipeline = Gst.parse_launch(pipeline_str)
        return self.pipeline

    def stop(self):
        # 초기화 시점에 빈 영상을 송출하도록 launch 라인 설정
        #pipeline_str = "( videotestsrc pattern=black ! videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! rtph264pay name=pay0 pt=96 )"
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None

class RTSPServer:
    def __init__(self, port=8554, mount_point="/test"):
        Gst.init(None)
        self.server = GstRtspServer.RTSPServer()
        self.server.props.service = str(port)
        self.mount_point = mount_point
        self.factory = None
        self.is_streaming = False

    def start(self):
        self.server.attach(None)

    def start_stream(self, device='/dev/video0'):
        if self.is_streaming:
            print("Streaming is already in progress.")
            return

        self.factory = CustomRTSPMediaFactory(device)
        self.factory.set_shared(True)
        mounts = self.server.get_mount_points()
        mounts.add_factory(self.mount_point, self.factory)
        self.is_streaming = True

    def stop_stream(self):
        if not self.is_streaming:
            print("Streaming is not in progress.")
            return

        if self.factory:
            self.factory.stop()
            # Mount point에서 팩토리 제거
            mounts = self.server.get_mount_points()
            mounts.remove_factory(self.mount_point)
            self.factory = None

        self.is_streaming = False
