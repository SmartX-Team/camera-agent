"""

앞으로 개선사항

개발 자체가 메인 작업이 아니기도하고 빨리 기능 구현해서 연구 및 컨텐츠 제공에 집중했는데,

데이터 모델과 데이터베이스 연결이 명확히 분리되어 있지 않아
데이터베이스 접근 로직과 비즈니스 로직이 혼재되어 있음


향후 개선 사항:
- 데이터베이스 접근을 담당하는 Data Access Layer(DAL) 또는 Repository 클래스를 분리하여 구현
- 데이터 모델을 표현하는 별도의 클래스 또는 데이터 구조체 도입
- ORM(Object Relational Mapping) 적용해서 고려하여 코드의 가독성과 유지보수성 향상

주석 작성일 240927 송인용

"""
import uuid
from datetime import datetime
from tinydb import Query
from database import db_instance

class AgentModel:
    
    @staticmethod
    def add_agent(agent_name, ip, port, stream_uri, rtsp_allowed_ip_range):
        """
        새로운 에이전트를 추가하거나 기존 에이전트를 반환하는 함수.
        IP를 기준으로 기존 에이전트 검색

        기존 에이전트가 있으면 해당 정보를 반환하고 없으면 새롭게 DB에 등록

        """
        existing_agent = db_instance.agent_table.get(Query().ip == ip)
        if existing_agent:
            return existing_agent['agent_id'], existing_agent, True  # True는 기존 에이전트임을 나타냄
        else:
            # 새로운 에이전트를 추가
            agent_id = str(uuid.uuid4())
            agent_data = {
                'agent_id': agent_id,
                'agent_name': agent_name,
                'ip': ip,
                'port': port,
                'stream_uri': stream_uri,
                'rtsp_allowed_ip_range': rtsp_allowed_ip_range,
                'camera_status': [],
                'last_update': datetime.utcnow().isoformat(),
                'frame_transmission_enabled': False
            }
            db_instance.agent_table.insert(agent_data)
            return agent_id, agent_data, False

    @staticmethod
    def upsert_agent(agent_data):
        db_instance.agent_table.upsert(agent_data, Query().agent_id == agent_data['agent_id'])

    @staticmethod
    def get_agent(agent_id):
        return db_instance.agent_table.get(Query().agent_id == agent_id)

    @staticmethod
    def update_agent(agent_id, data):
        db_instance.agent_table.update(data, Query().agent_id == agent_id)

    @staticmethod
    def get_all_agents():
        return db_instance.agent_table.all()
