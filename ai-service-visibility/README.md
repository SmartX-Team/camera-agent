# AI 서비스 설정 서버 (ai-service-visibility-server)

## 1. 개요

본 서비스는 Falcon 프로젝트의 AI 서비스들들(EX: `falcon-wrapper-service`)에 필요한 설정 정보를 중앙에서 관리하고 제공하는 역할을 한다. 사용자는 이 서버의 API를 통해 특정 카메라 스트림과 UWB(초광대역) 태그를 연동하고, 관련 설정을 Redis에 저장할 수 있습니다. `falcon-wrapper-service`등 AI Inferece Model 에 삽입을 지원해주는 Wrapper 서비스들은 Redis에 저장된 서비스 설정 정보 테이블 key-value를 주기적으로 읽어 동적으로 데이터 소스를 관리하고 처리 파이프라인을 구성합니다.

이를 통해 AI 서비스의 입력 소스를 실시간으로 유연하게 변경하고, Visibility 서버로부터 최신 카메라 정보를 반영하며, UWB 데이터등 다른 센서 데이터를 영상 스트리밍 데이터와 통합하는 과정을 지원합니다.

## 2. 핵심 기능

* **서비스 설정 등록 및 조회:**
    * AI 서비스(예: `falcon-wrapper-service`의 특정 인스턴스)에 대한 설정을 생성, 업데이트 및 조회합니다.
    * 설정 정보에는 사용할 카메라 정보(Visibility 서버로부터 동적으로 조회), 매핑할 UWB 태그 ID, UWB 데이터 처리 방식 등이 포함됩니다.
    * 모든 설정 정보는 `falcon-wrapper-service`가 소비할 수 있는 표준화된 JSON 형식으로 Redis에 저장됩니다.
* **활성 카메라 목록 제공:**
    * 연동된 Visibility 서버로부터 현재 사용 가능한 (활성 상태이며, 특정 오류 상태가 아닌) 카메라 목록과 상세 정보를 제공합니다.
    * 클라이언트(예: UI)는 이 정보를 바탕으로 서비스 설정 시 카메라를 선택할 수 있습니다.
* **UWB 데이터 조회:**
    * 연결된 PostgreSQL 데이터베이스에서 특정 UWB 태그 ID에 대한 최신 위치 정보를 조회하여 제공합니다.

## 3. 시스템 아키텍처 및 연동


1.  **클라이언트**는 `ai-service-config-server`의 API를 호출하여 새로운 서비스 설정을 등록하거나 기존 설정을 조회/업데이트합니다.
2.  설정 등록 시, `ai-service-config-server`는:
    a.  요청된 `input_camera_id`를 사용하여 **Visibility 서버**로부터 해당 카메라의 상세 정보(스트림 URL, 프로토콜 등)를 가져옵니다.
    b.  (선택적으로) 요청된 `input_uwb_tag_id`를 사용하여 **UWB 데이터베이스(PostgreSQL)** 에서 초기 UWB 데이터를 조회합니다.
    c.  수집된 정보를 바탕으로 `falcon-wrapper-service`가 이해할 수 있는 JSON 페이로드를 구성합니다.
    d.  구성된 페이로드를 **Redis**의 지정된 키 (`service_configs:<service_name>`)에 저장합니다.
3.  **`falcon-wrapper-service`** 는 주기적으로 Redis를 폴링하여 `service_configs:*` 패턴의 키들을 스캔하고, 변경된 설정을 감지하여 실시간으로 데이터 처리 파이프라인을 업데이트합니다.

## 4. API 엔드포인트

### 4.1. 서비스 설정 (Service Configuration)

#### `POST /service_configs`

새로운 서비스 설정을 등록하거나 기존 설정을 업데이트합니다.

* **요청 본문 (JSON):**
    ```json
    {
        "service_name": "cam_lobby_rtsp_01", // 서비스 설정의 고유 이름 (Redis 키 생성에 사용됨)
        "description": "Lobby RTSP camera with UWB tag 101, handled by postgresql", // 설명 (선택적)
        "input_camera_id": "uuid_of_camera_from_visibility_lobby", // Visibility 서버에 등록된 카메라의 고유 ID
        "input_uwb_tag_id": "101", // 이 카메라와 매핑될 UWB 태그 ID
        "uwb_handler_type": "postgresql", // "postgresql" 또는 "api". 없으면 wrapper의 기본값 사용 (선택적)
        "inference_config": { // 추론 서비스에 전달될 추가 설정 (선택적, 현재는 참고용)
            "model_name": "yolov5s",
            "confidence_threshold": 0.5
        }
    }
    ```
* **성공 응답 (201 Created):**
    ```json
    {
        "message": "Service configuration 'cam_lobby_rtsp_01' saved successfully to Redis.",
        "redis_key": "service_configs:cam_lobby_rtsp_01",
        "data_saved": {
            "service_name": "cam_lobby_rtsp_01",
            "description": "Lobby RTSP camera with UWB tag 101, handled by postgresql",
            "input_camera_id": "uuid_of_camera_from_visibility_lobby",
            "input_uwb_tag_id": "101",
            "uwb_handler_type": "postgresql",
            "visibility_camera_info": {
                "camera_name": "Lobby Cam (from Visibility)",
                "stream_protocol": "RTSP",
                "stream_details": {
                    "rtsp_url": "rtsp://[example.com/live/stream1](https://example.com/live/stream1)"
                },
                "camera_id_from_visibility_server": "uuid_of_camera_from_visibility_lobby",
                "agent_id": "agent_uuid_123",
                // ... 기타 Visibility 서버에서 가져온 카메라 정보
            },
            "initial_uwb_info_snapshot": { /* 등록 시점 UWB 데이터 스냅샷 */ },
            "inference_config": { /* 요청된 inference_config */ },
            "last_updated_utc": "2023-10-27T12:34:56.789Z"
        }
    }
    ```
* **오류 응답 (400, 404, 500 등):**
    ```json
    {
        "message": "Error message describing the issue."
    }
    ```

#### `GET /service_configs/<string:service_name>`

특정 서비스 설정을 Redis에서 조회합니다.

* **경로 파라미터:**
    * `service_name`: 조회할 서비스 설정의 이름.
* **성공 응답 (200 OK):**
    ```json
    {
        "redis_key": "service_configs:cam_lobby_rtsp_01",
        "data": { /* 저장된 서비스 설정 JSON 객체 */ }
    }
    ```
* **오류 응답 (404 Not Found 등):**
    ```json
    {
        "message": "Service configuration for 'cam_lobby_rtsp_01' not found in Redis (key prefix: 'service_configs:')."
    }
    ```

### 4.2. 활성 카메라 목록 (Active Cameras)

#### `GET /active_cameras`

Visibility 서버에서 사용 가능한 (특정 오류 상태가 아닌) 카메라 목록을 가져옵니다.

* **성공 응답 (200 OK):**
    ```json
    {
        "active_cameras": [
            {
                "agent_id": "agent_uuid_123",
                "agent_name": "Camera Agent 1",
                "camera_id": "uuid_of_camera_from_visibility_lobby",
                "camera_name": "Lobby Cam (from Visibility)",
                "camera_status": "streaming_rtsp",
                "stream_protocol": "RTSP",
                "stream_details": { "rtsp_url": "rtsp://[example.com/live/stream1](https://example.com/live/stream1)" },
                // ... 기타 카메라 정보
            },
            // ... 다른 활성 카메라 정보
        ],
        "count": 1 
    }
    ```
* **오류 응답 (500 Internal Server Error 등):**
    ```json
    {
        "message": "Failed to fetch camera list from Visibility Server."
    }
    ```

### 4.3. UWB 태그 데이터 (UWB Tag Data)

#### `GET /uwb_data/tags/<string:tag_id>`

PostgreSQL DB에서 특정 UWB 태그 ID의 최신 위치 데이터를 조회합니다.

* **경로 파라미터:**
    * `tag_id`: 조회할 UWB 태그 ID.
* **성공 응답 (200 OK):**
    ```json
    {
        "tag_id": "101",
        "data": {
            "id": 12345,
            "tag_id": "101",
            "x_position": 10.5,
            "y_position": 20.3,
            "raw_timestamp": "2023-10-27T12:30:00.000Z"
        }
    }
    ```
* **오류 응답 (404 Not Found, 500 Internal Server Error 등):**
    ```json
    {
        "message": "No UWB data found for tag_id '101'."
    }
    ```

## 5. 주요 의존성

* Python 3.9+
* Flask
* Flask-RESTful
* Flask-CORS
* psycopg2-binary (PostgreSQL 드라이버)
* redis (Python Redis 클라이언트)
* requests (HTTP 요청 라이브러리)
* python-dotenv (환경 변수 관리)

(전체 목록은 `requirements.txt` 참조)

## 6. 환경 변수 설정

본 서비스는 실행 환경에 따라 다음 환경 변수들을 설정해야 합니다. (`.env` 파일을 프로젝트 루트에 생성하여 관리할 수 있습니다.)

* **PostgreSQL 관련:**
    * `POSTGRES_HOST`: PostgreSQL 서버 호스트 (기본값: `10.79.1.13`)
    * `POSTGRES_PORT`: PostgreSQL 서버 포트 (기본값: `5432`)
    * `POSTGRES_USER`: PostgreSQL 사용자 이름
    * `POSTGRES_PASSWORD`: PostgreSQL 비밀번호
    * `POSTGRES_DB`: UWB 데이터가 저장된 데이터베이스 이름
    * `UWB_TABLE_NAME`: UWB 데이터 테이블 이름 (기본값: `uwb_raw`)
* **Redis 관련:**
    * `REDIS_HOST`: Redis 서버 호스트 (기본값: `localhost`)
    * `REDIS_PORT`: Redis 서버 포트 (기본값: `6379`)
    * `REDIS_DB_SERVICE_CONFIG`: 서비스 설정을 저장할 Redis DB 번호 (기본값: `0`)
    * `REDIS_PASSWORD`: Redis 비밀번호 (설정된 경우)
    * `REDIS_SERVICE_CONFIG_KEY_PREFIX`: Redis에 서비스 설정을 저장할 때 사용할 키 접두사 (기본값: `service_configs`)
* **Visibility 서버 관련:**
    * `VISIBILITY_SERVER_URL`: Visibility 서버의 기본 URL (예: `http://localhost:5111`)
* **서비스 자체 설정:**
    * `LOG_LEVEL`: 로깅 레벨 (예: `INFO`, `DEBUG`) (기본값: `INFO`)
    * `AI_CONFIG_SERVICE_PORT`: 본 서비스가 실행될 포트 (기본값: `5005`)

## 7. 실행 방법

1.  필요한 Python 라이브러리를 설치합니다:
    ```bash
    pip install -r requirements.txt
    ```
2.  필요한 환경 변수를 설정합니다. (예: `.env` 파일 생성 또는 직접 설정)
3.  Flask 개발 서버를 실행합니다:
    ```bash
    python app.py
    ```
    운영 환경에서는 Gunicorn과 같은 WSGI 서버 사용을 권장합니다.

## 8. `falcon-wrapper-service` 와의 연동

`ai-service-config-server`에 의해 Redis에 저장된 설정 정보 (키 패턴: `service_configs:*`)는 `falcon-wrapper-service`에 의해 주기적으로 폴링됩니다. `falcon-wrapper-service`는 이 정보를 바탕으로 다음을 수행합니다:

* `service_name`: 각 설정의 고유 식별자로 사용됩니다.
* `input_uwb_tag_id`: 해당 카메라 스트림과 융합할 UWB 태그를 식별합니다.
* `uwb_handler_type`: UWB 데이터를 가져올 방식(PostgreSQL 또는 API)을 결정합니다. (이 필드가 없으면 `falcon-wrapper-service`의 기본 설정 사용)
* `visibility_camera_info`:
    * `stream_protocol`: "RTSP" 또는 "KAFKA" 중 하나로, 입력 스트림의 종류를 나타냅니다.
    * `stream_details`:
        * RTSP인 경우: `{"rtsp_url": "..."}`
        * KAFKA인 경우: `{"kafka_topic": "...", "kafka_bootstrap_servers": "..."}` (만약 `kafka_bootstrap_servers`가 없으면 `falcon-wrapper-service`의 전역 Kafka 서버 설정 사용)

이러한 동적 설정을 통해 `falcon-wrapper-service`는 서비스 재시작 없이 실시간으로 입력 소스를 관리하고 변경 사항에 대응할 수 있습니다.
