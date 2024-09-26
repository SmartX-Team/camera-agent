import cv2
import requests
import threading
import time
import os

# AI 서버의 엔드포인트 URL 설정
AI_SERVER_URL = os.environ.get('AI_SERVER_URL', 'http://ai-server.example.com/receive_frame')

# 프레임 전송 활성화 여부 설정
SEND_FRAMES = os.environ.get('SEND_FRAMES', 'false').lower() == 'true'

# 카메라 인덱스 탐색 범위 설정
MAX_CAMERA_INDEX = 5  # 필요에 따라 조정 가능

def list_cameras():
    cameras = []
    for index in range(MAX_CAMERA_INDEX):
        cap = cv2.VideoCapture(index)
        if cap is None or not cap.isOpened():
            cap.release()
            continue
        else:
            cameras.append(index)
            cap.release()
    return cameras

def send_frame(frame, camera_id):
    # 프레임을 JPEG로 인코딩
    ret, jpeg = cv2.imencode('.jpg', frame)
    if not ret:
        print(f"카메라 {camera_id}: 프레임 인코딩 실패")
        return

    # 프레임 전송
    try:
        response = requests.post(
            AI_SERVER_URL,
            files={'image': ('frame.jpg', jpeg.tobytes(), 'image/jpeg')},
            data={'camera_id': camera_id},
            timeout=5
        )
        if response.status_code == 200:
            print(f"카메라 {camera_id}: 프레임 전송 성공")
        else:
            print(f"카메라 {camera_id}: 프레임 전송 실패 - 상태 코드 {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"카메라 {camera_id}: 프레임 전송 중 예외 발생 - {e}")

def camera_worker(camera_id):
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        print(f"카메라 {camera_id}: 열기 실패")
        return

    print(f"카메라 {camera_id}: 시작")
    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"카메라 {camera_id}: 프레임 읽기 실패")
            break

        if SEND_FRAMES:
            send_frame(frame, camera_id)

        # 프레임 처리 주기 설정 (예: 1초마다 프레임 캡처)
        time.sleep(1)

    cap.release()
    print(f"카메라 {camera_id}: 종료")

def main():
    cameras = list_cameras()
    if not cameras:
        print("연결된 카메라가 없습니다.")
        return

    print(f"연결된 카메라 목록: {cameras}")

    threads = []
    for camera_id in cameras:
        t = threading.Thread(target=camera_worker, args=(camera_id,))
        t.start()
        threads.append(t)

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("에이전트 종료 중...")

if __name__ == '__main__':
    main()
