"""
강력해진 LLM 으로 좀 더 개선된 형태로 리팩토링!!!
250517 송인용 다시 한번 추가 수정 작업 / 전보다는 좀 더 DataModel 이랑 DB 로직이 살짝 더 분리됨됨
"""

import uuid
from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware
from connections import DATABASE_FILE
import os
import logging




logger = logging.getLogger(__name__)

class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
# 싱글톤 연결 설정
    def _initialize(self):
        # --- tindy DB 사용할때는 항상 DB 파일 초기화 로직 하도록 설정해둠 ---
        # 싫으면 환경 변수 (RESET_DB_ON_START=false) 로 바꿔서 사용하는데 그럴빠에 그냥 새로 DB 연결하삼삼
 
        if os.getenv('FLASK_ENV') == 'development' or os.getenv('RESET_DB_ON_START', 'true').lower() == 'true':
            try:
                if os.path.exists(DATABASE_FILE):
                    os.remove(DATABASE_FILE)
                    logger.info(f"Development mode: Database file '{DATABASE_FILE}' removed for reset.")
            except OSError as e:
                logger.error(f"Error removing database file '{DATABASE_FILE}': {e}")
        # --- DB 파일 초기화 로직 끝 ---

        self.db = TinyDB(DATABASE_FILE, storage=CachingMiddleware(JSONStorage))
        self.agent_table = self.db.table('agents')
        logger.info(f"Database initialized. Using file: {DATABASE_FILE}")

    def insert_agent_document(self, agent_document: dict):
        """
        완전히 구성된 에이전트 문서를 데이터베이스에 삽입합니다.
        agent_document는 'agent_id'를 포함해야 합니다.
        AgentModel에서 agent_id 생성 및 last_update 필드 관리를 담당합니다.
        """
        # agent_document에 agent_id가 포함되어 있다고 가정합니다.
        # AgentModel에서 self.agent_table.insert(agent_data) 대신 이 메서드를 호출합니다.
        doc_id = self.agent_table.insert(agent_document)
        return doc_id # TinyDB의 insert는 document ID를 반환합니다.

    def get_agent_document_by_id(self, agent_id: str):
        """
        agent_id로 에이전트 문서를 조회합니다.
        """
        Agent = Query()
        results = self.agent_table.search(Agent.agent_id == agent_id)
        return results[0] if results else None

    def update_agent_document(self, agent_id: str, agent_data_to_update: dict):
        """
        특정 agent_id를 가진 에이전트 문서의 지정된 필드들을 업데이트합니다.
        agent_data_to_update 딕셔너리에는 변경할 필드와 값이 포함됩니다.
        (예: {'status': 'offline', 'last_update': 'timestamp', 'cameras': [...]})
        AgentModel에서 self.agent_table.update(data, Query().agent_id == agent_id) 대신 이 메서드를 호출합니다.
        """
        Agent = Query()
        updated_ids = self.agent_table.update(agent_data_to_update, Agent.agent_id == agent_id)
        return len(updated_ids) > 0 # 업데이트 성공 여부 반환

    def upsert_agent_document(self, agent_document: dict, agent_id: str):
        """
        agent_id를 기준으로 에이전트 문서를 업데이트하거나, 존재하지 않으면 새로 삽입합니다.
        AgentModel에서 self.agent_table.upsert(agent_data, Query().agent_id == agent_data['agent_id'])
        대신 이 메서드를 호출합니다.
        """
        Agent = Query()
        # TinyDB의 upsert는 반환 값으로 삽입된 doc_ids 리스트를 주거나, 업데이트 시에는 빈 리스트를 줄 수 있습니다.
        # 성공 여부를 명확히 하려면, upsert 후 해당 문서를 다시 조회하는 방법도 고려할 수 있으나,
        # 여기서는 실행 자체를 성공으로 간주합니다.
        self.agent_table.upsert(agent_document, Agent.agent_id == agent_id)
        return True # 실행 성공으로 간주

    def delete_agent_document_by_id(self, agent_id: str):
        """
        agent_id로 에이전트 문서를 삭제합니다.
        """
        Agent = Query()
        deleted_ids = self.agent_table.remove(Agent.agent_id == agent_id)
        return len(deleted_ids) > 0 # 삭제 성공 여부 반환

    def get_all_agent_documents(self):
        """
        모든 에이전트 문서를 반환합니다.
        """
        return self.agent_table.all()

    def get_agent_documents_by_name(self, agent_name: str):
        """
        agent_name으로 에이전트 문서들을 조회합니다 (이름은 중복될 수 있음을 가정).
        """
        Agent = Query()
        return self.agent_table.search(Agent.agent_name == agent_name)

# 싱글톤 연결 설정
db_instance = Database()