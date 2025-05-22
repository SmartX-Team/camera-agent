# ai_service_config_server/app.py
import logging
from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from flask_cors import CORS
from datetime import datetime, timezone

from config import config # 현재 디렉토리의 config.py에서 config 객체 임포트
from db_utils import init_pg_pool, close_pg_pool, init_redis_client, \
                     fetch_uwb_data_by_tag_id, \
                     get_camera_list_for_service, \
                     add_or_update_camera_in_service_list, \
                     delete_camera_from_service_list
                     
from visibility_client import get_active_cameras_from_visibility

from tasks import cleanup_inactive_camera_services 

# 로깅 설정
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL, logging.INFO),
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app) # 모든 출처에 대해 CORS 허용
api = Api(app)

# --- 애플리케이션 컨텍스트에서 DB 및 Redis 클라이언트 초기화/종료 ---
logger.info("Initializing database and Redis connections at app startup...")
init_pg_pool()
init_redis_client() # Redis 클라이언트 초기화

@app.teardown_appcontext
def close_connections(exception=None):

    pass # 특별한 종료 처리 불필요


# --- API 리소스 정의 ---

class ServiceCameraList(Resource):
    def get(self, service_name: str):
        """특정 서비스 이름으로 등록된 모든 카메라 설정 리스트를 반환합니다."""
        camera_list = get_camera_list_for_service(service_name)
        if camera_list is not None:
            return {"service_name": service_name,
                    "redis_key": f"{config.REDIS_SERVICE_CONFIG_KEY_PREFIX}:{service_name}", 
                    "cameras": camera_list, 
                    "count": len(camera_list)}, 200
        else:
            return {"message": f"Error retrieving camera configuration list for service '{service_name}'."}, 500


class ServiceCameraConfiguration(Resource):
    def post(self, service_name: str):
        """특정 서비스의 카메라 리스트에 새 카메라 설정을 추가하거나 기존 설정을 업데이트합니다."""
        data = request.get_json()
        if not data:
            return {"message": "Request body must be JSON"}, 400

        # 요청 본문에는 추가/업데이트할 단일 카메라의 정보가 와야 함
        # 예: {"input_camera_id": "...", "input_uwb_tag_id": "...", "description": "..."}
        camera_id_from_visibility = data.get("input_camera_id")
        uwb_tag_id_for_camera = data.get("input_uwb_tag_id")
        # uwb_handler_type 등 기타 필드도 data에서 가져옴
        uwb_handler_type = data.get("uwb_handler_type")
        description = data.get("description")
        inference_config_from_request = data.get("inference_config", {})


        if not all([camera_id_from_visibility, uwb_tag_id_for_camera]):
            return {"message": "Missing required fields in request body: input_camera_id, input_uwb_tag_id"}, 400
        
        all_cameras = get_active_cameras_from_visibility()
        if all_cameras is None:
             return {"message": "Failed to fetch camera list from Visibility Server."}, 500

        selected_camera_info_from_visibility = None
        for cam in all_cameras:
            if cam.get('camera_id') == camera_id_from_visibility:
                selected_camera_info_from_visibility = cam
                break
        
        if not selected_camera_info_from_visibility:
            return {"message": f"Camera with ID '{camera_id_from_visibility}' not found in Visibility Server."}, 404
        
        if selected_camera_info_from_visibility.get('camera_status') in config.NON_OPERATIONAL_CAMERA_STATUSES:
            logger.warning(f"Attempt to add/update camera '{camera_id_from_visibility}' for service '{service_name}', but camera is non-operational (status: {selected_camera_info_from_visibility.get('camera_status')}).")
            # 정책에 따라 여기서 400 에러를 반환할 수 있습니다.
            # return {"message": f"Camera '{camera_id_from_visibility}' is currently not operational. Cannot add/update config."}, 400

        uwb_info_snapshot_list = fetch_uwb_data_by_tag_id(uwb_tag_id_for_camera)
        current_uwb_snapshot = None
        if uwb_info_snapshot_list and isinstance(uwb_info_snapshot_list, list) and len(uwb_info_snapshot_list) > 0:
            current_uwb_snapshot = uwb_info_snapshot_list[0]
        # ... (기존 UWB 스냅샷 로직)

        # 저장될 단일 카메라 설정 객체 구성
        single_camera_config_payload = {
            "description": description if description is not None else f"Camera {camera_id_from_visibility} for service {service_name} with UWB tag {uwb_tag_id_for_camera}",
            "input_camera_id": camera_id_from_visibility,
            "input_uwb_tag_id": str(uwb_tag_id_for_camera),
            "visibility_camera_info": {
                "camera_name": selected_camera_info_from_visibility.get("camera_name"),
                "stream_protocol": selected_camera_info_from_visibility.get("stream_protocol"),
                "stream_details": selected_camera_info_from_visibility.get("stream_details"),
                "camera_id_from_visibility_server": selected_camera_info_from_visibility.get("camera_id"),
                "agent_id": selected_camera_info_from_visibility.get("agent_id"),
                "resolution": selected_camera_info_from_visibility.get("resolution"),
                "fps": selected_camera_info_from_visibility.get("fps"),
                "camera_type": selected_camera_info_from_visibility.get("camera_type"),
                "camera_environment": selected_camera_info_from_visibility.get("camera_environment"),
                "camera_status_at_registration": selected_camera_info_from_visibility.get("camera_status")
            },
            "initial_uwb_info_snapshot": current_uwb_snapshot,
            "inference_config": inference_config_from_request,
            "last_updated_utc": datetime.now(timezone.utc).isoformat()
        }
        
        if uwb_handler_type:
            single_camera_config_payload["uwb_handler_type"] = uwb_handler_type
        
        if add_or_update_camera_in_service_list(service_name, single_camera_config_payload):
            # 성공 시, 업데이트된 전체 리스트를 반환하거나, 추가/수정된 항목만 반환할 수 있음
            # 여기서는 추가/수정된 항목과 함께 메시지를 반환
            return {"message": f"Camera configuration for ID '{camera_id_from_visibility}' in service '{service_name}' saved successfully.", 
                    "service_name": service_name,
                    "camera_config_processed": single_camera_config_payload}, 200 # 201 (Created) 또는 200 (OK for update)
        else:
            return {"message": f"Failed to save camera configuration for ID '{camera_id_from_visibility}' in service '{service_name}'."}, 500

    def delete(self, service_name: str, camera_id_to_delete: str):
        """특정 서비스의 카메라 리스트에서 특정 input_camera_id를 가진 카메라 설정을 삭제합니다."""
        if delete_camera_from_service_list(service_name, camera_id_to_delete):
            return {"message": f"Camera configuration for ID '{camera_id_to_delete}' deleted successfully from service '{service_name}'."}, 200
        else:
            return {"message": f"Failed to delete camera config for ID '{camera_id_to_delete}' from service '{service_name}' or camera not found."}, 404



class ActiveCameraList(Resource):
    def get(self):
        """ 
        Visibility 서버에서 카메라 목록을 가져와,
        미동작/오류 상태가 아닌 카메라만 필터링하여 반환합니다.
        """
        all_cameras_from_visibility = get_active_cameras_from_visibility()

        if all_cameras_from_visibility is None: # get_active_cameras_from_visibility가 오류 시 []를 반환하므로, None 체크는 불필요할 수 있음
            logger.error("Failed to fetch camera list from Visibility Server or the server returned an unexpected value.")
            return {"message": "Failed to fetch camera list from Visibility Server."}, 500
        
        operational_cameras = [
            cam for cam in all_cameras_from_visibility 
            if isinstance(cam, dict) and cam.get('camera_status') not in config.NON_OPERATIONAL_CAMERA_STATUSES
        ]

        logger.info(f"Fetched {len(all_cameras_from_visibility)} cameras from visibility, "
                    f"filtered down to {len(operational_cameras)} operational cameras (excluding {config.NON_OPERATIONAL_CAMERA_STATUSES}).")
        
        return {"active_cameras": operational_cameras, "count": len(operational_cameras)}, 200

class UWBTagData(Resource):
    def get(self, tag_id):
        """ 특정 UWB 태그 ID의 최신 위치 데이터를 PostgreSQL에서 조회합니다. """
        uwb_data_list = fetch_uwb_data_by_tag_id(tag_id) # 리스트 또는 None 반환
        if uwb_data_list and isinstance(uwb_data_list, list) and len(uwb_data_list) > 0:
            return {"tag_id": tag_id, "data": uwb_data_list[0]}, 200
        elif uwb_data_list == []: # 데이터 없음
            return {"message": f"No UWB data found for tag_id '{tag_id}'."}, 404
        else: # None 반환 (DB 오류 등)
            return {"message": f"Error fetching UWB data for tag_id '{tag_id}' or no data available."}, 500


# API 엔드포인트 재구성
# GET /service_configs/<service_name> -> 특정 서비스의 카메라 리스트 조회
api.add_resource(ServiceCameraList, '/service_configs/<string:service_name>')

# POST /service_configs/<service_name>/cameras -> 특정 서비스에 카메라 추가/업데이트
# DELETE /service_configs/<service_name>/cameras/<camera_id> -> 특정 서비스에서 카메라 삭제
api.add_resource(ServiceCameraConfiguration, 
                 '/service_configs/<string:service_name>/cameras',  # POST
                 '/service_configs/<string:service_name>/cameras/<string:camera_id_to_delete>') # DELETE

api.add_resource(ActiveCameraList, '/active_cameras')
api.add_resource(UWBTagData, '/uwb_data/tags/<string:tag_id>')


# --- APScheduler 설정 ---
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import os # os 모듈 임포트

scheduler = BackgroundScheduler(daemon=True)

def initialize_scheduler():
    # tasks.py에서 가져온 함수를 사용
    scheduler.add_job(func=cleanup_inactive_camera_services, trigger="interval", minutes=config.CLEANUP_INTERVAL_MINUTES, id="cleanup_job") # 설정 파일에서 주기 로드
    
    try:
        scheduler.start()
        logger.info(f"Background scheduler started. Cleanup job will run every {config.CLEANUP_INTERVAL_MINUTES} minutes.")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}", exc_info=True)

    atexit.register(lambda: shutdown_scheduler())

def shutdown_scheduler():
    if scheduler.running:
        try:
            scheduler.shutdown()
            logger.info("Background scheduler shut down.")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}", exc_info=True)


if __name__ == '__main__':

    # Werkzeug reloader가 메인 프로세스에서만 스케줄러를 시작하도록 하는 로직
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        initialize_scheduler()
    else:
        logger.info("Skipping scheduler initialization in Werkzeug reloader child process.")

    logger.info(f"Starting AI Service Configuration Server on port {config.SERVICE_PORT}...")
    app.run(host='0.0.0.0', port=config.SERVICE_PORT, debug=(config.LOG_LEVEL == 'DEBUG'))
