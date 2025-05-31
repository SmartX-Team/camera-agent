# AI Service Configuration Server (ai-service-visibility-server)

## 1. Overview

This service acts as a central management and configuration provider for AI services in the Falcon project (e.g., `falcon-wrapper-service`). Users can use this server's API to connect specific camera streams with UWB (Ultra-Wideband) tags and store related configurations in Redis. AI Inference Model wrapper services like `falcon-wrapper-service` periodically read the service configuration table key-values stored in Redis to dynamically manage data sources and configure processing pipelines.

This enables real-time flexible changes to AI service input sources, reflects the latest camera information from the Visibility server, and supports the integration of UWB data and other sensor data with video streaming data.

## 2. Core Features

* **Service Configuration Registration and Retrieval:**
    * Create, update, and retrieve configurations for AI services (e.g., specific instances of `falcon-wrapper-service`).
    * Configuration information includes camera information to be used (dynamically retrieved from Visibility server), UWB tag IDs to be mapped, UWB data processing methods, etc.
    * All configuration information is stored in Redis in standardized JSON format that can be consumed by `falcon-wrapper-service`.
* **Active Camera List Provision:**
    * Provides a list and detailed information of currently available cameras (active and not in specific error states) from the connected Visibility server.
    * Clients (e.g., UI) can select cameras for service configuration based on this information.
* **UWB Data Retrieval:**
    * Retrieves and provides the latest location information for specific UWB tag IDs from the connected PostgreSQL database.

## 3. System Architecture and Integration

1. **Clients** call the `ai-service-config-server` API to register new service configurations or retrieve/update existing configurations.
2. During configuration registration, `ai-service-config-server`:
   a. Uses the requested `input_camera_id` to fetch detailed camera information (stream URL, protocol, etc.) from the **Visibility server**.
   b. (Optionally) uses the requested `input_uwb_tag_id` to retrieve initial UWB data from the **UWB database (PostgreSQL)**.
   c. Constructs a JSON payload that `falcon-wrapper-service` can understand based on the collected information.
   d. Stores the constructed payload in **Redis** under the designated key (`service_configs:<service_name>`).
3. **`falcon-wrapper-service`** periodically polls Redis to scan keys with the `service_configs:*` pattern, detects configuration changes, and updates the data processing pipeline in real-time.

## 4. API Endpoints

### 4.1. Service Configuration

#### `POST /service_configs`

Registers a new service configuration or updates an existing configuration.

* **Request Body (JSON):**
    ```json
    {
        "service_name": "cam_lobby_rtsp_01", // Unique name for service configuration (used for Redis key generation)
        "description": "Lobby RTSP camera with UWB tag 101, handled by postgresql", // Description (optional)
        "input_camera_id": "uuid_of_camera_from_visibility_lobby", // Unique ID of camera registered in Visibility server
        "input_uwb_tag_id": "101", // UWB tag ID to be mapped with this camera
        "uwb_handler_type": "postgresql", // "postgresql" or "api". Uses wrapper's default if not provided (optional)
        "inference_config": { // Additional configuration to be passed to inference service (optional, for reference)
            "model_name": "yolov5s",
            "confidence_threshold": 0.5
        }
    }
    ```
* **Success Response (201 Created):**
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
                    "rtsp_url": "rtsp://example.com/live/stream1"
                },
                "camera_id_from_visibility_server": "uuid_of_camera_from_visibility_lobby",
                "agent_id": "agent_uuid_123",
                // ... other camera information from Visibility server
            },
            "initial_uwb_info_snapshot": { /* UWB data snapshot at registration time */ },
            "inference_config": { /* requested inference_config */ },
            "last_updated_utc": "2023-10-27T12:34:56.789Z"
        }
    }
    ```
* **Error Response (400, 404, 500, etc.):**
    ```json
    {
        "message": "Error message describing the issue."
    }
    ```

#### `GET /service_configs/<string:service_name>`

Retrieves a specific service configuration from Redis.

* **Path Parameters:**
    * `service_name`: Name of the service configuration to retrieve.
* **Success Response (200 OK):**
    ```json
    {
        "redis_key": "service_configs:cam_lobby_rtsp_01",
        "data": { /* Stored service configuration JSON object */ }
    }
    ```
* **Error Response (404 Not Found, etc.):**
    ```json
    {
        "message": "Service configuration for 'cam_lobby_rtsp_01' not found in Redis (key prefix: 'service_configs:')."
    }
    ```

### 4.2. Active Cameras

#### `GET /active_cameras`

Retrieves the list of available cameras (not in specific error states) from the Visibility server.

* **Success Response (200 OK):**
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
                "stream_details": { "rtsp_url": "rtsp://example.com/live/stream1" },
                // ... other camera information
            },
            // ... other active camera information
        ],
        "count": 1 
    }
    ```
* **Error Response (500 Internal Server Error, etc.):**
    ```json
    {
        "message": "Failed to fetch camera list from Visibility Server."
    }
    ```

### 4.3. UWB Tag Data

#### `GET /uwb_data/tags/<string:tag_id>`

Retrieves the latest location data for a specific UWB tag ID from the PostgreSQL database.

* **Path Parameters:**
    * `tag_id`: UWB tag ID to retrieve.
* **Success Response (200 OK):**
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
* **Error Response (404 Not Found, 500 Internal Server Error, etc.):**
    ```json
    {
        "message": "No UWB data found for tag_id '101'."
    }
    ```

## 5. Key Dependencies

* Python 3.9+
* Flask
* Flask-RESTful
* Flask-CORS
* psycopg2-binary (PostgreSQL driver)
* redis (Python Redis client)
* requests (HTTP request library)
* python-dotenv (Environment variable management)

(See `requirements.txt` for complete list)

## 6. Environment Variable Configuration

This service requires the following environment variables to be set depending on the execution environment. (You can create a `.env` file in the project root to manage them.)

* **PostgreSQL Related:**
    * `POSTGRES_HOST`: PostgreSQL server host (default: `10.79.1.13`)
    * `POSTGRES_PORT`: PostgreSQL server port (default: `5432`)
    * `POSTGRES_USER`: PostgreSQL username
    * `POSTGRES_PASSWORD`: PostgreSQL password
    * `POSTGRES_DB`: Database name where UWB data is stored
    * `UWB_TABLE_NAME`: UWB data table name (default: `uwb_raw`)
* **Redis Related:**
    * `REDIS_HOST`: Redis server host (default: `localhost`)
    * `REDIS_PORT`: Redis server port (default: `6379`)
    * `REDIS_DB_SERVICE_CONFIG`: Redis DB number for storing service configurations (default: `0`)
    * `REDIS_PASSWORD`: Redis password (if configured)
    * `REDIS_SERVICE_CONFIG_KEY_PREFIX`: Key prefix for storing service configurations in Redis (default: `service_configs`)
* **Visibility Server Related:**
    * `VISIBILITY_SERVER_URL`: Base URL of the Visibility server (e.g., `http://localhost:5111`)
* **Service Configuration:**
    * `LOG_LEVEL`: Logging level (e.g., `INFO`, `DEBUG`) (default: `INFO`)
    * `AI_CONFIG_SERVICE_PORT`: Port on which this service will run (default: `5005`)

## 7. How to Run

1. Install required Python libraries:
    ```bash
    pip install -r requirements.txt
    ```
2. Set up required environment variables. (e.g., create `.env` file or set directly)
3. Run the Flask development server:
    ```bash
    python app.py
    ```
    For production environments, using a WSGI server like Gunicorn is recommended.

## 8. Integration with `falcon-wrapper-service`

Configuration information stored in Redis by `ai-service-config-server` (key pattern: `service_configs:*`) is periodically polled by `falcon-wrapper-service`. `falcon-wrapper-service` performs the following based on this information:

* `service_name`: Used as a unique identifier for each configuration.
* `input_uwb_tag_id`: Identifies the UWB tag to be fused with the corresponding camera stream.
* `uwb_handler_type`: Determines the method for retrieving UWB data (PostgreSQL or API). (If this field is missing, uses `falcon-wrapper-service`'s default configuration)
* `visibility_camera_info`:
    * `stream_protocol`: Either "RTSP" or "KAFKA", indicating the type of input stream.
    * `stream_details`:
        * For RTSP: `{"rtsp_url": "..."}`
        * For KAFKA: `{"kafka_topic": "...", "kafka_bootstrap_servers": "..."}` (If `kafka_bootstrap_servers` is missing, uses `falcon-wrapper-service`'s global Kafka server configuration)

Through this dynamic configuration, `falcon-wrapper-service` can manage input sources in real-time and respond to changes without service restarts.