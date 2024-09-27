"""
서버와 agent들이 통신할때 사용하는 API 모음

"""

from flask import request
from flask_restful import Resource
from flasgger import swag_from
from datetime import datetime

from models.agent import AgentModel

import logging


# 처음 Agent 가 Visiblity 서버에 접속할때 알림
class AgentRegister(Resource):
    @swag_from('../docs/agent_register.yml')
    def post(self):
        data = request.get_json()
        agent_name = data.get('agent_name')
        ip = data.get('ip')
        port = data.get('port')
        stream_uri = data.get('stream_uri')

        if not agent_name or not ip or not port:
            return {'message': 'agent_name, ip, and port are required'}, 400

        # Agent 등록
        agent_id = AgentModel.add_agent(agent_name, ip, port, stream_uri)
        return {'message': 'Agent registered successfully', 'agent_id': agent_id}, 201


class AgentUpdateStatus(Resource):
    @swag_from('../docs/agent_update_status.yml')
    def post(self):
        data = request.get_json()
        agent_id = data.get('agent_id')
        if not agent_id:
            return {'message': 'agent_id is required'}, 400

        agent = AgentModel.get_agent(agent_id)
        if not agent:
            return {'message': 'Agent not found'}, 404

        agent_data = agent.copy()
        agent_data.update({
            'last_update': datetime.utcnow().isoformat(),
            'camera_status': data.get('camera_status', agent.get('camera_status', [])),
            'frame_transmission_enabled': data.get('frame_transmission_enabled', agent.get('frame_transmission_enabled', False))
        })

        AgentModel.upsert_agent(agent_data)
        return {'message': 'Status updated successfully'}, 200

class AgentGetConfig(Resource):
    @swag_from('../docs/agent_get_config.yml')
    def get(self):
        agent_id = request.args.get('agent_id')
        if not agent_id:
            app.logger.error('agent_id is missing in request')
            return {'message': 'agent_id is required'}, 400

        agent = AgentModel.get_agent(agent_id)
        if not agent:
            return {'message': 'Agent not found'}, 404

        return {
            'frame_transmission_enabled': agent.get('frame_transmission_enabled', False)
        }, 200
