"""

업데이트 된 서버 및 데이터 모델에 맞춰 에이전트도 업데이트!

20250517 작성일 InYong Song 


Pod Deployment 로 배포할때 환경변수 load 하는 사긴이랑 모듈 import 시간 문제로 인식 안되길래 해당 문제 개선


처음 agent 가 실행시 register_agent() 실행,
등록 실패시 일단 agent 종료하도록함

해당 코드는 처음 등록할때 서버에 등록 및 FAST API 서버 실행되도록함
FAST API 는 후에 gRPC 로 대체될 수 있음

최근 작성일 240930 송인용

"""

from fastapi import FastAPI , HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .rtsp_server import RTSPServer
from .camera_manager import CameraManager
from .ptp_synchronization import synchronize_with_ptp_server
import threading
import logging
import os
import requests
import time
import uuid
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application lifespan: startup sequence initiated.")
    # 환경 변수 로드
    app.state.streaming_method = os.getenv('STREAMING_METHOD', 'RTSP').upper()
    
    # Visibility 서버 정보
    # VISIBILITY_SERVER_URL 환경 변수가 전체 URL을 포함하도록 권장
    server_url_env = os.getenv('VISIBILITY_SERVER_URL', 'http://10.32.187.108:5111')
    if not (server_url_env.startswith('http://') or server_url_env.startswith('https://')):
        _server_ip_val = os.getenv('SERVER_IP', '10.32.187.108') # 호환성을 위해 남겨둠
        _server_port_val = os.getenv('SERVER_PORT', '5111')    # 호환성을 위해 남겨둠
        app.state.server_url = f'http://{_server_ip_val}:{_server_port_val}'
    else:
        app.state.server_url = server_url_env
    
    app.state.agent_fastapi_port = int(os.getenv('AGENT_PORT', 8000))
    # AGENT_ID 환경변수가 있다면 그것을 이름으로 사용, 없으면 AGENT_NAME, 그것도 없으면 기본값 생성
    app.state.agent_name = os.getenv("AGENT_ID", os.getenv("AGENT_NAME", f"default-agent-{uuid.uuid4().hex[:6]}"))


    logger.info(f"Target Visibility Server URL: {app.state.server_url}")
    logger.info(f"Agent Name: {app.state.agent_name}")
    logger.info(f"Agent FastAPI Port: {app.state.agent_fastapi_port}")
    logger.info(f"Streaming Method: {app.state.streaming_method}")

    app.state.start_time = time.time()

    # 카메라 메타데이터 환경 변수 로드
    camera_env_configs = {
        'camera_device_path_override': os.getenv('CAMERA_DEVICE_PATH'),
        'camera_id_override': os.getenv('CAMERA_ID_OVERRIDE'),
        'camera_name': os.getenv('CAMERA_NAME'), # CameraManager에서 None일 경우 기본값 처리
        'camera_type': os.getenv('CAMERA_TYPE', 'rgb'),
        'camera_environment': os.getenv('CAMERA_ENVIRONMENT', 'real'),
        'camera_resolution': os.getenv('CAMERA_RESOLUTION', '640x480'),
        'camera_fps': os.getenv('CAMERA_FPS', '15'),
        'camera_location': os.getenv('CAMERA_LOCATION'), # CameraManager에서 None일 경우 기본값 처리
    }
    logger.info(f"Camera Environment Configs: {camera_env_configs}")

    # 스트리밍 서버/파라미터 초기화
    rtsp_server_instance = None
    kafka_init_params = None
    app.state.rtsp_server = None # app.state에도 초기화
    app.state.kafka_params = None

    if app.state.streaming_method == 'RTSP':
        rtsp_listen_port = int(os.getenv('RTSP_SERVER_LISTEN_PORT', 8554))
        rtsp_mount_point = os.getenv('RTSP_MOUNT_POINT', '/default_stream')
        rtsp_server_instance = RTSPServer(port=rtsp_listen_port, mount_point=rtsp_mount_point)
        rtsp_server_instance.start() 
        app.state.rtsp_server = rtsp_server_instance
        logger.info(f"RTSPServer thread started. Listening on port {rtsp_listen_port}, mount point {rtsp_mount_point}.")
    elif app.state.streaming_method == 'KAFKA':
        kafka_init_params = {
            'topic': os.getenv('KAFKA_TOPIC', 'default_video_topic'),
            'bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        }
        app.state.kafka_params = kafka_init_params
        logger.info(f"Kafka streaming configured with params: {kafka_init_params}")
    else:
        logger.warning(f"Unsupported or 'NONE' STREAMING_METHOD: {app.state.streaming_method}. No specific streaming server will be initialized by main.py directly.")

    # --- Agent 등록 로직 ---
    # CameraManager를 먼저 생성 (이때 agent_id는 임시값 또는 agent_name 사용)
    temp_cm_for_init = CameraManager(
        agent_id=app.state.agent_name, 
        server_url=app.state.server_url,
        streaming_method=app.state.streaming_method,
        rtsp_server_instance=rtsp_server_instance, # 생성된 RTSPServer 인스턴스 전달
        kafka_init_params=kafka_init_params,     # Kafka 설정 전달
        camera_env_configs=camera_env_configs    # 카메라 메타데이터 설정 전달
    )
    initial_cameras_list = temp_cm_for_init.get_initial_camera_data_for_registration()

    if not initial_cameras_list and app.state.streaming_method != 'NONE':
        logger.error("No camera(s) configured or detected for registration. Registration payload will be empty for cameras.")
    
    def perform_agent_registration():
        registration_payload = {
            "agent_name": app.state.agent_name,
            "agent_port": app.state.agent_fastapi_port,
            "cameras": initial_cameras_list if initial_cameras_list else []
        }
        logger.info(f"Attempting agent registration with payload: {registration_payload}")
        try:
            response = requests.post(
                f"{app.state.server_url}/agent_register", 
                json=registration_payload,
                timeout=10
            )
            logger.info(f"Agent registration response status: {response.status_code}")
            if response.status_code == 201:
                data = response.json()
                server_assigned_agent_id = data.get("agent_id")
                if server_assigned_agent_id:
                    logger.info(f"Agent registered successfully. Server assigned Agent ID: {server_assigned_agent_id}")
                    return server_assigned_agent_id
                else:
                    logger.error(f"'agent_id' not found in successful registration response: {data}")
                    return None
            else:
                logger.error(f"Agent registration failed. Status: {response.status_code}, Body: {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Agent registration request failed (network/request error): {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during agent registration: {e}", exc_info=True)
            return None

    server_assigned_agent_id = None
    max_retries = 3
    retry_delay = 5
    for attempt in range(max_retries):
        server_assigned_agent_id = perform_agent_registration()
        if server_assigned_agent_id:
            break
        logger.error(f"Registration attempt {attempt + 1} of {max_retries} failed.")
        if attempt < max_retries - 1:
            logger.info(f"Retrying registration in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            logger.error("Maximum registration attempts reached. Agent may not function correctly with the server.")
            # raise RuntimeError("Failed to register agent with server after multiple retries.") # 필요시 에러 발생

    # CameraManager 최종 설정 및 시작
    app.state.camera_manager = temp_cm_for_init # 어쨌든 camera_manager는 app.state에 할당
    if server_assigned_agent_id:
        app.state.camera_manager.agent_id = server_assigned_agent_id # 실제 ID로 업데이트
        logger.info(f"CameraManager will use final agent_id: {server_assigned_agent_id}")
    else:
        logger.warning(f"CameraManager will use placeholder agent_id: {app.state.camera_manager.agent_id} due to registration failure.")
    
    # 등록 성공 여부와 관계없이 CameraManager 스레드는 시작 (로컬 기능 또는 재시도 등 고려)
    # 단, server_url이 있어야 서버 통신 시도라도 할 수 있음
    if app.state.server_url: # 서버 URL이 있을 때만 CM 스레드 시작 (서버 통신 시도)
         app.state.camera_manager.start()
         logger.info("CameraManager thread started.")
    else:
        logger.warning("VISIBILITY_SERVER_URL not set. CameraManager thread not started. Agent will operate locally if possible.")


    yield # FastAPI 애플리케이션 실행 구간

    # --- 애플리케이션 종료 시 처리 ---
    logger.info("Application lifespan: shutdown sequence initiated.")
    if hasattr(app.state, 'camera_manager') and app.state.camera_manager and app.state.camera_manager.is_alive():
        logger.info("Stopping CameraManager thread...")
        app.state.camera_manager.stop_manager_thread()
        app.state.camera_manager.join(timeout=10)
        if app.state.camera_manager.is_alive():
            logger.warning("CameraManager thread did not terminate gracefully.")
    
    if hasattr(app.state, 'rtsp_server') and app.state.rtsp_server and app.state.rtsp_server.is_alive():
        logger.info("Stopping RTSPServer thread...")
        app.state.rtsp_server.stop_server()
        app.state.rtsp_server.join(timeout=5)
        if app.state.rtsp_server.is_alive():
            logger.warning("RTSPServer thread did not terminate gracefully.")

    logger.info("Application shutdown completed.")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- FastAPI 엔드포인트들 ---
def get_cm(): # Helper function to get camera_manager from app.state
    if not hasattr(app.state, 'camera_manager') or not app.state.camera_manager:
        raise HTTPException(status_code=503, detail="CameraManager not initialized or agent not registered.")
    return app.state.camera_manager

@app.post("/start_stream", summary="Start the camera stream")
async def start_stream_endpoint():
    cm = get_cm()
    if cm.start_stream(): # CameraManager.start_stream()은 성공 시 True 반환하도록 수정 가정
        return {"message": f"{app.state.streaming_method} streaming started for device {cm.current_device_path}"}
    else:
        # start_stream이 False를 반환했거나, current_device_path가 없을 수 있음
        detail_msg = f"Failed to start {app.state.streaming_method} stream"
        if not cm.current_device_path:
            detail_msg += " (no active camera device)"
        else:
            detail_msg += f" for device {cm.current_device_path}"
        raise HTTPException(status_code=500, detail=detail_msg)

@app.post("/stop_stream", summary="Stop the camera stream")
async def stop_stream_endpoint():
    cm = get_cm()
    cm.stop_stream() # 반환값 없어도 일단 실행
    return {"message": f"{app.state.streaming_method} streaming stopped."}

@app.get("/camera_info", summary="Get information about managed camera(s)")
async def get_camera_info_endpoint():
    cm = get_cm()
    camera_list_details = cm.get_camera_info() 
    return {
        "agent_id": cm.agent_id, # 현재 CM이 알고있는 agent_id 포함
        "streaming_method": app.state.streaming_method,
        "camera_found": len(camera_list_details) > 0 if camera_list_details else False,
        "camera_list": camera_list_details if camera_list_details else []
    }

@app.get("/health", summary="Perform a health check of the agent")
async def health_check_endpoint():
    # STREAMING_METHOD을 app.state에서 가져오도록 수정
    current_streaming_method = app.state.streaming_method if hasattr(app.state, 'streaming_method') else 'UNKNOWN'
    
    if not hasattr(app.state, 'camera_manager') or not app.state.camera_manager:
        uptime = time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
        return {"status": "error", "message": "CameraManager not initialized", "uptime_seconds": uptime}

    cm = app.state.camera_manager
    try:
        device_path = cm.current_device_path
        camera_device_ok = cm.is_camera_available(device_path) if device_path else False
        streaming_pipeline_active = cm.check_status()
        
        agent_overall_status = "ok"
        # frame_transmission_enabled는 self.cameras[0]에 저장된 '서버가 원하는 상태' 또는 '로컬의 실제 상태'
        # 여기서는 실제 파이프라인 상태를 기준으로 판단
        is_transmitting_when_should = True # 기본값을 True로 두고, 문제가 있을 때 False로 변경
        if current_streaming_method != 'NONE': # 스트리밍 방식이 설정된 경우에만
            if cm.cameras and isinstance(cm.cameras[0], dict): # 카메라 정보가 있을 때
                 # 서버가 전송을 원하는데 (frame_transmission_enabled=True) 실제 파이프라인이 안돌면 degraded
                if cm.cameras[0].get('frame_transmission_enabled') and not streaming_pipeline_active:
                    agent_overall_status = "degraded"
                    is_transmitting_when_should = False
            # 장치가 없으면 error
            if not camera_device_ok:
                agent_overall_status = "error"
                is_transmitting_when_should = False # 장치가 없으므로 전송 불가

        return {
            "status": agent_overall_status,
            "agent_id": cm.agent_id,
            "camera_device_available": camera_device_ok,
            "streaming_pipeline_active": streaming_pipeline_active,
            "configured_streaming_method": current_streaming_method,
            "expected_vs_actual_transmission": is_transmitting_when_should,
            "visibility_server_url": app.state.server_url if hasattr(app.state, 'server_url') else "N/A",
            "uptime_seconds": time.time() - app.state.start_time
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        uptime = time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
        return {"status": "error", "detail": str(e), "uptime_seconds": uptime}