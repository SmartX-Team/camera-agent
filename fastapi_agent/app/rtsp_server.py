"""

gstreamer 로 rtsp 서버 개방하도록 하는 코드

최근 작성일 240930 송인용

"""


# app/rtsp_server.py
import gi
import threading
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GObject, GLib


# Gstreamer 의 CustomRTSPMediaFactory 상속 받아서 유저가 동적으로 API 호출하여 파이프라인 제어
class CustomRTSPMediaFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, device, **properties):
        super(CustomRTSPMediaFactory, self).__init__(**properties)
        self.device = device
        self.media = None
        self.pipeline = None

    def do_create_element(self, url):
        pipeline_str = f"( v4l2src device={self.device} ! videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! rtph264pay name=pay0 pt=96 )"
        return Gst.parse_launch(pipeline_str)

    def do_media_configure(self, media):
        self.media = media
        # media에서 파이프라인 요소 가져오기
        self.pipeline = media.get_element()

    def stop(self):
        if self.pipeline:
            # 파이프라인의 상태를 NULL로 변경하여 스트리밍 중지
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
        if self.media:
            self.media = None

class RTSPServer(threading.Thread):
    def __init__(self, port=8554, mount_point="/test"):
        super(RTSPServer, self).__init__()
        Gst.init(None)
        self.server = GstRtspServer.RTSPServer()
        self.server.props.service = str(port)
        self.mount_point = mount_point
        self.factory = None
        self.is_streaming = False
        self.loop = GLib.MainLoop()
        self.mounts = self.server.get_mount_points()

    def run(self):
        self.server.attach(None)
        print("RTSP server started.")
        self.loop.run()

    def start_server(self):
        self.start()

    def stop_server(self):
        if self.loop.is_running():
            self.loop.quit()
            print("RTSP server stopped.")

    def start_stream(self, device='/dev/video0'):
        if self.is_streaming:
            print("Streaming is already in progress.")
            return

        self.factory = CustomRTSPMediaFactory(device)
        self.factory.set_shared(True)
        self.mounts.add_factory(self.mount_point, self.factory)
        self.is_streaming = True
        print("Streaming started.")

    def stop_stream(self):
        if not self.is_streaming:
            print("Streaming is not in progress.")
            return

        if self.factory:
            self.factory.stop()
            self.mounts.remove_factory(self.mount_point)
            self.factory = None
            print("Streaming stopped.")

        self.is_streaming = False
