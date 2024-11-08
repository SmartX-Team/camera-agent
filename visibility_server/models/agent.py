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
    def add_agent(agent_info):
        """
        새로운 에이전트를 데이터베이스에 추가하는 함수.
        """
        agent_id = str(uuid.uuid4())
        agent_data = {
            'agent_id': agent_id,
            'agent_name': agent_info.get('agent_name'),
            'ip': agent_info.get('ip'),
            'streaming_method': agent_info.get('streaming_method'),
            'agent_port': agent_info.get('agent_port', 8000),
            'last_update': datetime.utcnow().isoformat(),
            'frame_transmission_enabled': False,
            'camera_status': [],
            # 추가적인 공통 필드들
        }

        if agent_info.get('streaming_method') == 'RTSP':
            agent_data.update({
                'rtsp_port': agent_info.get('rtsp_port'),
                'mount_point': agent_info.get('mount_point'),
                'rtsp_allowed_ip_range': agent_info.get('rtsp_allowed_ip_range'),
                'stream_uri': agent_info.get('stream_uri'),
            })
        elif agent_info.get('streaming_method') == 'KAFKA':
            agent_data.update({
                'kafka_topic': agent_info.get('kafka_topic'),
                'bootstrap_servers': agent_info.get('bootstrap_servers'),
                'frame_rate': agent_info.get('frame_rate'),
                'image_width': agent_info.get('image_width'),
                'image_height': agent_info.get('image_height'),
            })
        else:
            # 지원하지 않는 스트리밍 방식일 경우 예외 처리
            raise ValueError(f"Unsupported streaming method: {agent_info.get('streaming_method')}")

        # 데이터베이스에 에이전트 정보 저장
        db_instance.agent_table.insert(agent_data)
        return agent_id

    @staticmethod
    def upsert_agent(agent_data):
        Agent = Query()
        db_instance.agent_table.upsert(agent_data, Agent.agent_id == agent_data['agent_id'])

    @staticmethod
    def get_agent(agent_id):
        Agent = Query()
        result = db_instance.agent_table.search(Agent.agent_id == agent_id)
        if result:
            return result[0]
        else:
            return None

    @staticmethod
    def update_agent(agent_id, data):
        Agent = Query()
        db_instance.agent_table.update(data, Agent.agent_id == agent_id)

    @staticmethod
    def delete_agent(agent_id):
        Agent = Query()
        db_instance.agent_table.remove(Agent.agent_id == agent_id)

    @staticmethod
    def get_all_agents():
        return db_instance.agent_table.all()

    @staticmethod
    def get_agent_by_name(agent_name):
        Agent = Query()
        result = db_instance.agent_table.search(Agent.agent_name == agent_name)
        return result