# Camera Status Visibility Server

## 프로젝트 개요


Camera Status Visibility Server는 여러 데스크탑 에이전트로부터 카메라 상태 정보를 수집하고 관리하며, 사용자에게 API를 통해 카메라 상태 조회 및 제어 기능을 제공합니다.

DB는 등록된 Agent 들 정보 관리정도로만 사용하고 있는데 지금은 간단하게 tinyDB 사용해서 서버 컨테이너 새로 생성되면, 데이터 초기화하도록 해둠
만약 필요하면 MobileX 에 배포한 PostgreSQL 같은 DB 사용하면됨

## 주요 기능

- **에이전트 상태 업데이트**: 에이전트는 주기적으로 자신의 카메라 상태를 서버에 전송합니다.
- **에이전트 설정 조회**: 에이전트는 서버로부터 프레임 전송 설정을 가져옵니다.
- **카메라 상태 조회**: 사용자는 해당 서버를 통해 에이전트의 카메라 상태를 조회할 수 있습니다.
- **프레임 전송 설정 변경**: 사용자는 해당 서버를 특정 에이전트의 프레임 전송 활성화 여부를 변경할 수 있습니다.
- **Swagger 통합**: 해당 서버 API 문서를 자동으로 생성하여 Swagger UI를 통해 확인할 수 있습니다.

## 디렉토리 구조


## 주요 파일 설명

- **`app.py`**: Flask 애플리케이션을 초기화하고 실행하는 진입점입니다.
- **`config.py`**: 환경 변수 및 설정 값을 관리합니다.
- **`connections.py`**: 데이터베이스, Spark, Kafka등 외부 서비스 연결을 초기화하고 관리합니다.


### **디렉토리**

- **`models/`**: 데이터 모델을 정의하는 모듈을 포함합니다.
  - **`agent.py`**: 에이전트 관련 데이터 모델을 정의합니다.

- **`resources/`**: API 엔드포인트(Resource)를 정의하는 모듈을 포함합니다.
  - **`agent_resources.py`**: 에이전트 통신 관련 API 엔드포인트를 정의
  - **`user_resources.py`**: 사용자가 agent 조작 관련 API 엔드포인트를 정의
  - **`webui_resources.py`**: webui 에서 간단한 CRUD 관련 API 엔드포인트를 정의
- **`utils/`**: 공용 함수나 유틸리티 코드를 포함합니다.
  - **`common.py`**: 프로젝트 전반에서 사용하는 공통 함수 묶음

- **`docs/`**: Swagger 문서 파일을 저장합니다.
  - **`agent_get_config.yml`**, **`agent_update_status.yml`** 등: 각 API 엔드포인트에 대한 Swagger 문서

## 설치 및 실행 방법

이미지 빌드 예시
docker build -t camera-status-server .

컨테이너 실행 예시
docker run -d -p 5111:5111 camera-status-server

Swagger API 문서 접속 그런데 25년도 패치 반영안해나서 아마 안될듯 ㅋㅋ
/apidocs/

접속 예시
http://10.32.187.108:5111/apidocs/

### **필요한 패키지 설치**

```bash
pip install -r requirements.txt
