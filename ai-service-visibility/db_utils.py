# ai_service_config_server/db_utils.py
import psycopg2
from psycopg2 import pool
from psycopg2.extras import DictCursor
import redis
import logging
import json
from typing import List, Dict, Union, Optional, Any
from config import config # 현재 디렉토리의 config.py에서 config 객체 임포트

logger = logging.getLogger(__name__)

pg_connection_pool = None

def init_pg_pool():
    global pg_connection_pool
    try:
        logger.info(f"Initializing PostgreSQL connection pool for {config.POSTGRES_DB} on {config.POSTGRES_HOST}...")
        pg_connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, 5,
            user=config.POSTGRES_USER,
            password=config.POSTGRES_PASSWORD,
            host=config.POSTGRES_HOST,
            port=config.POSTGRES_PORT,
            database=config.POSTGRES_DB
        )
        conn = pg_connection_pool.getconn()
        logger.info("PostgreSQL connection pool successfully initialized and tested.")
        pg_connection_pool.putconn(conn)
    except (Exception, psycopg2.Error) as error:
        logger.error(f"Error while connecting to PostgreSQL or initializing pool: {error}", exc_info=True)
        pg_connection_pool = None

def get_pg_connection():
    if pg_connection_pool:
        return pg_connection_pool.getconn()
    # 풀이 초기화 안됐으면 여기서 초기화 시도 (선택적)
    logger.warning("PostgreSQL connection pool was not initialized. Attempting to initialize now.")
    init_pg_pool()
    if pg_connection_pool:
        return pg_connection_pool.getconn()
    logger.error("Failed to get PostgreSQL connection after attempting re-initialization.")
    return None


def put_pg_connection(conn):
    if pg_connection_pool and conn:
        pg_connection_pool.putconn(conn)

def close_pg_pool():
    global pg_connection_pool
    if pg_connection_pool:
        logger.info("Closing PostgreSQL connection pool.")
        pg_connection_pool.closeall()
        pg_connection_pool = None

# 타입 힌트 수정: list[dict] | None  ->  Union[List[Dict], None] 또는 Optional[List[Dict]]
def fetch_uwb_data_by_tag_id(tag_id: str) -> Optional[List[Dict]]:
    """ 특정 UWB 태그 ID의 최신 위치 데이터를 PostgreSQL에서 조회합니다.
        데이터 발견 시: [dict(result)]
        데이터 미발견 시: [] (빈 리스트)
        DB 오류 시: None
    """
    conn = None
    try:
        conn = get_pg_connection()
        if not conn:
            return None # DB 연결 실패 시 None 반환
        
        # 'psycopg2.extras.DictCursor' 대신 'DictCursor' 사용
        with conn.cursor(cursor_factory=DictCursor) as cur:
            query = f"""
                SELECT id, tag_id, x_position, y_position, raw_timestamp::TEXT AS raw_timestamp
                FROM {config.UWB_TABLE_NAME} 
                WHERE tag_id = %s 
                ORDER BY raw_timestamp DESC 
                LIMIT 1;
            """
            cur.execute(query, (str(tag_id),))
            result = cur.fetchone()
            
            if result:
                logger.debug(f"UWB data found for tag_id '{tag_id}': {dict(result)}")
                return [dict(result)] 
            else:
                logger.info(f"No UWB data found for tag_id '{tag_id}' in table '{config.UWB_TABLE_NAME}'.")
                return [] # <--- 수정: 데이터 없을 시 빈 리스트 반환
    except (Exception, psycopg2.Error) as error:
        logger.error(f"Error fetching UWB data for tag_id '{tag_id}': {error}", exc_info=True)
        return None # <--- DB 오류 시 None 반환
    finally:
        if conn:
            put_pg_connection(conn)

redis_client = None

def init_redis_client():
    global redis_client
    try:
        logger.info(f"Initializing Redis client for {config.REDIS_HOST}:{config.REDIS_PORT} DB {config.REDIS_DB_SERVICE_CONFIG}...")
        redis_client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=int(config.REDIS_DB_SERVICE_CONFIG), # config에서 문자열로 올 수 있으므로 int 변환
            password=config.REDIS_PASSWORD if hasattr(config, 'REDIS_PASSWORD') else None, # 비밀번호 없을 수 있음
            socket_connect_timeout=5,
            socket_timeout=5,
            decode_responses=True # JSON 문자열 처리를 위해 True 유지
        )
        redis_client.ping()
        logger.info("Redis client successfully initialized and connected.")
    except redis.exceptions.RedisError as error:
        logger.error(f"Error connecting to Redis: {error}", exc_info=True)
        redis_client = None
    except Exception as e: # 포괄적인 예외 처리
        logger.error(f"An unexpected error occurred during Redis client initialization: {e}", exc_info=True)
        redis_client = None

def get_redis_client() -> Optional[redis.Redis]: # 타입 힌트 추가
    if not redis_client:
        logger.warning("Redis client is not initialized. Attempting to initialize now.")
        init_redis_client()
    return redis_client

# --- 서비스별 카메라 리스트 관리 함수 ---

def get_service_specific_redis_key(service_name: str) -> str:
    """특정 서비스 이름에 대한 Redis 키를 생성합니다."""
    return f"{config.REDIS_SERVICE_CONFIG_KEY_PREFIX}:{service_name}"

def get_camera_list_for_service(service_name: str) -> Optional[List[Dict[str, Any]]]:
    """특정 서비스 이름으로 등록된 카메라 설정 리스트를 조회합니다."""
    r = get_redis_client()
    if not r:
        logger.error(f"Cannot get camera list for service '{service_name}': Redis client not available.")
        return None
        
    redis_key = get_service_specific_redis_key(service_name)
    try:
        raw_data = r.get(redis_key)
        if raw_data:
            camera_config_list = json.loads(raw_data)
            if not isinstance(camera_config_list, list):
                logger.error(f"Data for service '{service_name}' (key '{redis_key}') is not a list. Data: {camera_config_list}")
                return [] # 또는 None, 오류 상황에 따라 결정
            logger.info(f"Camera config list for service '{service_name}' retrieved. Count: {len(camera_config_list)}")
            return camera_config_list
        else:
            logger.info(f"No camera config list found for service '{service_name}' (key '{redis_key}'). Returning empty list.")
            return [] # 키가 없으면 빈 리스트로 시작
    except Exception as e:
        logger.error(f"Error getting camera list for service '{service_name}' (key '{redis_key}'): {e}", exc_info=True)
        return None # JSONDecodeError 등 포함

def add_or_update_camera_in_service_list(service_name: str, camera_config_to_add: Dict[str, Any]) -> bool:
    """특정 서비스의 카메라 리스트에 새 카메라 설정을 추가하거나 기존 설정을 업데이트합니다."""
    r = get_redis_client()
    if not r:
        logger.error(f"Cannot add/update camera for service '{service_name}': Redis client not available.")
        return False
    
    redis_key = get_service_specific_redis_key(service_name)
    # 카메라 식별자: 'input_camera_id' 또는 'visibility_camera_info'.'camera_id_from_visibility_server'
    cam_id_to_add = camera_config_to_add.get("input_camera_id")
    if not cam_id_to_add and camera_config_to_add.get("visibility_camera_info"):
        cam_id_to_add = camera_config_to_add["visibility_camera_info"].get("camera_id_from_visibility_server")

    if not cam_id_to_add:
        logger.error(f"Cannot add/update camera for service '{service_name}': Camera ID is missing in the provided config.")
        return False

    try:
        with r.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(redis_key)
                    current_list_str = pipe.get(redis_key)
                    current_camera_list = []
                    if current_list_str:
                        current_camera_list = json.loads(current_list_str)
                        if not isinstance(current_camera_list, list):
                            logger.warning(f"Data for service '{service_name}' (key '{redis_key}') was not a list. Overwriting.")
                            current_camera_list = []
                    
                    updated_existing = False
                    for i, existing_cam_config in enumerate(current_camera_list):
                        existing_cam_id = existing_cam_config.get("input_camera_id")
                        if not existing_cam_id and existing_cam_config.get("visibility_camera_info"):
                             existing_cam_id = existing_cam_config["visibility_camera_info"].get("camera_id_from_visibility_server")

                        if existing_cam_id == cam_id_to_add:
                            current_camera_list[i] = camera_config_to_add # 업데이트
                            logger.info(f"Updated camera config for ID '{cam_id_to_add}' in service '{service_name}'.")
                            updated_existing = True
                            break
                    
                    if not updated_existing:
                        current_camera_list.append(camera_config_to_add) # 추가
                        logger.info(f"Added new camera config for ID '{cam_id_to_add}' to service '{service_name}'.")

                    pipe.multi()
                    pipe.set(redis_key, json.dumps(current_camera_list))
                    pipe.execute()
                    return True
                except redis.exceptions.WatchError:
                    logger.warning(f"WatchError on key '{redis_key}' for service '{service_name}', retrying.")
                    continue
                except Exception as e_pipe: # JSONDecodeError 등 포함
                    logger.error(f"Error during Redis pipeline for service '{service_name}' (key '{redis_key}'): {e_pipe}", exc_info=True)
                    return False
    except Exception as e:
        logger.error(f"General error adding/updating camera for service '{service_name}': {e}", exc_info=True)
        return False

def delete_camera_from_service_list(service_name: str, camera_id_to_delete: str) -> bool:
    """특정 서비스의 카메라 리스트에서 특정 camera_id를 가진 설정을 삭제합니다."""
    r = get_redis_client()
    if not r:
        logger.error(f"Cannot delete camera from service '{service_name}': Redis client not available.")
        return False

    redis_key = get_service_specific_redis_key(service_name)
    try:
        with r.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(redis_key)
                    current_list_str = pipe.get(redis_key)
                    if not current_list_str:
                        logger.info(f"Cannot delete camera: List for service '{service_name}' (key '{redis_key}') does not exist.")
                        return False 
                    
                    current_camera_list = json.loads(current_list_str)
                    if not isinstance(current_camera_list, list):
                        logger.error(f"Data for service '{service_name}' (key '{redis_key}') is not a list. Cannot delete.")
                        return False

                    initial_len = len(current_camera_list)
                    new_camera_list = []
                    deleted = False
                    for cam_config in current_camera_list:
                        existing_cam_id = cam_config.get("input_camera_id")
                        if not existing_cam_id and cam_config.get("visibility_camera_info"):
                             existing_cam_id = cam_config["visibility_camera_info"].get("camera_id_from_visibility_server")
                        
                        if existing_cam_id == camera_id_to_delete:
                            deleted = True
                            # 이 항목은 new_camera_list에 추가하지 않음
                        else:
                            new_camera_list.append(cam_config)
                    
                    if deleted: # 삭제된 항목이 있다면
                        pipe.multi()
                        if not new_camera_list: # 리스트가 비게 되면 키 자체를 삭제 (선택적)
                            logger.info(f"Camera list for service '{service_name}' is now empty. Deleting key '{redis_key}'.")
                            pipe.delete(redis_key)
                        else:
                            pipe.set(redis_key, json.dumps(new_camera_list))
                        pipe.execute()
                        logger.info(f"Successfully deleted camera config for ID '{camera_id_to_delete}' from service '{service_name}'.")
                        return True
                    else:
                        logger.info(f"Camera config for ID '{camera_id_to_delete}' not found in service '{service_name}'. Nothing to delete.")
                        return False # 삭제할 대상이 없음
                except redis.exceptions.WatchError:
                    logger.warning(f"WatchError on key '{redis_key}' for service '{service_name}' while deleting, retrying.")
                    continue
                except Exception as e_pipe_del: # JSONDecodeError 등 포함
                    logger.error(f"Error during Redis pipeline for delete on service '{service_name}' (key '{redis_key}'): {e_pipe_del}", exc_info=True)
                    return False
    except Exception as e:
        logger.error(f"General error deleting camera for ID '{camera_id_to_delete}' from service '{service_name}': {e}", exc_info=True)
        return False



def save_service_config_to_redis(service_name: str, service_config_data: dict) -> bool:
    r = get_redis_client()
    if not r:
        logger.error("Cannot save service config to Redis: client not available.")
        return False
    
    redis_key = f"{config.REDIS_SERVICE_CONFIG_KEY_PREFIX}:{service_name}"
    try:
        # datetime 객체 등이 있다면 JSON 직렬화 전에 문자열로 변환 필요
        r.set(redis_key, json.dumps(service_config_data))
        logger.info(f"Service config for '{service_name}' saved to Redis key '{redis_key}'.")
        return True
    except redis.exceptions.RedisError as e:
        logger.error(f"Error saving service config for '{service_name}' to Redis: {e}", exc_info=True)
        return False
    except TypeError as e_ser: # json.dumps에서 발생할 수 있는 TypeError (직렬화 불가 객체)
        logger.error(f"Error serializing service config for '{service_name}' before saving to Redis: {e_ser}", exc_info=True)
        return False
    except Exception as e_gen: # 기타 예외
        logger.error(f"Unexpected error saving service config for '{service_name}' to Redis: {e_gen}", exc_info=True)
        return False

def get_service_config_from_redis(service_name: str) -> Optional[Dict]:
    r = get_redis_client()
    if not r:
        logger.error("Cannot get service config from Redis: client not available.")
        return None
        
    redis_key = f"{config.REDIS_SERVICE_CONFIG_KEY_PREFIX}:{service_name}"
    try:
        raw_data = r.get(redis_key)
        if raw_data:
            # raw_data는 decode_responses=True로 인해 이미 문자열일 것임
            config_data = json.loads(raw_data) 
            logger.info(f"Service config for '{service_name}' retrieved from Redis key '{redis_key}'.")
            return config_data
        else:
            logger.info(f"No service config found in Redis for service_name '{service_name}' (key: '{redis_key}').")
            return None
    except redis.exceptions.RedisError as e:
        logger.error(f"Error getting service config for '{service_name}' from Redis: {e}", exc_info=True)
        return None
    except json.JSONDecodeError as e_json:
        logger.error(f"Error decoding JSON service config for '{service_name}' from Redis: {e_json}. Raw data: {raw_data[:200] if raw_data else 'N/A'}", exc_info=True)
        return None
    except Exception as e_gen: # 기타 예외
        logger.error(f"Unexpected error getting service config for '{service_name}' from Redis: {e_gen}", exc_info=True)
        return None