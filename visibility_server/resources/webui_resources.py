from flask_restful import Resource
from flask import jsonify
from flask import request
from models.agent import AgentModel
from flasgger import swag_from
import logging
import json
from datetime import datetime
import requests
logger = logging.getLogger(__name__)

class GetAgentList(Resource):
    @swag_from('../docs/webui_get_agent_list.yml') # Swagger 문서 경로 확인
    def get(self):
        logger.info("WebUI request: GetAgentList called")
        try:
            # AgentModel에서 include_summary=True 옵션을 사용하여 요약 정보와 함께 에이전트 목록을 가져옵니다.
            # AgentModel.get_all_agents는 이제 [(에이전트 문서), ...] 형태를 반환합니다.
            agents_from_db = AgentModel.get_all_agents(include_summary=True) 
            
            response_data = []
            if agents_from_db:
                for agent in agents_from_db:
                    # UI가 필요한 에이전트 레벨 정보 및 요약 정보만 선택적으로 구성
                    agent_info_for_ui = {
                        'agent_id': agent.get('agent_id'),
                        'agent_name': agent.get('agent_name'),
                        'ip': agent.get('ip'),
                        'agent_port': agent.get('agent_port'), # Agent의 FastAPI/관리 API 포트
                        'status': agent.get('status', 'unknown'), # Agent 자체의 상태
                        'last_update': agent.get('last_update'),
                        
                        # AgentModel.get_all_agents(include_summary=True)가 제공하는 요약 정보
                        'camera_summary': agent.get('camera_summary', 'N/A'), 
                        'total_camera_count': agent.get('total_camera_count', 0),
                        'active_camera_count': agent.get('active_camera_count', 0),
                        'environment_summary': agent.get('environment_summary', 'N/A')
                    }
                    response_data.append(agent_info_for_ui)
            
            logger.info(f"Returning {len(response_data)} agents for WebUI list.")
            logger.info(f"GetAgentList: Returning data for WebUI: {json.dumps(response_data, indent=2)}") # JSON 형태로 예쁘게 로깅
            return response_data, 200 # Flask-RESTful은 자동으로 jsonify 처리
        except Exception as e:
            logger.error(f"Error in GetAgentList: {e}", exc_info=True)
            return {"message": "Error fetching agent list", "error": str(e)}, 500

class GetAgentDetails(Resource):
    @swag_from('../docs/webui_get_agent_details.yml') # Swagger 문서 경로 확인
    def get(self, agent_id):
        logger.info(f"WebUI request: GetAgentDetails called for agent_id: {agent_id}")
        try:
            agent_document = AgentModel.get_agent(agent_id) # 전체 에이전트 문서 반환
            
            if agent_document:
                # AgentModel.get_agent가 반환하는 전체 문서를 그대로 사용합니다.
                # 이 문서에는 'agent_id', 'agent_name', 'ip', 'agent_port', 'status', 'last_update'
                # 그리고 가장 중요한 'cameras' 리스트 (각 카메라의 모든 상세 정보 포함)가 들어있습니다.
                # UI(main.js)는 이 전체 구조를 받아 처리하도록 이미 수정되었습니다.
                logger.info(f"Returning details for agent_id: {agent_id}")
                logger.info(f"GetAgentDetails: Returning data for agent_id {agent_id}: {json.dumps(agent_document, indent=2)}")
                return agent_document, 200
            else:
                logger.warning(f"Agent not found for agent_id: {agent_id}")
                return {'message': 'Agent not found'}, 404
        except Exception as e:
            logger.error(f"Error in GetAgentDetails for agent_id {agent_id}: {e}", exc_info=True)
            return {"message": "Error fetching agent details", "error": str(e)}, 500

class CameraFrameTransmissionControl(Resource):
    @swag_from('../docs/webui_control_camera_transmission.yml')
    def post(self, agent_id, camera_id):
        logger.info(f"WebUI request: CameraFrameTransmissionControl for agent {agent_id}, camera {camera_id}")
        try:
            data = request.get_json()
            if data is None:
                return {'message': 'Request body must be JSON'}, 400
            enable = data.get('frame_transmission_enabled')
            if enable is None or not isinstance(enable, bool):
                return {'message': "'frame_transmission_enabled' (boolean) is required"}, 400

            agent = AgentModel.get_agent(agent_id)
            if not agent:
                return {'message': 'Agent not found'}, 404

            camera_updated_in_db = False
            target_camera_index = -1
            if 'cameras' in agent and isinstance(agent['cameras'], list):
                for i, cam in enumerate(agent['cameras']):
                    if cam.get('camera_id') == camera_id:
                        agent['cameras'][i]['frame_transmission_enabled'] = enable
                        agent['cameras'][i]['status'] = 'streaming' if enable else 'active' # 상태도 함께 변경
                        agent['cameras'][i]['last_update'] = datetime.utcnow().isoformat()
                        target_camera_index = i
                        camera_updated_in_db = True
                        break
            
            if not camera_updated_in_db:
                return {'message': 'Camera not found for this agent'}, 404

            update_payload = {
                'cameras': agent['cameras'],
                'last_update': datetime.utcnow().isoformat()
            }
            db_update_success = AgentModel.update_agent(agent_id, update_payload)

            if db_update_success:
                logger.info(f"DB: Camera {camera_id} on agent {agent_id} FTE set to {enable}.")
                
                # --- Agent 직접 호출 (옵션 2) ---
                agent_ip = agent.get('ip')
                agent_api_port = agent.get('agent_port')
                if agent_ip and agent_api_port:
                    agent_control_url = f"http://{agent_ip}:{agent_api_port}"
                    action_endpoint = "/start_stream" if enable else "/stop_stream"
                    
                    logger.info(f"Attempting to call Agent API: POST {agent_control_url}{action_endpoint}")
                    try:
                        # Agent의 FastAPI 엔드포인트는 POST 요청을 받음
                        agent_response = requests.post(f"{agent_control_url}{action_endpoint}", timeout=5)
                        agent_response.raise_for_status() # 2xx가 아니면 예외 발생
                        logger.info(f"Successfully called Agent API {action_endpoint}. Response: {agent_response.text}") # 응답이 JSON이 아닐 수 있음
                        return {'message': f'Frame transmission for camera {camera_id} command sent to agent. New state: {enable}'}, 200
                    except requests.exceptions.RequestException as e_agent_call:
                        logger.error(f"Failed to call Agent API {action_endpoint} for agent {agent_id}: {e_agent_call}")
                        # Agent 직접 호출 실패 시, Agent의 주기적 동기화에 의존
                        return {'message': f'DB updated for camera {camera_id} (FTE: {enable}). Agent direct call failed, will sync later.'}, 202 # Accepted, but not immediately acted upon by agent
                    except Exception as e_unexpected: # JSONDecodeError 등
                        logger.error(f"Unexpected error calling Agent API {action_endpoint} for agent {agent_id}: {e_unexpected}")
                        return {'message': f'DB updated for camera {camera_id} (FTE: {enable}). Error during agent direct call, will sync later.'}, 202
                else:
                    logger.warning(f"Agent IP or port not found for agent {agent_id}. Cannot call Agent API directly. Agent will sync.")
                    return {'message': f'DB updated for camera {camera_id} (FTE: {enable}). Agent will sync this change.'}, 200 # DB는 업데이트됨
            else:
                logger.error(f"Failed to update camera {camera_id} FTE in DB for agent {agent_id}.")
                return {'message': 'Failed to update camera configuration in DB'}, 500
        except Exception as e:
            logger.error(f"Error in CameraFrameTransmissionControl for agent {agent_id}, camera {camera_id}: {e}", exc_info=True)
            return {"message": "Error controlling camera frame transmission", "error": str(e)}, 500
