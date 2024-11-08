# Camera-agent

MobileX-station 이나 Husky Robot 등 카메라들에 컨테이너 베이스로 배포하여 

Gstreamer 기반으로 업데이트 하였으며

Visibility Server 와 통신하면서 카메라 정보 조회 및 파이프라인에 on/off 기능을 담당한다.

그 외 Prometeus 로 네트워크 트래픽 전송 수집 및 사용량등 visibility 정보들 수집

빠르게 개발하고, 현재 통신 정도는 FAST API 로 개발해도 문제 없을꺼라 판단해서 우선 FAST API 기반으로 Agent 실행


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
docker run --rm -it \
    --device /dev/video0:/dev/video0 \
    -e VISIBILITY_SERVER_URL=http://your_server:5000 \
    -e RTSP_SERVER_IP=rtsp_server_ip \
    -e RTSP_SERVER_PORT=8554 \
    agent

docker run -e STREAMING_METHOD=KAFKA \
           -e KAFKA_TOPIC=my_topic \
           -e KAFKA_BOOTSTRAP_SERVERS=broker:9092 \
           -e FRAME_RATE=5 \
           -e IMAGE_WIDTH=640 \
           -e IMAGE_HEIGHT=480 \

아래 내용은 설계 변경으로 FAST API 로 기능 대체함
--------------------------------------------
서버측이 Agent 에 요청을 할때는 gRPC 메인으로 사용함 

gRPC 용 프로토콜 버퍼 생성은 다음과 같음

python -m grpc_tools.protoc -I./models/grpc_proto --python_out=./models/grpc_proto --grpc_python_out=./models/grpc_proto ./models/grpc_proto/agent.proto

