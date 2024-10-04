"""

처음 agent 가 실행시 register_agent() 실행,
등록 실패시 일단 agent 종료하도록함

해당 코드는 처음 등록할때 서버에 등록 및 FAST API 서버 실행되도록함
FAST API 는 후에 gRPC 로 대체될 수 있음

최근 작성일 240930 송인용

"""

# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI()
# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용 (필요에 따라 특정 도메인으로 제한 가능)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rtsp_server = RTSPServer()
rtsp_server.start()
SERVER_URL = 'http://10.32.187.108:5111'


# Agent 등록 초기에 서버에 agent가 정상적으로 등록이 성공해야만 Agent 가 정상적으로 활성화 되도록 수정
def register_agent():
    rtsp_allowed_ip_range = '0.0.0.0/0'
    agent_info = {
        "agent_name": os.getenv("AGENT_ID", "default_agent"),
        "rtsp_port": rtsp_server.server.props.service,
        "agent_port": os.getenv("AGENT_PORT", 8000),
        "mount_point": rtsp_server.mount_point,
        "rtsp_allowed_ip_range": rtsp_allowed_ip_range
    }
    try:
        # 서버에 등록이 성공했을때, 이후 로직 구현
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
            exit(1)  # 프로그램 종료

# CameraManager 초기화 및 시작
camera_manager = CameraManager(rtsp_server, agent_id, SERVER_URL) 
camera_manager.start()

# PTP 동기화 시작
ptp_thread = threading.Thread(target=synchronize_with_ptp_server, daemon=True)
ptp_thread.start()

@app.post("/start_stream")
def start_stream():
    rtsp_server.start_stream()
    return {"message": "스트리밍을 시작했습니다."}

@app.post("/stop_stream")
def stop_stream():
    rtsp_server.stop_stream()
    return {"message": "스트리밍을 중지하고 빈 영상을 송출합니다."}

@app.get("/camera_info")
def get_camera_info():
    # 카메라 정보를 반환
    return {
        "camera_found": camera_manager.camera_found,
        "stream_uri": rtsp_server.get_stream_uri(),
    }

@app.post("/shutdown")
def shutdown():
    # 애플리케이션 종료
    camera_manager.stop()
    rtsp_server.loop.quit()
    return {"message": "Agent를 종료합니다."}

@app.get("/health")
def health_check():
    
    # 서버가 에이전트의 연결 상태를 확인하기 위한 엔드포인트.
    
    return {"status": "ok"}