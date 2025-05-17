"""

gstreamer 로 현재 agent 가 동작하는 카메라 status 확인 및 관리하는 코드

최근 작성일 240930 송인용

"""

# app/camera_manager.py

import threading
import time
import requests
import glob
import gi
import logging

gi.require_version('Gst', '1.0')
from gi.repository import Gst , GObject
from .kafka_streamer import KafkaStreamer

logger = logging.getLogger(__name__)

class CameraManager(threading.Thread):
    def __init__(self, agent_id, server_url, streaming_method='RTSP', streaming_server=None, kafka_params=None, update_interval=10):
        super().__init__()
        Gst.init(None)
        self.agent_id = agent_id
        self.server_url = server_url
        self.streaming_method = streaming_method
        self.streaming_server = streaming_server  # RTSPServer 객체 또는 None
        self.kafka_params = kafka_params
        self.update_interval = update_interval
        self.running = True
        self.cameras = []
        self.current_device = None

        if self.streaming_method == 'KAFKA':
            self.kafka_streamer = KafkaStreamer(**self.kafka_params)
        else:
            self.kafka_streamer = None

        #self.loop = GObject.MainLoop()
        #self.main_context = self.loop.get_context()

        # Create a thread for the main loop


    def run(self):
        Gst.init(None)
        while self.running:
            self.discover_cameras()
            self.update_camera_status()
            time.sleep(self.update_interval)

    def discover_cameras(self):
        #logger.info("Discovering cameras using GStreamer...")
        previous_cameras = set(cam['device'] for cam in self.cameras)
        self.cameras = []
        video_devices = glob.glob('/dev/video*')

        for device in video_devices:
            #logger.info(f"Camera found: {device}")
            if self.is_camera_available(device):
                self.cameras.append({'device': device})
                
            else:
                logger.info(f"Device {device} is not a valid camera.")

        current_cameras = set(cam['device'] for cam in self.cameras)

        # 새로운 카메라가 연결되었을 때 스트리밍 시작
        if not previous_cameras and current_cameras:
            self.current_device = self.cameras[0]['device']
            self.start_stream()

        # 모든 카메라가 제거되었을 때 스트리밍 중지
        if previous_cameras and not current_cameras:
            self.stop_stream()
            self.current_device = None

    def is_camera_available(self, device):
        pipeline_str = f'v4l2src device={device} ! fakesink'
        pipeline = Gst.parse_launch(pipeline_str)
        ret = pipeline.set_state(Gst.State.PLAYING)

        if ret == Gst.StateChangeReturn.FAILURE:
            pipeline.set_state(Gst.State.NULL)
            return False
        else:
            pipeline.set_state(Gst.State.NULL)
            return True

    def update_camera_status(self):
        # 카메라 상태를 서버에 업데이트
        camera_status = [{'device': cam['device']} for cam in self.cameras]
        data = {
            'agent_id': self.agent_id,
            'camera_status': camera_status
        }
        print(data)
        try:
            response = requests.post(
                f'{self.server_url}/agent/update_status',
                json=data
            )
            response.raise_for_status()
            logger.info("Camera status updated to server.")
        except Exception as e:
            logger.error(f"Failed to update camera status: {e}")

    def get_camera_info(self):
        return [{'device': cam['device']} for cam in self.cameras]

    def start_stream(self):
        if self.current_device:
            if self.streaming_method == 'RTSP' and self.streaming_server:
                self.streaming_server.start_stream(self.current_device)
                logger.info("RTSP streaming started.")
            elif self.streaming_method == 'KAFKA' and self.kafka_streamer:
                self.kafka_streamer.start_stream(self.current_device)
                logger.info("Kafka streaming started.")
            else:
                logger.warning("No valid streaming server to start.")
        else:
            logger.warning("No camera device found to start streaming.")

    def stop_stream(self):
        if self.streaming_method == 'RTSP' and self.streaming_server:
            self.streaming_server.stop_stream()
            logger.info("RTSP streaming stopped.")
        elif self.streaming_method == 'KAFKA' and self.kafka_streamer:
            self.kafka_streamer.stop_stream()
            logger.info("Kafka streaming stopped.")
        else:
            logger.warning("No valid streaming server to stop.")

    def check_status(self):
        # 현재 스트리밍 상태를 반환
        if self.streaming_method == 'RTSP' and self.streaming_server:
            return self.streaming_server.is_streaming
        elif self.streaming_method == 'KAFKA' and self.kafka_streamer:
            return self.kafka_streamer.running
        else:
            return False

    def stop(self):
        self.running = False
        self.stop_stream()