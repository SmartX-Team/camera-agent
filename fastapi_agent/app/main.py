# app/main.py
from fastapi import FastAPI
from .rtsp_server import RTSPServer
from .camera_manager import CameraManager
import threading
import logging
import os
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
rtsp_server = RTSPServer()
rtsp_server.start()
SERVER_URL = 'http://10.32.187.108:5000'


# Agent 등록 초기에 서버에 agent가 정상적으로 등록이 성공해야만 Agent 가 정상적으로 활성화 되도록 수정
def register_agent():
    agent_info = {
        "agent_name": os.getenv("AGENT_ID", "default_agent"),
        "agent_ip": rtsp_server.server.props.address,
        "rtsp_port": rtsp_server.server.props.service,
        "stream_uri": rtsp_server.get_stream_uri(),
    }
    try:
        # 서버에 등록이 성공했을때, 이후 로직 구현
        response = requests.post(f"{SERVER_URL}/agent/register", json=agent_info)
        if response.status_code == 200 or response.status_code == 201 :
            print("Agent registered successfully.")
            # 서버로부터 추가 정보를 수신(할당된 id, 프로메테우스 현재 서버 주소등)
            data = response.json()
            agent_id = data.get("agent_id")

            logger.info(f"Agent registered successfully. Agent ID: {agent_id}")
            return agent_id
        else:
            print(f"Agent 등록 실패: {response.status_code}")
            logger.error(f"Agent registration failed: {response.status_code} {response.text}")
            return None

    except Exception as e:
        print(f"Failed to register agent: {e}")
        return None


agent_id = register_agent()

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