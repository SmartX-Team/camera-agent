"""

정기적으로 실행되는 작업을 정의하는 모듈입니다.

cleanup_inactive_camera_services :이 모듈은 Redis에 저장된 서비스 설정을 점검하고,
더 이상 활성화되지 않은 카메라를 참조하는 설정을 삭제합니다.

# camera-agent/ai-service-visibility/tasks.py


"""

import logging
from config import config
from db_utils import get_redis_client, get_camera_list_for_service # get_camera_list_for_service 사용
from visibility_client import get_active_cameras_from_visibility

logger = logging.getLogger(__name__)

def cleanup_inactive_camera_services():
    """
    주기적으로 실행되어 Redis에 저장된 모든 서비스 설정들을 순회합니다.
    각 서비스 설정(카메라 설정 리스트) 내에서, 더 이상 Visibility 서버에서 
    활성화되지 않거나 운영 불가능한 상태의 카메라를 참조하는 설정을 찾아 제거합니다.
    """
    logger.info("Starting cleanup task for inactive/non-operational camera services across all service configs...")
    r = get_redis_client()
    if not r:
        logger.error("Redis client not available. Skipping cleanup task.")
        return

    try:
        # 1. Redis에서 모든 서비스 설정 키 가져오기 (예: "service_configs:*")
        all_service_keys_pattern = f"{config.REDIS_SERVICE_CONFIG_KEY_PREFIX}:*"
        all_service_keys = r.keys(all_service_keys_pattern) # 이미 문자열 리스트로 반환됨 (decode_responses=True)

        if not all_service_keys:
            logger.info("No service configurations found in Redis with pattern '%s'. Cleanup not needed.", all_service_keys_pattern)
            return

        logger.info(f"Found {len(all_service_keys)} service configuration keys in Redis to check (pattern: '{all_service_keys_pattern}').")

        # 2. Visibility 서버에서 현재 운영 가능한 카메라 ID 목록 가져오기
        all_cameras_from_visibility = get_active_cameras_from_visibility()
        if all_cameras_from_visibility is None:
            logger.error("Failed to fetch camera list from Visibility Server. Skipping cleanup task.")
            return
        
        operational_cameras_from_visibility = [
            cam for cam in all_cameras_from_visibility
            if isinstance(cam, dict) and cam.get('camera_status') not in config.NON_OPERATIONAL_CAMERA_STATUSES and cam.get('camera_id')
        ]
        operational_camera_ids = {cam.get('camera_id') for cam in operational_cameras_from_visibility}
        logger.info(f"Fetched {len(all_cameras_from_visibility)} cameras from Visibility, "
                    f"filtered down to {len(operational_camera_ids)} operational camera IDs (excluding statuses: {config.NON_OPERATIONAL_CAMERA_STATUSES}).")

        total_deleted_camera_configs_count = 0

        # 3. 각 서비스 설정 키에 대해 작업 수행
        for service_key in all_service_keys:
            service_name = service_key.split(f"{config.REDIS_SERVICE_CONFIG_KEY_PREFIX}:", 1)[-1]
            logger.debug(f"Processing service: '{service_name}' (key: {service_key})")

            # 현재 서비스의 카메라 설정 리스트 가져오기
            # get_camera_list_for_service는 키가 없거나 데이터가 리스트가 아니면 [] 또는 None을 반환할 수 있음
            current_camera_list = get_camera_list_for_service(service_name)

            if current_camera_list is None: # db_utils에서 오류 발생 시 None 반환 가능성
                logger.error(f"Failed to retrieve camera list for service '{service_name}'. Skipping this service.")
                continue
            
            if not isinstance(current_camera_list, list) or not current_camera_list:
                logger.info(f"No camera configurations or invalid data for service '{service_name}'. Skipping.")
                continue

            updated_camera_list = []
            service_specific_deleted_count = 0
            
            for camera_config in current_camera_list:
                camera_id_in_config = None
                if camera_config.get('visibility_camera_info') and \
                   isinstance(camera_config['visibility_camera_info'], dict):
                    camera_id_in_config = camera_config['visibility_camera_info'].get('camera_id_from_visibility_server')
                
                if not camera_id_in_config: 
                    camera_id_in_config = camera_config.get('input_camera_id')

                if camera_id_in_config:
                    if camera_id_in_config not in operational_camera_ids:
                        logger.warning(
                            f"Camera config for ID '{camera_id_in_config}' in service '{service_name}' "
                            f"references an inactive/non-operational camera. Marking for removal from this service's list."
                        )
                        service_specific_deleted_count += 1
                    else:
                        updated_camera_list.append(camera_config) # 유효한 설정은 새 리스트에 추가
                        logger.debug(f"Camera config for ID '{camera_id_in_config}' in service '{service_name}' is operational. Keeping.")
                else:
                    logger.warning(f"Could not determine camera_id for a camera config in service '{service_name}'. Keeping it for safety: {camera_config}")
                    updated_camera_list.append(camera_config) # ID 없으면 일단 유지 (또는 다른 정책 적용)
            
            # 변경 사항이 있다면 Redis에 업데이트된 리스트 저장
            if service_specific_deleted_count > 0:
                logger.info(f"Service '{service_name}': {service_specific_deleted_count} camera configs marked for removal.")
                # Redis에 업데이트된 리스트 저장 (파이프라인 사용 권장)
                try:
                    with r.pipeline() as pipe:
                        while True:
                            try:
                                pipe.watch(service_key) # 현재 서비스 키 감시
                                # 현재 값을 다시 읽어와서 병합하는 로직은 복잡해질 수 있으므로,
                                # 여기서는 필터링된 updated_camera_list로 덮어쓰는 방식을 사용.
                                # 만약 이 작업 중에 다른 요청으로 리스트가 변경되면 WatchError 발생.
                                pipe.multi()
                                if not updated_camera_list: # 리스트가 비게 되면 키 자체를 삭제
                                    logger.info(f"Camera list for service '{service_name}' (key: {service_key}) is now empty. Deleting the key.")
                                    pipe.delete(service_key)
                                else:
                                    pipe.set(service_key, json.dumps(updated_camera_list))
                                pipe.execute()
                                logger.info(f"Successfully updated camera list for service '{service_name}' in Redis. Removed {service_specific_deleted_count} configs.")
                                total_deleted_camera_configs_count += service_specific_deleted_count
                                break # 트랜잭션 성공
                            except redis.exceptions.WatchError:
                                logger.warning(f"WatchError on key '{service_key}' for service '{service_name}' during cleanup, retrying transaction.")
                                continue # 재시도
                            except Exception as e_pipe_clean:
                                logger.error(f"Error during Redis pipeline for cleanup on service '{service_name}' (key '{service_key}'): {e_pipe_clean}", exc_info=True)
                                break # 파이프라인 오류 시 해당 서비스 건너뛰기
                except Exception as e_outer_pipe:
                     logger.error(f"Outer error during Redis transaction for cleanup on service '{service_name}' (key '{service_key}'): {e_outer_pipe}", exc_info=True)

            elif not current_camera_list and service_specific_deleted_count == 0 : # 원래 비어있던 경우
                 logger.debug(f"Service '{service_name}' (key: {service_key}) was already empty or became empty without deletions. No update needed.")
            else :
                 logger.debug(f"Service '{service_name}' (key: {service_key}) requires no cleanup for camera configs.")


        logger.info(f"Cleanup task finished. Total camera configurations deleted across all services: {total_deleted_camera_configs_count}.")

    except Exception as e:
        logger.error(f"Error during the main cleanup_inactive_camera_services task: {e}", exc_info=True)