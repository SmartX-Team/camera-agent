## 주요 컴포넌트 및 기능

### 1. Agent
주요 스택: FAST API(gRPC로 대체될 수 있음), Gstreamer

목적: Gstreamer 기반으로 웹캠과 같은 일반 카메라 장비를 IP 카메라 처럼 사용할수 있도록 지원하고, 카메라 상태를 주기적으로 Visibility Server 에 주기적으로 전송

또한 스트리밍 on/off 등 동적으로 조절할 수 있는 API를 지원하여, 네트워크 상태등에 따라 유동적으로 생성되는 데이터 크기를 조절할 수 있음

Rtsp 프로토콜로 스트리밍 되기에 여러 서비스에서 동시에 카메라의 데이터에 접근하기 수월해지고, 전체 시스템를 관리하기도 쉬어짐

--

#### 주요 기능:
- [x] 기능 1: Gstreamer 기반으로 일반 카메라를 rtsp 프로토콜로 스트리밍할 수 있도록 지원
- [ ] 기능 2: PTP 프로토콜로 Agent들간 시간 동기화 (구현은 했으나 안정화 확인되면 이후에 다시 활성화할 예정)
- [ ] 기능 3: Prometheus 로 현재 Agent의 시스템 사용량 관리 

#### 구현된 세부 요구사항:
- [x] 요구사항 1: Agent 생성시 Visibility Server 에 등록 API 호출
- [x] 요구사항 2: 주기적으로 Visibility Server에 카메라 상태 업데이트
- [x] 요구사항 3: FAST API 기반 스트리밍 송출 on/off 구현
- [ ] 요구사항 4: PTP 프로토콜 동기화 (가능은 한데 안전성 때문에 현재 실 사용은 안하고 있음)
- [ ] 요구사항 5: UWB 서버 연동하여 현재 웹캠카메라가 설치된 Host PC 의 위치좌표 web_ui 에 같이 노출하기
- [ ] 요구사항 6: 쿠버네티스 API와 연동하여 현재 Agent가 돌아가고 있는 PC의 Name web_ui 에 같이 노출하기


자세한 정보: [Agent/README.md](Agent/README.md)

### 2. Visibility Server
주요 스택: Flask, tinyDB

목적: Agent 들의 현재 상태를 관리하고, 사용자가 사용하는 WebUI 를 위해 기본적인 CRUD 기능 지원


#### 주요 기능:
- [x] 기능 1: Agent 가 신규 등록시 DB 에 관련 정보 유지 및 관리
- [x] 기능 2: 사용자가 Agent의 카메라 조작 가능한 엔드포인트 API 제공
- [x] 기능 3: 사용자가 사용하는 web-ui 에서 사용가능한 엔드포인트 API 제공
- [x] 기능 4: 프로메테우스 서버 연동하여 agent 들의 컴퓨팅 사용량 조회

#### 구현된 요구사항:
- [x] 기능 1 관련:
  - [x] 1.1: Agent 신규 등록 시 필요한 정보 정의 및 DB 스키마 Open API 등과 연계
  - [x] 1.2: Agent 정보 등록, 조회, 수정 API 구현
  - [x] 1.3: DB에 동일 IP 대역이 있으면 신규 ID 발급하지 말고 기존 agent 정보에 업데이트 지원

- [x] 기능 2 관련:
  - [x] 2.1: Agent 스트림(on/off) 조작 API 구현

- [x] 기능 3 관련:
  - [x] 3.1: web-ui용 Agent 목록 조회 API 구현
  - [x] 3.2: web-ui용 Agent 상세 정보 조회 API 구현

- [ ] 기능 4 관련:
  - [ ] 4.1: 프로메테우스 연동을 위한 메트릭 수집 및 제공 기능 구현

#### 비기능적 요구사항:
- [] NFR 1: Agent들은 기본 컨테이너 단위로 동작하며, Agent 삭제 기능은 Argo CD 와 같은 툴을 이용해 구현예정임


자세한 정보: [Backend/README.md](Backend/README.md)

### 3. PTP Server
목적: Agent들의 시간 동기화를 위한 컨테이너 기반 PTP 서버

#### 주요 기능:
- [x] 기능 1: [설명]
#### 구현된 요구사항:
- [x] 요구사항 1: [설명]

자세한 정보: 

### 4. WebUI
**목적**: Agent들의 관리를 위한 WebUI 

#### 주요 기능:
- [x] 기능 1: Agent가 신규 등록 시 DB에 관련 정보 유지 및 관리
- [x] 기능 2: 사용자가 Agent의 카메라를 제어할 수 있는 엔드포인트 API 제공
- [x] 기능 3: 사용자가 사용하는 WebUI에서 사용 가능한 엔드포인트 API 제공
- [ ] 기능 4: Prometheus 서버 연동하여 Agent들의 컴퓨팅 자원 사용량 조회
- [x] 기능 5: CORS 설정을 통한 Cross-Origin 요청 허용
- [x] 기능 6: rtsp 프로토콜 말고도 다른 프로토콜로 비디오 데이터 처리 구현 필요

#### 구현된 요구사항:

- 기능 1 관련:
  - [x] 1.1: Agent 신규 등록 시 필요한 정보 정의 및 DB 스키마, OpenAPI 연계
    - `rtsp_port`와 `agent_port`를 분리하여 저장하도록 DB 스키마 수정
    - Swagger 문서(`agent_register.yml`)에 `agent_port` 필드 추가
  - [x] 1.2: Agent 정보 등록, 조회, 수정 API 구현
    - `AgentRegister` 클래스에서 `agent_port`를 처리하도록 수정
    - `AgentModel`과 `Database` 클래스에서 `agent_port`를 저장 및 관리하도록 수정
  - [x] 1.3: DB에 동일 IP가 있으면 신규 ID 발급하지 않고 기존 Agent 정보 반환
    - TinyDB 쿼리 및 데이터 구조 수정으로 중복 등록 문제 해결
    - IP 주소를 기준으로 기존 Agent 검색 및 반환 로직 구현

- 기능 2 관련:
  - [x] 2.1: Agent 스트림(On/Off) 제어 API 구현
    - `SetFrameTransmission` 엔드포인트에서 Agent의 IP와 포트를 통해 스트림 제어 명령 전송
    - Agent의 `/start_stream` 및 `/stop_stream` 엔드포인트와 연동
  - [x] 2.2: Agent의 API 포트를 사용하여 통신하도록 수정
    - Agent 등록 시 `agent_port` 정보를 포함하여 서버에 전달
    - 서버에서 Agent의 `agent_port`를 사용하여 통신

- 기능 3 관련:
  - [x] 3.1: WebUI용 Agent 목록 조회 API 구현
    - Agent 목록을 반환하는 엔드포인트 구현
  - [x] 3.2: WebUI용 Agent 상세 정보 조회 API 구현
    - 특정 Agent의 상세 정보를 반환하는 엔드포인트 구현
  - [x] 3.3: CORS 설정을 통해 WebUI에서 API 호출 가능하도록 설정
    - Flask와 FastAPI 애플리케이션에서 CORS 설정 추가

- **기능 4 관련:**
  - [ ] **4.1**: Prometheus 연동을 위한 메트릭 수집 및 제공 기능 구현
    - **진행 중**: Prometheus와의 연동을 위한 메트릭 수집 기능 개발 필요

- 기능 5 관련:
  - [x] 5.1: CORS 설정을 통한 Cross-Origin 요청 허용
    - Flask 앱에서 `flask_cors`를 사용하여 CORS 설정 추가
    - FastAPI 앱에서 `CORSMiddleware`를 사용하여 CORS 설정 추가
  - [x] 5.2: Preflight 요청에 대한 처리 로직 추가
    - OPTIONS 메서드를 허용하고 적절한 CORS 헤더를 반환하도록 수정

#### 비기능적 요구사항:
- [] NFR 1: Web-UI 는 빠른 개발을 위해 제이쿼리 위주의 간단한 UI 버전 과 이후 세부적인 기능을 위한 전문 프레임워크를 사용한 버전 추가 개발 요청
---