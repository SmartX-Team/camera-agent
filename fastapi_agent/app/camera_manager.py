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
import os
import uuid
from datetime import datetime


gi.require_version('Gst', '1.0')
from gi.repository import Gst , GObject
from .kafka_streamer import KafkaStreamer

logger = logging.getLogger(__name__)

class CameraManager(threading.Thread):
    def __init__(self, agent_id, server_url, streaming_method='RTSP', 
                 rtsp_server_instance=None, # RTSPServer 객체 주입
                 kafka_init_params=None,    # Kafka 초기화 파라미터 주입
                 camera_env_configs=None,   # 카메라 메타데이터 환경변수 값들 주입
                 update_interval=10):
        super().__init__()
        Gst.init(None) # 스레드별 Gst 초기화는 run 메서드 시작 시에도 고려 가능
        
        self.agent_id = agent_id # Visibility 서버로부터 받은 최종 agent_id로 업데이트 필요
        self.server_url = server_url
        self.streaming_method = streaming_method.upper()
        
        self.rtsp_server = rtsp_server_instance # 주입된 RTSPServer 인스턴스
        self.kafka_params = kafka_init_params if kafka_init_params else {} # Kafka 설정값
        self.camera_configs = camera_env_configs if camera_env_configs else {} # 카메라 메타데이터 설정값

        self.update_interval = update_interval
        self.running = True
        
        self.cameras = [] # 상세 카메라 정보를 담을 리스트 (단일 카메라 객체 포함)
        self.current_device_path = None # 실제 사용될 카메라 장치 경로
        self.camera_id = self.camera_configs.get('camera_id_override') or str(uuid.uuid4())

        self.kafka_streamer = None
        if self.streaming_method == 'KAFKA':
            # KafkaStreamer에 해상도/FPS 전달 (환경변수에서 파싱한 값)
            try:
                self.kafka_streamer = KafkaStreamer()
                
            except ValueError as e:
                logger.error(f"Invalid resolution/FPS for Kafka: {res_str}, {fps_val}. Error: {e}")
                # KafkaStreamer 초기화 실패 시 스트리밍 불가 처리 필요
                self.streaming_method = 'NONE' # 또는 적절한 오류 상태

        self._initialize_managed_camera() # 카메라 정보 객체 생성

    def _determine_device_path(self):
        """ 환경 변수 또는 자동 감지를 통해 사용할 카메라 장치 경로를 결정합니다. """
        configured_path = self.camera_configs.get('camera_device_path_override')
        if configured_path:
            if os.path.exists(configured_path) and self.is_camera_available(configured_path):
                logger.info(f"Using configured camera device: {configured_path}")
                return configured_path
            else:
                logger.warning(f"Configured camera device {configured_path} not available or not found.")
        
        logger.info("No valid CAMERA_DEVICE_PATH set or device not available, attempting auto-detection...")
        video_devices = sorted(glob.glob('/dev/video*')) # 정렬하여 일관성 유지
        for device in video_devices:
            if self.is_camera_available(device):
                logger.info(f"Auto-detected and using camera device: {device}")
                return device
        
        logger.error("No available camera device found.")
        return None

    def _build_camera_object(self):
        """ self.current_device_path를 기반으로 단일 카메라 정보 객체를 생성/업데이트합니다. """
        if not self.current_device_path:
            self.cameras = []
            return

        # 해상도 및 FPS 파싱 (환경변수 우선)
        resolution_str = self.camera_configs.get('camera_resolution', '640x480')
        fps_val = 15
        try:
            fps_val = int(self.camera_configs.get('camera_fps', '15'))
        except ValueError:
            logger.warning(f"Invalid CAMERA_FPS value. Defaulting to 15.")

        # stream_details 구성
        stream_details_obj = {}
        if self.streaming_method == 'RTSP' and self.rtsp_server:
            stream_details_obj['rtsp_uri'] = self.rtsp_server.get_full_stream_uri()
        elif self.streaming_method == 'KAFKA':
            stream_details_obj['kafka_topic'] = self.kafka_params.get('topic', 'N/A')
            stream_details_obj['kafka_bootstrap_servers'] = self.kafka_params.get('bootstrap_servers', 'N/A')
        
        current_time = datetime.utcnow().isoformat()
        is_currently_streaming = self.check_status() # 실제 스트리밍 상태 확인

        camera_object = {
            'camera_id': self.camera_id,
            'camera_name': self.camera_configs.get('camera_name', f"Cam-{self.current_device_path.split('/')[-1]}"),
            'status': 'streaming' if is_currently_streaming else ('active' if self.current_device_path else 'error'),
            'type': self.camera_configs.get('camera_type', 'rgb'),
            'environment': self.camera_configs.get('camera_environment', 'real'),
            'stream_protocol': self.streaming_method if self.current_device_path else 'NONE',
            'stream_details': stream_details_obj if self.current_device_path else {},
            'resolution': resolution_str,
            'fps': fps_val,
            'location': self.camera_configs.get('camera_location', 'N/A'),
            'host_pc_name': os.getenv('HOSTNAME', self.agent_id.split('-')[0]), # Agent ID에서 일부 사용 또는 HOSTNAME
            'frame_transmission_enabled': is_currently_streaming,
            'last_update': current_time,
            '_device_path': self.current_device_path # 내부 관리용
        }
        self.cameras = [camera_object]

    def _initialize_managed_camera(self):
        """ 단일 관리 카메라 정보를 설정하고 self.cameras 리스트를 업데이트합니다. """
        self.current_device_path = self._determine_device_path()
        self._build_camera_object() # self.cameras 업데이트

    def get_initial_camera_data_for_registration(self):
        """ Agent 등록 시 사용할 초기 카메라 정보 리스트를 반환합니다. """
        # __init__에서 이미 _initialize_managed_camera()를 통해 self.cameras가 설정됨
        return self.cameras

    def run(self):
        # Gst.init(None) # 스레드 시작 시 Gst 초기화 (필요한 경우)
        logger.info(f"CameraManager thread started for agent {self.agent_id}.")
        while self.running:
            is_currently_streaming = self.check_status() # 실제 스트리밍 파이프라인 상태

            if not is_currently_streaming: # 스트리밍 중이 아닐 때만 장치 유효성 집중 검사
                if not self.current_device_path or not self.is_camera_available(self.current_device_path):
                    logger.warning(f"Managed camera device {self.current_device_path} is not available or stream is down. Attempting rediscovery.")
                    previous_device = self.current_device_path
                    self._initialize_managed_camera() # 장치 재탐색 및 카메라 정보 업데이트
                    if self.current_device_path != previous_device and self.current_device_path is not None:
                        logger.info(f"New camera device {self.current_device_path} initialized. Previous: {previous_device}")
                        # 스트림이 비활성 상태였으므로, sync_config_from_server가 다음 주기에 스트림 시작 여부 결정
                else:
                    # 스트리밍 중은 아니지만, 장치는 사용 가능한 상태
                    logger.debug(f"Device {self.current_device_path} is available, but stream is not active. Waiting for server config.")
            else:
                # 스트리밍 중일 때는 장치가 사용 가능하다고 간주 (주기적인 심층 검사 생략)
                logger.debug(f"Stream for {self.current_device_path} is active. Skipping deep availability check.")

            self.update_server_status() # 서버로 현재 상태 보고
            self.sync_config_from_server() # 서버 설정과 동기화
            time.sleep(self.update_interval)
        logger.info(f"CameraManager thread stopped for agent {self.agent_id}.")

    def is_camera_available(self, device_path):
        if not device_path or not os.path.exists(device_path):
            return False
        pipeline_str = f'v4l2src device={device_path} num-buffers=1 ! fakesink'
        try:
            pipeline = Gst.parse_launch(pipeline_str)
            ret = pipeline.set_state(Gst.State.PLAYING)
            # 짧은 시간 동안 상태 변경 대기 (PLAYING까지 도달하는지)
            if ret != Gst.StateChangeReturn.FAILURE:
                # 실제 데이터가 나오는지 확인하려면 약간의 대기 후 상태 체크 필요
                # 여기서는 파이프라인 생성 및 PLAYING 시도 성공 여부만 판단
                bus = pipeline.get_bus()
                msg = bus.timed_pop_filtered(100 * Gst.MSECOND, Gst.MessageType.ERROR | Gst.MessageType.EOS) # 100ms
                pipeline.set_state(Gst.State.NULL)
                return msg is None # 에러나 EOS가 없으면 사용 가능하다고 간주
            pipeline.set_state(Gst.State.NULL)
            return False
        except Exception as e:
            logger.error(f"Error checking camera {device_path}: {e}")
            return False


    def update_server_status(self):
        if not self.cameras: # 관리할 카메라 정보가 없으면 업데이트 스킵
            logger.debug("No camera data to update to server.")
            return

        # 현재 카메라의 실제 상태를 반영하여 self.cameras[0] 업데이트
        self._build_camera_object() # 상태, last_update 등을 최신으로 업데이트

        payload = {
            'agent_id': self.agent_id,
            'cameras': self.cameras # 상세 정보가 담긴 단일 카메라 객체 리스트
        }
        logger.debug(f"Updating server status with payload: {payload}")
        try:
            response = requests.post(
                f'{self.server_url}/agent_update_status', # 수정된 엔드포인트
                json=payload,
                timeout=5
            )
            response.raise_for_status()
            logger.info(f"Camera status successfully updated to server for agent {self.agent_id}.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update camera status for agent {self.agent_id}: {e}")

    def sync_config_from_server(self):
        if not self.cameras or not self.current_device_path: # 관리 카메라가 없으면 동기화 스킵
            return
        
        logger.debug(f"Syncing config from server for agent {self.agent_id}...")
        try:
            response = requests.get(
                f'{self.server_url}/agent_get_config?agent_id={self.agent_id}',
                timeout=5
            )
            response.raise_for_status()
            server_config = response.json()
            logger.debug(f"Received config from server: {server_config}")

            server_cameras_info = server_config.get('cameras', [])
            if not server_cameras_info:
                logger.warning("No camera configurations received from server.")
                return

            # 이 Agent가 관리하는 카메라(ID 기준)에 대한 설정을 찾음
            my_cam_config_from_server = None
            for cam_info in server_cameras_info:
                if cam_info.get('camera_id') == self.camera_id:
                    my_cam_config_from_server = cam_info
                    break
            
            if my_cam_config_from_server:
                desired_fte = my_cam_config_from_server.get('frame_transmission_enabled', False)
                current_fte = self.cameras[0].get('frame_transmission_enabled', False) # 로컬 상태

                logger.debug(f"Camera {self.camera_id}: Server wants FTE={desired_fte}, current FTE={current_fte}")

                if desired_fte and not current_fte:
                    logger.info(f"Server requests to START frame transmission for camera {self.camera_id}. Starting stream...")
                    self.start_stream()
                elif not desired_fte and current_fte:
                    logger.info(f"Server requests to STOP frame transmission for camera {self.camera_id}. Stopping stream...")
                    self.stop_stream()
                # 상태가 이미 일치하면 아무것도 안 함
            else:
                logger.warning(f"Configuration for camera_id {self.camera_id} not found in server response.")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to sync config from server for agent {self.agent_id}: {e}")
        except Exception as e: # JSON 파싱 오류 등
            logger.error(f"Error processing server config for agent {self.agent_id}: {e}", exc_info=True)


    def get_camera_info(self):
        """ Agent의 FastAPI 엔드포인트에서 사용될 카메라 정보 반환 """
        # 현재 상태를 반영하기 위해 _build_camera_object() 호출
        if self.current_device_path: # 장치가 있을 때만 업데이트 시도
            self._build_camera_object()
        return self.cameras

    def start_stream(self): # device 인자 제거, self.current_device_path 사용
        if not self.current_device_path:
            logger.warning("No current device path set to start streaming.")
            return False
        
        success = False
        if self.streaming_method == 'RTSP' and self.rtsp_server:
            logger.info(f"Attempting to start RTSP stream for device {self.current_device_path}...")
            success = self.rtsp_server.start_stream(self.current_device_path)
        elif self.streaming_method == 'KAFKA' and self.kafka_streamer:
            logger.info(f"Attempting to start Kafka stream for device {self.current_device_path}...")
            self.kafka_streamer.start_stream() # KafkaStreamer의 start_stream은 스레드 시작
            success = True # KafkaStreamer는 스레드를 시작하므로 즉시 성공으로 간주 (실제 스트리밍은 스레드 내에서)
        else:
            logger.warning(f"No valid streaming_method ({self.streaming_method}) or server/streamer instance to start stream.")
            return False

        if success and self.cameras:
            self.cameras[0]['status'] = 'streaming'
            self.cameras[0]['frame_transmission_enabled'] = True
            self.cameras[0]['last_update'] = datetime.utcnow().isoformat()
            logger.info(f"Stream started for {self.current_device_path}. Updated local camera status.")
        elif self.cameras: # 성공하지 못했으나 카메라 객체는 존재
             self.cameras[0]['status'] = 'error' # 또는 'active' (시작 실패)
             self.cameras[0]['frame_transmission_enabled'] = False
             logger.warning(f"Failed to start stream for {self.current_device_path}.")
        return success

    def stop_stream(self): # device 인자 제거
        logger.info(f"Attempting to stop stream (method: {self.streaming_method})...")
        if self.streaming_method == 'RTSP' and self.rtsp_server:
            self.rtsp_server.stop_stream()
        elif self.streaming_method == 'KAFKA' and self.kafka_streamer:
            self.kafka_streamer.stop_stream()
        else:
            logger.warning(f"No valid streaming_method ({self.streaming_method}) or server/streamer instance to stop stream.")
            return

        if self.cameras: # 카메라 객체가 있다면 상태 업데이트
            self.cameras[0]['status'] = 'active' # 스트림 중지 후 'active' 상태로 변경 (장치는 여전히 사용 가능 가정)
            self.cameras[0]['frame_transmission_enabled'] = False
            self.cameras[0]['last_update'] = datetime.utcnow().isoformat()
            logger.info("Stream stopped. Updated local camera status.")

    def check_status(self):
        # 현재 스트리밍 파이프라인의 실제 동작 상태를 반환
        if self.streaming_method == 'RTSP' and self.rtsp_server:
            return self.rtsp_server.is_streaming
        elif self.streaming_method == 'KAFKA' and self.kafka_streamer:
            return self.kafka_streamer.is_alive() # KafkaStreamer의 running 플래그 제공하는 getter 사용
        return False

    def stop_manager_thread(self): # threading.Thread의 stop은 없으므로 이름 변경
        logger.info(f"Stopping CameraManager thread for agent {self.agent_id}...")
        self.running = False
        self.stop_stream() # 현재 진행 중인 스트림도 중지