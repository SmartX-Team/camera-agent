"""

250517 해당코드도 제미나이 2.5의 도움으로 리팩토링 및 업데이트해둠!!


Visibility 서버와 agent들이 통신할때 사용하는 API 모음

"""

from flask import request, jsonify 
from flask_restful import Resource
from flasgger import swag_from
from datetime import datetime

from models.agent import AgentModel
import logging

""" 처음 Agent 가 Visibility 서버에 접속할때 알림
현재는 내부 DB에 처음 agent가 등록할때 관련 정보 저장
"""
logger = logging.getLogger(__name__)

class AgentRegister(Resource):
    @swag_from('../docs/agent_register.yml')
    def post(self):
        data = request.get_json()
        if not data:
            logger.warning("AgentRegister: Empty JSON payload received.")
            return {'message': 'Request body must be JSON'}, 400

        agent_name = data.get('agent_name')
        host_ip = self.get_client_ip()
        agent_port = data.get('agent_port', 8000)
        cameras_payload = data.get('cameras')
        agent_status_payload = data.get('status', 'active')

        if not agent_name:
            logger.warning("AgentRegister: 'agent_name' is missing.")
            return {'message': 'agent_name is required'}, 400
        if cameras_payload is None or not isinstance(cameras_payload, list): # None 체크 추가
            logger.warning("AgentRegister: 'cameras' field must be a list or is missing.")
            # 'cameras'가 필수가 아니라면 이 검사를 조정할 수 있습니다.
            # 여기서는 필수라고 가정하고 에러 처리합니다.
            # 만약 빈 리스트도 허용한다면, cameras_payload if cameras_payload is not None else [] 등으로 처리 가능
            return {'message': 'cameras list is required and must be a list'}, 400


        agent_info_for_model = {
            'agent_name': agent_name,
            'ip': host_ip,
            'agent_port': agent_port,
            'cameras': cameras_payload,
            'status': agent_status_payload
        }
        logger.info(f"AgentRegister: Attempting to register agent: {agent_name} from IP: {host_ip}")

        try:
            agent_id = AgentModel.add_agent(agent_info_for_model)

            # AgentModel.add_agent의 반환 값(agent_id)을 확인합니다.
            if agent_id:
                logger.info(f"AgentRegister: Agent '{agent_name}' registered successfully with ID: {agent_id}")
                return {'message': 'Agent registered successfully', 'agent_id': agent_id}, 201
            else:
                # agent_id가 None이면 AgentModel.add_agent에서 DB 등록에 실패한 것입니다.
                logger.error(f"AgentRegister: Failed to register agent '{agent_name}'. AgentModel.add_agent returned None (DB insertion likely failed).")
                return {'message': 'Agent registration failed due to an internal server error.'}, 500

        except ValueError as ve: # AgentModel에서 발생시킬 수 있는 유효성 검사 오류
            logger.error(f"AgentRegister: Validation error for agent '{agent_name}'. Details: {ve}", exc_info=True) # exc_info 추가
            return {'message': str(ve)}, 400
        except Exception as e: # 그 외 예기치 않은 모든 오류
            logger.error(f"AgentRegister: Unexpected error while trying to register agent '{agent_name}'. Error: {e}", exc_info=True)
            return {'message': 'Internal server error during agent registration'}, 500



    def get_client_ip(self):
        if request.headers.getlist("X-Forwarded-For"):
            ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
        else:
            ip = request.remote_addr
        return ip


class AgentUpdateStatus(Resource):
    @swag_from('../docs/agent_update_status.yml') # YAML 파일 업데이트 필수
    def post(self):
        data = request.get_json()
        if not data:
            logger.warning("AgentUpdateStatus: Empty JSON payload received.")
            return {'message': 'Request body must be JSON'}, 400

        agent_id = data.get('agent_id')
        if not agent_id:
            logger.warning("AgentUpdateStatus: 'agent_id' is missing in payload.")
            return {'message': 'agent_id is required'}, 400

        logger.info(f"AgentUpdateStatus: Attempting to update status for agent_id: {agent_id}")

        # AgentModel.get_agent를 호출하기 전에 agent_id 존재 유무만 확인하는 것이 아니라,
        # get_agent를 호출하여 실제 agent 객체를 가져오는 것이 더 안전 (AgentModel v2에서 이미 이렇게 함)
        # AgentModel.update_agent 내부에서 last_update 타임스탬프 처리
        update_payload_for_model = {}
        # 에이전트가 자신의 전체 카메라 목록(상태 포함)을 보냈다고 가정
        if 'cameras' in data:
            # cameras 데이터의 유효성 검사는 AgentModel에서 수행하거나 여기서 간단히 타입 체크 가능
            if not isinstance(data['cameras'], list):
                logger.warning(f"AgentUpdateStatus: 'cameras' field for agent {agent_id} must be a list.")
                return {'message': "'cameras' field must be a list"},400
            update_payload_for_model['cameras'] = data['cameras']

        # 에이전트 자체의 상태 업데이트 (선택적)
        if 'status' in data: # 페이로드 필드명을 'status'로 일관되게 사용 (이전 agent_status에서 변경)
            update_payload_for_model['status'] = data['status']
        
        # 업데이트할 다른 최상위 에이전트 필드가 있다면 여기에 추가
        # 예: if 'agent_port' in data: update_payload_for_model['agent_port'] = data['agent_port']

        if not update_payload_for_model:
            logger.info(f"AgentUpdateStatus: No updatable fields provided for agent_id: {agent_id}")
            return {'message': 'No updatable fields provided for agent status update'}, 400

        try:
            # 먼저 에이전트 존재 확인 (선택적이지만, 불필요한 업데이트 시도 방지)
            # AgentModel.update_agent 내부에서 last_update 자동 관리
            # AgentModel.get_agent를 여기서 호출하여 존재하지 않으면 404를 먼저 반환하는 것도 좋음
            if not AgentModel.get_agent(agent_id): # 에이전트 존재 확인
                logger.warning(f"AgentUpdateStatus: Agent not found with agent_id: {agent_id}")
                return {'message': 'Agent not found'}, 404

            success = AgentModel.update_agent(agent_id, update_payload_for_model)
            if success:
                logger.info(f"AgentUpdateStatus: Agent status updated successfully for agent_id: {agent_id}")
                return {'message': 'Agent status updated successfully'}, 200
            else:
                # 이 경우는 DB에서 업데이트된 문서가 없음을 의미 (agent_id는 존재했으나 변경사항이 없거나 DB오류)
                logger.warning(f"AgentUpdateStatus: Agent status update for agent_id {agent_id} reported no changes or failed at DB level.")
                return {'message': 'Agent status update failed or no effective changes made'}, 400 # 좀 더 명확한 메시지
        except ValueError as ve: # AgentModel 내부에서 발생할 수 있는 데이터 유효성 오류
            logger.error(f"AgentUpdateStatus: Validation error for agent {agent_id}. Details: {ve}")
            return {'message': str(ve)}, 400
        except Exception as e:
            logger.error(f"AgentUpdateStatus: Failed to update agent status for {agent_id}. Error: {e}", exc_info=True)
            return {'message': 'Internal server error during agent status update'}, 500


class AgentGetConfig(Resource):
    @swag_from('../docs/agent_get_config.yml') # YAML 파일 업데이트 필수
    def get(self):
        agent_id = request.args.get('agent_id')
        if not agent_id:
            logger.warning("AgentGetConfig: 'agent_id' is missing in request arguments.")
            return {'message': 'agent_id is required in query parameters'}, 400

        logger.info(f"AgentGetConfig: Attempting to get config for agent_id: {agent_id}")

        # AgentModel.get_agent는 db_instance.get_agent_document_by_id 호출
        agent_document = AgentModel.get_agent(agent_id)
        
        if not agent_document:
            logger.warning(f"AgentGetConfig: Agent not found with agent_id: {agent_id}")
            return {'message': 'Agent not found'}, 404

        # AgentModel.get_agent가 반환하는 문서는 DB의 내용 그대로이므로,
        # API 응답으로 바로 사용 가능. (TinyDB는 기본적으로 _id 필드를 문서에 추가하지 않음)
        logger.info(f"AgentGetConfig: Configuration retrieved successfully for agent_id: {agent_id}")
        return jsonify(agent_document) # 명시적으로 jsonify 사용, HTTP Status 200은 기본값