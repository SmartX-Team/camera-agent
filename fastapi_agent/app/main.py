# app/main.py
from fastapi import FastAPI
from .rtsp_server import RTSPServer
import threading

app = FastAPI()
rtsp_server = RTSPServer()
rtsp_server.start()

@app.post("/start_stream")
def start_stream():
    rtsp_server.start_stream()
    return {"message": "스트리밍을 시작했습니다."}

@app.post("/stop_stream")
def stop_stream():
    rtsp_server.stop_stream()
    return {"message": "스트리밍을 중지하고 빈 영상을 송출합니다."}
