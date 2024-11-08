"""

Pod Deployment 로 배포할때 환경변수 load 하는 사긴이랑 모듈 import 시간 문제로 인식 안되길래 해당 문제 개선


처음 agent 가 실행시 register_agent() 실행,
등록 실패시 일단 agent 종료하도록함

해당 코드는 처음 등록할때 서버에 등록 및 FAST API 서버 실행되도록함
FAST API 는 후에 gRPC 로 대체될 수 있음

최근 작성일 240930 송인용

"""

from fastapi import FastAPI
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global camera_manager, ptp_thread

    STREAMING_METHOD = os.getenv('STREAMING_METHOD', 'RTSP').upper()
    KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'my_topic')
    KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    FRAME_RATE = int(os.getenv('FRAME_RATE', 5))
    IMAGE_WIDTH = int(os.getenv('IMAGE_WIDTH', 640))
    IMAGE_HEIGHT = int(os.getenv('IMAGE_HEIGHT', 480))

    app.state.streaming_method = STREAMING_METHOD
    app.state.kafka_topic = KAFKA_TOPIC
    app.state.bootstrap_servers = KAFKA_BOOTSTRAP_SERVERS

    # RTSP 서버 초기화 (RTSP 방식일 경우)
    if STREAMING_METHOD == 'RTSP':
        app.state.streaming_server = RTSPServer()
        app.state.streaming_server.start()
    elif STREAMING_METHOD == 'KAFKA':
        app.state.streaming_server = None
    else:
        app.state.streaming_server = None

    SERVER_IP = os.getenv('SERVER_IP', '10.32.187.108')  # 기본값 설정
    SERVER_PORT = os.getenv('SERVER_PORT', '5111')    # 기본 포트 설정
    SERVER_URL = f'http://{SERVER_IP}:{SERVER_PORT}'

    logger.info(f"SERVER_IP: {SERVER_IP}")
    logger.info(f"SERVER_PORT: {SERVER_PORT}")
    logger.info(f"SERVER_URL: {SERVER_URL}")
    logger.info(f"AGENT_ID: {os.getenv('AGENT_ID')}")
    logger.info(f"AGENT_PORT: {os.getenv('AGENT_PORT')}")

    # Agent 등록 함수 정의
    def register_agent():
        rtsp_allowed_ip_range = '0.0.0.0/0'
        agent_info = {
            "agent_name": os.getenv("AGENT_ID", "default_agent"),
            "rtsp_port": app.state.rtsp_server.server.props.service,
            "agent_port": os.getenv("AGENT_PORT", 8000),
            "mount_point": app.state.rtsp_server.mount_point,
            "rtsp_allowed_ip_range": rtsp_allowed_ip_range
        }
        logger.info(f"Agent configuration: {agent_info}")
        try:
            # 서버에 등록이 성공했을 때, 이후 로직 구현
            response = requests.post(f"{SERVER_URL}/agent/register", json=agent_info)
            data = response.json()
            if response.status_code == 201:
                # 새로 등록된 경우
                agent_id = data.get("agent_id")
                print("Agent registered successfully.")
                logger.info(f"Agent registered successfully. Agent ID: {agent_id}")
                return agent_id

            elif response.status_code == 200:
                # 이미 등록된 경우
                agent_id = data.get("agent_id")
                print("Agent already registered. Using existing registration.")
                logger.info(f"Agent already registered. Agent ID: {agent_id}")
                return agent_id
            else:
                print(f"Agent 등록 실패: {response.status_code}")
                logger.error(f"Agent registration failed: {response.status_code} {response.text}")
                return None

        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            return None

    max_retries = 3  # 최대 재시도 횟수 설정
    retry_delay = 5  # 재시도 사이의 대기 시간 (초)

    for attempt in range(max_retries):
        agent_id = register_agent()
        if agent_id is not None:
            break  # 등록 성공 시 반복 종료
        else:
            logger.error(f"Registration attempt {attempt + 1} failed.")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("Max registration attempts reached. Exiting program.")
                # FastAPI 애플리케이션에서 종료하려면 예외를 발생시킨다.
                raise RuntimeError("Max registration attempts reached.")
            
    kafka_params = {
        'topic': KAFKA_TOPIC,
        'bootstrap_servers': KAFKA_BOOTSTRAP_SERVERS,
        'frame_rate': FRAME_RATE,
        'image_width': IMAGE_WIDTH,
        'image_height': IMAGE_HEIGHT,
    }

    # CameraManager 초기화 및 시작
    camera_manager = CameraManager(
        streaming_server=app.state.streaming_server,
        agent_id=agent_id,
        server_url=SERVER_URL,
        streaming_method=STREAMING_METHOD,
        kafka_params=kafka_params
    )
    camera_manager.start()

    # PTP 동기화 시작
    #ptp_thread = threading.Thread(target=synchronize_with_ptp_server, daemon=True)
    #ptp_thread.start()

    # 애플리케이션이 실행되는 동안 유지시킴
    yield

    # 애플리케이션 종료 시 행동
    camera_manager.stop()
    if STREAMING_METHOD == 'RTSP' and app.state.streaming_server:
        app.state.streaming_server.loop.quit()
    logger.info("Application shutdown completed.")

app = FastAPI(lifespan=lifespan)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용 (필요에 따라 특정 도메인으로 제한 가능)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/start_stream")
def start_stream():
    app.state.rtsp_server.start_stream()
    return {"message": "스트리밍을 시작"}

@app.post("/stop_stream")
def stop_stream():
    app.state.rtsp_server.stop_stream()
    return {"message": "스트리밍을 중지하고 빈 영상을 송출"}

@app.get("/camera_info")
def get_camera_info():
    camera_info = camera_manager.get_camera_info()
    response = {
        "camera_found": len(camera_info) > 0,
        "camera_list": camera_info
    }
    if app.state.streaming_method == 'RTSP' and app.state.streaming_server:
        response.update({
            "stream_uri": app.state.streaming_server.get_stream_uri(),
        })
    elif app.state.streaming_method == 'KAFKA' and camera_manager.kafka_streamer:
        response.update({
            "kafka_topic": app.state.kafka_topic,
            "bootstrap_servers": app.state.bootstrap_servers,
        })
    return response

@app.post("/shutdown")
def shutdown():
    # 애플리케이션 종료
    camera_manager.stop()
    app.state.rtsp_server.loop.quit()
    return {"message": "Agent를 종료"}

@app.get("/health")
async def health_check():
    try:
        rtsp_status = app.state.rtsp_server.check_status()
        camera_status = app.state.camera_manager.check_status()
        return {
            "status": "ok" if rtsp_status and camera_status else "degraded",
            "rtsp_server": rtsp_status,
            "camera": camera_status,
            "last_error": None,
            "uptime": time.time() - app.state.start_time
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }