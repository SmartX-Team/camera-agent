# app/rtsp_server.py
import gi
import threading
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GObject

class RTSPServer(threading.Thread):
    def __init__(self, port=8554, mount_point="/test"):
        super().__init__()
        Gst.init(None)
        self.loop = GObject.MainLoop()
        self.server = GstRtspServer.RTSPServer()
        self.server.props.service = str(port)
        self.is_streaming = False

        self.server.props.address = '0.0.0.0'

        self.factory = GstRtspServer.RTSPMediaFactory()
        self.factory.set_shared(True)

        # 초기화 시점에 빈 영상을 송출하도록 launch 라인 설정
        pipeline_str = "( videotestsrc pattern=black ! videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! rtph264pay name=pay0 pt=96 )"
        self.factory.set_launch(pipeline_str)

        self.mount_points = self.server.get_mount_points()
        self.mount_points.add_factory(mount_point, self.factory)

    def run(self):
        self.server.attach(None)
        self.loop.run()

    def start_stream(self, device='/dev/video0'):
        if self.is_streaming:
            print("Streaming is already in progress.")
            return
        # 실제 카메라 데이터 송출
        pipeline_str = f"( v4l2src device={device} ! videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! rtph264pay name=pay0 pt=96 )"
        self.factory.set_launch(pipeline_str)
        self.is_streaming = True
        print(f"Streaming has started on device {device}.")

    def stop_stream(self):
        if not self.is_streaming:
            print("Streaming is not in progress.")
            return
        # 빈 영상을 송출하는 파이프라인으로 전환
        pipeline_str = "( videotestsrc pattern=black ! videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! rtph264pay name=pay0 pt=96 )"
        self.factory.set_launch(pipeline_str)
        self.is_streaming = False
        print("Streaming has stopped. A blank video is being transmitted.")

