# Camera-agent

MobileX-station 등 베어메탈 Node 들에 컨테이너 배포하면 웹캠 카메라등을 CCTV 처럼 활용할 수 있도록 지원해주는 Agent 코드이다.



베어메탈 버전 Camera Agent Gstreamer 기반으로 개발되었으며, Visibility Server 와 통신하면서 카메라 정보 조회 및 파이프라인에 on/off 기능을 담당한다.
빠르게 개발하고, 현재 서버와 통신 부분은 기존 설계인 grpc 대신  FAST API 기반으로 개발해둠둠


250518: 기존 RTSP 기능 뿐만 아니라 Kafka 버전 스트리밍도 안정적으로 잘 됨을 확인


미 구현:
PTP 동기화/ 호스트 머신에 ptpd 사전 설치 필요 -> 시간상 생략략
그 외 Prometeus 로 네트워크 트래픽 전송 수집 및 사용량등 visibility 정보들 수집 -> 여유 있으면 추가 개발 마무리는 고민

주의:

초기 설계 목표대로 AI 대학원이나 지스트 내 다른 건물 로컬망에서만 센싱을 위한 정도는 문제 없겠으나
만약 해당 코드를 지속적으로 사용해서 외부망에서 진행되는 과제등에서도 사용되게 된다면 꼭 현재와 같이 Agent 내에 ID 기록 및 관리하는 구조 나 인증 부분 전부 고치고 사용하삼삼


애플리케이션 실행

uvicorn app.main:app --reload --host 0.0.0.0

curl -X POST http://localhost:8000/start_stream

### PTP 서버 권한 허용

Agent 
하드웨어 레벨, 특히 네트워크 인터페이스 카드 수준
sudo setcap cap_net_bind_service,cap_net_admin,cap_net_raw+ep $(which ptpd2)

---

주요 기능
연결된 카메라를 검색하고 관리합니다.

초기화 과정
에이전트는 컨테이너 기반으로 배포되며, 시작 시 서버에 자신의 존재를 알리고, 필요한 설정 정보를 받아온다.


카메라 모델명을 감지하여 필요시 agent에서 모델별 고급 기능을 지원합니다.(구현 예정)


프레임 전송
서버로부터 받은 설정에 따라 프레임 전송을 동적으로 on/off 합니다.

- **에이전트 상태 정보 전송**
  - 에이전트는 주기적으로 카메라 상태 정보를 서버의 API로 전송합니다.

- **gRPC를 통한 에이전트 제어**
  - 서버는 gRPC를 통해 에이전트에 명령을 보내 스트리밍을 시작하거나 중지시킬 수 있습니다.

- **프로메테우스를 통한 메트릭 전송**
  - 에이전트는 프로메테우스를 통해 메트릭을 전송합니다.



에이전트는 서버로부터 명령을 수신하여 동작을 변경할 수 있습니다.
예: 카메라 정보 조회 주기를 동적으로 업데이트
메트릭 전송
프로메테우스를 통해 네트워크 사용량 및 카메라 개수 등의 메트릭을 전송합니다.


docker build -t agent .

# RTSP 통신 스트리밍 모드 실행 예시시

docker run -d --rm \
    --network host \
    --name my-rtsp-camera-agent \
    --device /dev/video0:/dev/video0 \
    -e VISIBILITY_SERVER_URL="http://10.32.187.108:5111" \
    -e AGENT_NAME="RTSP_Camera_Agent_01" \
    -e AGENT_PORT="8000" \
    -e STREAMING_METHOD="RTSP" \
    -e CAMERA_DEVICE_PATH="/dev/video0" \
    -e CAMERA_ID_OVERRIDE="a1b2c3d4-e5f6-7890-1234-567890abcdef" \
    -e CAMERA_NAME="현관 앞 카메라 (RTSP)" \
    -e CAMERA_TYPE="rgb" \
    -e CAMERA_ENVIRONMENT="real" \
    -e CAMERA_RESOLUTION="1280x720" \
    -e CAMERA_FPS="25" \
    -e CAMERA_LOCATION="현관 입구" \
    -e RTSP_SERVER_LISTEN_PORT="8554" \
    -e RTSP_MOUNT_POINT="/live_stream_01" \
    ttyy441/camera-agent:<tag>


# KAFKA 통신 스트리밍 모드 실행 예시시

docker run  --rm \
    --network host \
    --name my-kafka-camera-agent \
    --device /dev/video0:/dev/video0 \
    -e VISIBILITY_SERVER_URL="http://10.32.187.108:5111" \
    -e AGENT_NAME="Kafka_Camera_Agent_01" \
    -e AGENT_PORT="8000" \
    -e STREAMING_METHOD="KAFKA" \
    -e CAMERA_DEVICE_PATH="/dev/video0" \
    -e CAMERA_ID_OVERRIDE="kfk-cam-uuid-001" \
    -e CAMERA_NAME="공정라인 A 카메라 (Kafka)" \
    -e CAMERA_TYPE="rgb" \
    -e CAMERA_ENVIRONMENT="real" \
    -e CAMERA_RESOLUTION="1280x720" \
    -e CAMERA_FPS="20" \
    -e CAMERA_LOCATION="원장실 방" \
    -e KAFKA_TOPIC="camera-agent-01" \
    -e KAFKA_BOOTSTRAP_SERVERS="10.79.1.1:9094" \
    ttyy441/camera-agent:<tag>

