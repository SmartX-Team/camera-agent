"""
사용자가 Agent를 제어하기 위한 API 엔드포인트들의 실제 로직들의 구현체 모음

"""

from flask import request
from flask_restful import Resource
from flasgger import swag_from

from models.agent import AgentModel
import requests

class GetCameraStatus(Resource):
    @swag_from('../docs/get_camera_status.yml')
    def get(self):
        agents = AgentModel.get_all_agents()
        return agents, 200

class SetFrameTransmission(Resource):
    @swag_from('../docs/set_frame_transmission.yml')
    def post(self):
        data = request.get_json()
        agent_id = data.get('agent_id')
        enabled = data.get('frame_transmission_enabled')

        if agent_id is None or enabled is None:
            return {'message': 'agent_id and frame_transmission_enabled are required'}, 400

        agent = AgentModel.get_agent(agent_id)
        if not agent:
            return {'message': 'Agent not found'}, 404

        # 에이전트의 IP와 포트 가져오기
        agent_ip = agent.get('ip')
        agent_port = agent.get('agent_port', 8000)  # 에이전트의 API 포트 없으면 (기본값 8000)

        if not agent_ip:
            return {'message': 'Agent IP not found'}, 400

        # 에이전트의 API URL 생성
        agent_url = f"http://{agent_ip}:{agent_port}"

        # 에이전트에게 스트림 시작/중지 요청 보내기
        try:
            if enabled:
                response = requests.post(f"{agent_url}/start_stream")
            else:
                response = requests.post(f"{agent_url}/stop_stream")

            if response.status_code == 200:
                # 데이터베이스 업데이트
                agent['frame_transmission_enabled'] = enabled
                AgentModel.update_agent(agent_id, agent)
                return {'message': 'Frame transmission setting updated and agent notified'}, 200
            else:
                return {'message': f'Failed to update agent stream status: {response.text}'}, 500
        except requests.exceptions.RequestException as e:
            return {'message': f'Error connecting to agent: {str(e)}'}, 500
