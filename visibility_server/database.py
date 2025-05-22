import uuid
from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
# from tinydb.middlewares import CachingMiddleware # 테스트를 위해 제거된 상태 유지
import os
import logging
from datetime import datetime, timedelta

# --- DATABASE_FILE 설정 로직 (이전과 동일) ---
try:
    from connections import DATABASE_FILE
    if DATABASE_FILE is None:
        DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agents_fallback.json')
        logging.warning(f"DATABASE_FILE was None in connections.py, using fallback: {DATABASE_FILE}")
except ImportError:
    DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agents_db.json')
    logging.warning(f"'connections.py' not found or DATABASE_FILE not imported. Using default: {DATABASE_FILE}")
except Exception as e_conn:
    DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agents_db_exc.json')
    logging.error(f"Error importing from connections.py: {e_conn}. Using default: {DATABASE_FILE}", exc_info=True)

logger = logging.getLogger(__name__)

class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            logger.debug("[DB_NEW] Creating new Database instance.")
            instance = super(Database, cls).__new__(cls)
            instance._db = None
            instance._agent_table = None
            try:
                instance._initialize()
            except Exception as e:
                logger.error(f"[DB_NEW] CRITICAL error during Database instance initialization: {e}", exc_info=True)
            cls._instance = instance
        return cls._instance

    def _initialize(self):
        logger.info(f"[DB_INIT_START] Initializing Database. Current self id: {id(self)}")
        reset_db_env_var = os.getenv('RESET_DB_ON_START', 'true').lower()
        if os.getenv('FLASK_ENV') == 'development' or reset_db_env_var == 'true':
            logger.info(f"[DB_INIT] Reset condition met. Checking DB file: {DATABASE_FILE}")
            try:
                if DATABASE_FILE and os.path.exists(DATABASE_FILE):
                    os.remove(DATABASE_FILE)
                    logger.info(f"[DB_INIT] Database file '{DATABASE_FILE}' removed for reset.")
                elif not DATABASE_FILE:
                     logger.warning("[DB_INIT] DATABASE_FILE path is not set. Cannot remove for reset.")
            except OSError as e:
                logger.error(f"[DB_INIT] Error removing database file '{DATABASE_FILE}': {e}", exc_info=True)
        
        if not DATABASE_FILE:
            logger.error("[DB_INIT] DATABASE_FILE is not defined. Cannot initialize TinyDB.")
            self._db = None
            self._agent_table = None
            return

        try:
            logger.debug(f"[DB_INIT] Initializing TinyDB with file: {DATABASE_FILE}")
            self._db = TinyDB(DATABASE_FILE, storage=JSONStorage) # CachingMiddleware 없이
            logger.info("[DB_INIT] TinyDB initialized with JSONStorage directly (CachingMiddleware REMOVED for testing).")
            self._agent_table = self._db.table('agents')
            if self._agent_table is None: # table()이 None을 반환하는 경우는 거의 없지만 방어.
                 logger.error("[DB_INIT_END] '_agents' table object is None after db.table('agents') call! This is unexpected.")
            else: # 정상 초기화되면 _agent_table은 비어있더라도 유효한 Table 객체.
                 logger.info(f"[DB_INIT_END] Database initialized successfully. Using file: {DATABASE_FILE}. Agent table type: {type(self._agent_table)}")
        except Exception as e:
            logger.error(f"[DB_INIT_END] Failed to initialize TinyDB or get 'agents' table: {e}", exc_info=True)
            self._db = None
            self._agent_table = None

    @property
    def db(self):
        if self._db is None:
            logger.error(f"[DB_PROPERTY_DB] Self id: {id(self)}. Underlying _db connection object is None!")
        # else: # 너무 많은 로그를 피하기 위해 정상 케이스는 DEBUG 레벨 또는 생략 가능
            # logger.debug(f"[DB_PROPERTY_DB] Self id: {id(self)}. Returning _db object. Type: {type(self._db)}")
        return self._db

    @property
    def agent_table(self):
        current_method_context = "[AGENT_TABLE_PROPERTY]"
        logger.debug(f"{current_method_context} Entry. self id: {id(self)}, Current self._agent_table type: {type(self._agent_table)}, Current self._db type: {type(self._db)}")
        if self._agent_table is None:
            logger.warning(f"{current_method_context} Internal _agent_table is None at entry.")
            if self._db is not None:
                logger.info(f"{current_method_context} Internal _db object exists. Attempting to re-fetch table 'agents'.")
                try:
                    table = self._db.table('agents')
                    if table is not None:
                        self._agent_table = table
                        logger.info(f"{current_method_context} Successfully re-fetched and cached _agent_table. Type: {type(self._agent_table)}")
                    else:
                        logger.error(f"{current_method_context} self._db.table('agents') returned None. _agent_table remains None.")
                except Exception as e:
                    logger.error(f"{current_method_context} Exception during re-fetch of _agent_table: {e}", exc_info=True)
                    self._agent_table = None
            else:
                logger.error(f"{current_method_context} Internal _db is also None. Cannot re-fetch _agent_table. _agent_table remains None.")
        elif self._db is None and self._agent_table is not None:
            logger.warning(f"{current_method_context} Internal _db is None, but _agent_table existed. Invalidating stale _agent_table.")
            self._agent_table = None
            
        final_table_to_return = self._agent_table
        if final_table_to_return is None:
            logger.warning(f"{current_method_context} FINAL_RETURN: Returning None. self id: {id(self)}")
        else:
            # 비어있는 테이블도 유효한 객체이므로 INFO 레벨로 변경, ID는 너무 상세하므로 제거 또는 DEBUG로
            logger.info(f"{current_method_context} FINAL_RETURN: Returning Table object. Type: {type(final_table_to_return)}. self id: {id(self)}")
        return final_table_to_return

    def _get_valid_table_or_log_error(self, operation_name: str):
        logger.debug(f"[{operation_name}] Calling self.agent_table property. self id for this call: {id(self)}")
        table_instance_received = self.agent_table
        
        is_none_check = table_instance_received is None
        # bool_check_if_not_none = (not table_instance_received) if table_instance_received is not None else False # 이 로그는 혼란 유발, 제거 또는 수정
        # logger.info(f"[{operation_name}] Value received from property: {repr(table_instance_received)}, Type: {type(table_instance_received)}, ID: {id(table_instance_received) if table_instance_received is not None else 'N/A'}, IsNone: {is_none_check}, EvaluatesToFalseIfNotEmpty: {bool_check_if_not_none}")

        if table_instance_received is None: # <--- 올바른 None 체크
            logger.error(f"[{operation_name}] Agent table object IS None (property returned None). Operation cancelled.")
            return None
        
        logger.info(f"[{operation_name}] Agent table object IS available (not None). Type: {type(table_instance_received)}. Proceeding.")
        return table_instance_received

    # --- 모든 DB 접근 메서드에서 'if not tbl:' 을 'if tbl is None:' 으로 수정 ---
    def insert_agent_document(self, agent_document: dict):
        tbl = self._get_valid_table_or_log_error("DB_INSERT")
        if tbl is None: # <--- 수정됨
            return None
        try:
            doc_id = tbl.insert(agent_document)
            logger.debug(f"[DB_INSERT] Document inserted with doc_id: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"[DB_INSERT] Exception during actual insert operation: {e}", exc_info=True)
            return None # TinyDB의 insert는 일반적으로 예외 대신 doc_id 리스트를 반환하지만, 방어적으로 추가

    def get_agent_document_by_id(self, agent_id: str):
        tbl = self._get_valid_table_or_log_error(f"DB_GET_BY_ID (id:{agent_id})")
        if tbl is None: # <--- 수정됨
            return None
        AgentQuery = Query()
        results = tbl.search(AgentQuery.agent_id == agent_id)
        return results[0] if results else None

    def update_agent_document(self, agent_id: str, agent_data_to_update: dict):
        tbl = self._get_valid_table_or_log_error(f"DB_UPDATE (id:{agent_id})")
        if tbl is None: # <--- 수정됨
            return False
        AgentQuery = Query()
        updated_ids = tbl.update(agent_data_to_update, AgentQuery.agent_id == agent_id)
        return len(updated_ids) > 0

    def upsert_agent_document(self, agent_document: dict, agent_id: str):
        tbl = self._get_valid_table_or_log_error(f"DB_UPSERT (id:{agent_id})")
        if tbl is None: # <--- 수정됨
            return False
        AgentQuery = Query()
        tbl.upsert(agent_document, AgentQuery.agent_id == agent_id)
        return True

    def delete_agent_document_by_id(self, agent_id: str):
        tbl = self._get_valid_table_or_log_error(f"DB_DELETE (id:{agent_id})")
        if tbl is None: # <--- 수정됨
            return False
        AgentQuery = Query()
        deleted_ids = tbl.remove(AgentQuery.agent_id == agent_id)
        return len(deleted_ids) > 0

    def get_all_agent_documents(self):
        tbl = self._get_valid_table_or_log_error("DB_GET_ALL")
        if tbl is None: # <--- 수정됨
            return []
        return tbl.all()

    def get_agent_documents_by_name(self, agent_name: str):
        tbl = self._get_valid_table_or_log_error(f"DB_GET_BY_NAME (name:{agent_name})")
        if tbl is None: # <--- 수정됨
            return []
        AgentQuery = Query()
        return tbl.search(AgentQuery.agent_name == agent_name)

    def purge_inactive_agents(self, inactive_threshold_seconds: int) -> list[str]:
        tbl = self._get_valid_table_or_log_error("DB_PURGE_INACTIVE")
        if tbl is None: # <--- 수정됨
            return []
        
        if not isinstance(inactive_threshold_seconds, int) or inactive_threshold_seconds <= 0:
            logger.warning("[DB_PURGE_INACTIVE] inactive_threshold_seconds must be a positive integer.")
            return []

        # ... (이하 purge_inactive_agents 로직은 tbl을 사용하므로 동일)
        cutoff_datetime = datetime.utcnow() - timedelta(seconds=inactive_threshold_seconds)
        cutoff_iso_timestamp = cutoff_datetime.isoformat()
        logger.info(f"[DB_PURGE_INACTIVE] Purging agents inactive since: {cutoff_iso_timestamp} (threshold: {inactive_threshold_seconds} seconds ago)")
        AgentQuery = Query()
        removed_agent_ids_uuid = []
        try:
            stale_agents_to_remove = tbl.search(
                (AgentQuery.last_update.exists()) & (AgentQuery.last_update < cutoff_iso_timestamp)
            )
            # ... (나머지 purge 로직 동일) ...
        except Exception as e:
            logger.error(f"[DB_PURGE_INACTIVE] Error during agent purging process: {e}", exc_info=True)
        return removed_agent_ids_uuid

# Database 클래스 정의 후 db_instance 생성
db_instance = Database()

# 모듈 레벨 로깅 수정
logger.info(f"[DATABASE_PY_MODULE_SCOPE] db_instance created with id: {id(db_instance)}")
initial_table_access = db_instance.agent_table

logger.info(f"[DATABASE_PY_MODULE_SCOPE] Value received from initial db_instance.agent_table call: {repr(initial_table_access)}, Type: {type(initial_table_access)}, ID: {id(initial_table_access) if initial_table_access is not None else 'N/A'}")

if initial_table_access is not None: # <--- 수정됨: None인지 명시적으로 확인
    logger.info(f"[DATABASE_PY_MODULE_SCOPE] db_instance.agent_table (via property, id: {id(initial_table_access) if initial_table_access is not None else 'N/A'}) is NOT None. Type: {type(initial_table_access)}")
else:
    logger.warning(f"[DATABASE_PY_MODULE_SCOPE] db_instance.agent_table (via property) IS None after init. Value: {repr(initial_table_access)}, Type: {type(initial_table_access)}")
