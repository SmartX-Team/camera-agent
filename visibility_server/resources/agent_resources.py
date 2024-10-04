"""
Visibility 서버와 agent들이 통신할때 사용하는 API 모음

"""

from flask import request
from flask_restful import Resource
from flasgger import swag_from
from datetime import datetime

from models.agent import AgentModel

""" 처음 Agent 가 Visibility 서버에 접속할때 알림
현재는 내부 DB에 처음 agent가 등록할때 관련 정보 저장
"""
class AgentRegister(Resource):
    @swag_from('../docs/agent_register.yml')
    def post(self):
        data = request.get_json()
        agent_name = data.get('agent_name')
        host_ip = self.get_client_ip()
        rtsp_port = data.get('rtsp_port')
        mount_point = data.get('mount_point', '/test')
        rtsp_allowed_ip_range = data.get('rtsp_allowed_ip_range', '0.0.0.0/0')
        agent_port = data.get('agent_port', 8000)

        if not agent_name or not host_ip or not rtsp_port or not agent_port:
            return {'message': 'agent_name, ip, rtsp_port, and agent_port are required'}, 400
        # stream_url 설정
        stream_uri = f'rtsp://{host_ip}:{rtsp_port}{mount_point}' 

        # 에이전트 등록 또는 기존 에이전트 반환
        agent_id, agent_data, existing = AgentModel.add_agent(
            agent_name, host_ip, rtsp_port, agent_port, stream_uri, rtsp_allowed_ip_range
        )

        if existing:
            return {
                'message': 'Existing agent found, returning existing information',
                'agent_id': agent_id,
                'agent_data': agent_data
            }, 200
        else:
            return {
                'message': 'Agent registered successfully',
                'agent_id': agent_id
            }, 201
    
    # Agent 등록시 Host의 IP를 가져오는 함수
    def get_client_ip(self):
        if request.headers.getlist("X-Forwarded-For"):
            ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0]
        else:
            ip = request.remote_addr
        return ip


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
            return {'message': 'agent_id is required'}, 400

        agent = AgentModel.get_agent(agent_id)
        if not agent:
            return {'message': 'Agent not found'}, 404

        return {
            'frame_transmission_enabled': agent.get('frame_transmission_enabled', False)
        }, 200
