"""

250517 제미나이 2.5 의 도움을 받아 새롭게 코드 리팩토링 !!


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
# from tinydb import Query # Query는 이제 database.py 내부에서만 사용됩니다.
from database import db_instance # 수정된 database.py의 db_instance를 임포트합니다.

class AgentModel:
    @staticmethod
    def add_agent(agent_info_from_api: dict):
        """
        새로운 에이전트와 그 에이전트가 관리하는 카메라 정보를 데이터베이스에 추가합니다.
        agent_info_from_api는 API 리소스로부터 받은 초기 에이전트 및 카메라 정보입니다.
        AgentModel이 agent_id 생성, last_update 타임스탬프 설정 등 완전한 문서를 만듭니다.
        """
        agent_id = str(uuid.uuid4())
        current_time = datetime.utcnow().isoformat()

        processed_cameras = []
        if 'cameras' in agent_info_from_api and isinstance(agent_info_from_api['cameras'], list):
            for cam_data in agent_info_from_api['cameras']:
                camera = {
                    'camera_id': cam_data.get('camera_id', str(uuid.uuid4())),
                    'camera_name': cam_data.get('camera_name', f"Cam-{uuid.uuid4().hex[:6]}"),
                    'status': cam_data.get('status', 'inactive'),
                    'type': cam_data.get('type', 'rgb'),
                    'environment': cam_data.get('environment', 'real'),
                    'stream_protocol': cam_data.get('stream_protocol'),
                    'stream_details': cam_data.get('stream_details', {}), # API에서 이미 상세정보를 구성해서 전달 가정
                    'resolution': cam_data.get('resolution'),
                    'fps': cam_data.get('fps'),
                    'location': cam_data.get('location', 'N/A'),
                    'host_pc_name': cam_data.get('host_pc_name', 'N/A'),
                    'frame_transmission_enabled': cam_data.get('frame_transmission_enabled', False),
                    'last_update': current_time # 카메라 정보도 함께 생성되므로 동일 시점 사용
                }
                processed_cameras.append(camera)

        agent_document = {
            'agent_id': agent_id,
            'agent_name': agent_info_from_api.get('agent_name', f'Agent-{agent_id[:8]}'),
            'ip': agent_info_from_api.get('ip'),
            'agent_port': agent_info_from_api.get('agent_port', 8000),
            'last_update': current_time,
            'cameras': processed_cameras,
            'status': agent_info_from_api.get('status', 'active')
        }

        db_instance.insert_agent_document(agent_document)
        return agent_id

    @staticmethod
    def upsert_agent(agent_document_to_upsert: dict):
        """
        에이전트 문서를 업데이트하거나 존재하지 않으면 새로 추가합니다.
        agent_document_to_upsert는 완전한 에이전트 문서여야 하며,
        이 메서드 내에서 agent_id 및 last_update를 관리합니다.
        """
        if 'agent_id' not in agent_document_to_upsert or not agent_document_to_upsert['agent_id']:
            # agent_id가 없거나 비어있으면 새로 생성 (주로 새 문서 삽입 시)
            agent_document_to_upsert['agent_id'] = str(uuid.uuid4())
            # 새 문서이므로 카메라 ID 등도 여기서 재할당하거나 검증 필요 (정책에 따라)

        agent_document_to_upsert['last_update'] = datetime.utcnow().isoformat()
        # 카메라 리스트 내부의 last_update도 갱신 (선택적)
        if 'cameras' in agent_document_to_upsert and isinstance(agent_document_to_upsert['cameras'], list):
            for camera in agent_document_to_upsert['cameras']:
                camera['last_update'] = agent_document_to_upsert['last_update']

        db_instance.upsert_agent_document(agent_document_to_upsert, agent_document_to_upsert['agent_id'])
        return agent_document_to_upsert['agent_id']


    @staticmethod
    def get_agent(agent_id: str):
        """agent_id로 특정 에이전트의 정보를 조회합니다."""
        return db_instance.get_agent_document_by_id(agent_id)

    @staticmethod
    def update_agent(agent_id: str, data_to_update: dict):
        """
        특정 에이전트의 정보를 부분적으로 업데이트합니다.
        data_to_update 딕셔너리에는 변경할 필드와 값이 포함됩니다.
        last_update 타임스탬프는 이 메서드에서 자동으로 관리합니다.
        """
        data_to_update['last_update'] = datetime.utcnow().isoformat()
        # 만약 cameras 필드가 업데이트 내용에 포함된다면, 각 카메라의 last_update도 갱신 가능
        if 'cameras' in data_to_update and isinstance(data_to_update['cameras'], list):
            for camera_data in data_to_update['cameras']:
                if isinstance(camera_data, dict): # 카메라 데이터가 딕셔너리 형태인지 확인
                     camera_data['last_update'] = data_to_update['last_update']

        success = db_instance.update_agent_document(agent_id, data_to_update)
        return success # 업데이트 성공 여부 (True/False) 반환

    @staticmethod
    def delete_agent(agent_id: str):
        """agent_id로 특정 에이전트를 삭제합니다."""
        success = db_instance.delete_agent_document_by_id(agent_id)
        return success # 삭제 성공 여부 (True/False) 반환

    @staticmethod
    def get_all_agents(include_summary=False):
        """
        모든 에이전트 정보를 반환합니다.
        include_summary가 True이면 카메라 요약 정보를 추가합니다.
        """
        agents = db_instance.get_all_agent_documents()
        if include_summary and agents: # agents가 None이거나 비어있지 않은 경우에만 요약 계산
            for agent in agents:
                if 'cameras' in agent and agent['cameras']:
                    type_counts = {}
                    env_set = set()
                    active_cameras = 0
                    for cam in agent['cameras']:
                        cam_type = cam.get('type', 'N/A')
                        type_counts[cam_type] = type_counts.get(cam_type, 0) + 1
                        if cam.get('environment'):
                            env_set.add(cam.get('environment'))
                        if cam.get('status') == 'active' or cam.get('status') == 'streaming': # 'streaming'도 활성 상태로 간주
                            active_cameras +=1
                    
                    agent['camera_summary'] = ", ".join([f"{t}:{c}" for t, c in type_counts.items()]) if type_counts else "N/A"
                    agent['environment_summary'] = ", ".join(list(env_set)) if env_set else "N/A"
                    agent['active_camera_count'] = active_cameras # 활성 카메라 수 추가
                    agent['total_camera_count'] = len(agent['cameras']) # 전체 카메라 수 추가
                else:
                    agent['camera_summary'] = "No cameras"
                    agent['environment_summary'] = "N/A"
                    agent['active_camera_count'] = 0
                    agent['total_camera_count'] = 0
        return agents

    @staticmethod
    def get_agent_by_name(agent_name: str):
        """agent_name으로 에이전트 정보를 조회합니다 (이름은 중복 가능, 리스트 반환)."""
        return db_instance.get_agent_documents_by_name(agent_name)

    # --- 카메라 개별 관리를 위한 추가적인 메서드 ---
    @staticmethod
    def add_camera_to_agent(agent_id: str, camera_info_from_api: dict):
        """특정 에이전트에 새 카메라를 추가합니다."""
        agent = AgentModel.get_agent(agent_id)
        if not agent:
            # 애플리케이션에 맞는 적절한 예외 발생 또는 오류 코드 반환
            raise ValueError(f"Agent with id {agent_id} not found.")

        current_time = datetime.utcnow().isoformat()
        new_camera_id = camera_info_from_api.get('camera_id', str(uuid.uuid4()))
        new_camera = {
            'camera_id': new_camera_id,
            'camera_name': camera_info_from_api.get('camera_name', f'Cam-{new_camera_id[:6]}'),
            'status': camera_info_from_api.get('status', 'inactive'),
            'type': camera_info_from_api.get('type', 'rgb'),
            'environment': camera_info_from_api.get('environment', 'real'),
            'stream_protocol': camera_info_from_api.get('stream_protocol'),
            'stream_details': camera_info_from_api.get('stream_details', {}),
            'resolution': camera_info_from_api.get('resolution'),
            'fps': camera_info_from_api.get('fps'),
            'location': camera_info_from_api.get('location', 'N/A'),
            'host_pc_name': camera_info_from_api.get('host_pc_name', 'N/A'),
            'frame_transmission_enabled': camera_info_from_api.get('frame_transmission_enabled', False),
            'last_update': current_time
        }
        # stream_details 채우는 로직 (add_agent와 유사하게 필요시 추가)
        
        agent.setdefault('cameras', []).append(new_camera)
        
        update_payload = {
            'cameras': agent['cameras'],
            # last_update는 update_agent 메서드에서 처리됨
        }
        if AgentModel.update_agent(agent_id, update_payload):
            return new_camera_id
        else:
            # 업데이트 실패 시 처리
            raise Exception(f"Failed to add camera to agent {agent_id}")


    @staticmethod
    def update_camera_in_agent(agent_id: str, camera_id: str, camera_update_data_from_api: dict):
        """특정 에이전트의 특정 카메라 정보를 업데이트합니다."""
        agent = AgentModel.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent with id {agent_id} not found.")
        
        camera_found = False
        current_time = datetime.utcnow().isoformat()
        if 'cameras' in agent and isinstance(agent['cameras'], list):
            for i, cam in enumerate(agent['cameras']):
                if cam['camera_id'] == camera_id:
                    # 기존 카메라 정보를 유지하면서 업데이트할 필드만 변경
                    for key, value in camera_update_data_from_api.items():
                        if key == 'stream_details' and isinstance(value, dict) and isinstance(cam.get(key), dict):
                             cam[key].update(value) # 기존 stream_details에 병합
                        else:
                            cam[key] = value
                    cam['last_update'] = current_time # 카메라 자체의 last_update
                    # agent['cameras'][i] = cam # 리스트 내 객체는 직접 수정됨
                    camera_found = True
                    break
        
        if not camera_found:
            raise ValueError(f"Camera with id {camera_id} not found in agent {agent_id}.")

        update_payload = {
            'cameras': agent['cameras'], # 수정된 전체 카메라 리스트
             # last_update는 update_agent 메서드에서 처리됨
        }
        return AgentModel.update_agent(agent_id, update_payload)

    @staticmethod
    def remove_camera_from_agent(agent_id: str, camera_id: str):
        """특정 에이전트에서 카메라를 제거합니다."""
        agent = AgentModel.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent with id {agent_id} not found.")

        original_camera_count = len(agent.get('cameras', []))
        # cameras 필드가 없거나 비어있는 경우를 안전하게 처리
        agent['cameras'] = [cam for cam in agent.get('cameras', []) if cam.get('camera_id') != camera_id]
        
        if len(agent.get('cameras', [])) == original_camera_count:
            raise ValueError(f"Camera with id {camera_id} not found or not removed from agent {agent_id}.")

        update_payload = {
            'cameras': agent['cameras'],
            # last_update는 update_agent 메서드에서 처리됨
        }
        return AgentModel.update_agent(agent_id, update_payload)