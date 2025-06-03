# camera-agent Project

## 프로젝트 소개

이 프로젝트는 컨테이너 베이스로 멀티 카메라를 대상으로 유연성과 기능성을 제공함으로써, 코드 재사용성을 높이고 디지털 트윈 프로젝트와 연계하여 개발 진행 예정입니다. 

Camera Agent Project는 컨테이너 기반으로 MobileX Station등 카메라가 장착된 Box들에 컨테이너 배포하면, IP 카메라처럼 카메라 영상을 실시간 스트리밍하여, AI 추론 및 DT 서비스 개발에 활용할 수 있게 하는 프로젝트로 초기 Falcon을 보완하기 위해 진행되었으며, 지금은 물리/가상/ROS2 토픽의 카메라들을 대상으로 스트리밍을 지원합니다.

1. **웹캠을 IP 카메라로 변환**: 기존 MobileX Station등 저희 공간안의 Box들에  웹캠을 IP 카메라와 같은 기능성을 가진 장치로 전환합니다. 이를 통해 네트워크를 통한 원격 접근과 제어가 가능해집니다.

2. **중앙화된 카메라 관리**: WebUI를 통해 현재 사용 가능한 모든 카메라의 목록을 확인하고 관리할 수 있습니다. 이는 시스템 관리자에게 직관적이고 효율적인 카메라 관리 환경을 제공합니다.

3. **AI 서비스에 메타데이터 제공**: 특정 카메라들을 다른 AI 서비스들에 적용할지 선택할 수 있는 API 를 제공하여, AI 서비스의 유연성을 높였습니다.




### REPO 의 주요 구성 요소


web-UI 는 현재는 light 버전만 지원됩니다.



## 전체 구조도

ver 240930
![Falcon 설계 고민사항](https://github.com/user-attachments/assets/79894cc2-47da-423d-92b1-04e40496439a)


# Camera Agent based Streamer-Process-Service 3tier-Architecture 
![Camera Agent 3계층 아키텍처](/docs/images/3tier-architecture.png)

## 계층별 역할

### 🎥 Streamer Layer
- **Physical/Virtual Camera**: ROS, Omniverse 카메라 소스
- **Camera-Agent**: GStreamer 기반 RTSP 스트리밍
- **Agent-Visibility**: 실시간 상태 관리 및 UI

### ⚙️ Process Layer  
- **Spark Application**: 대용량 스트림 데이터 처리
- **Delta Lake**: 실시간 데이터 레이크 저장
- **Falcon-wrapper-service**: AI 추론 서비스 연동

### 🚀 Service Layer
- **Falcon Inference**: AI 기반 분석 결과
- **Kit Extension**: Omniverse 통합
- **USD**: 3D 시각화 및 Digital Twin


Web-UI 동작 예시

<img width="1438" alt="스크린샷 2024-10-04 오전 10 00 21" src="/docs/images/agent-ui.png">



자세한 정보: 
## 설치 및 실행 방법

모든 서버 기능들은 컨테이너 베이스로 유지됨, 도커 파일은 프로젝트마다 있음
MobileX 에서는 K8S 에 자동 배포 유지되도록 세팅 해둘것임


