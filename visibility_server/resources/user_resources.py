"""
사용자가 Agent를 제어하기 위한 API 엔드포인트들의 실제 로직들의 구현체 모음

"""

from flask import request
from flask_restful import Resource
from flasgger import swag_from

from models.agent import AgentModel

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

        agent['frame_transmission_enabled'] = enabled
        AgentModel.update_agent(agent_id, agent)

        return {'message': 'Frame transmission setting updated'}, 200
