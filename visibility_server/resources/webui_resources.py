"""

webui 에서 view 기능을 담당하는 api 구현체 모음

"""
from flask_restful import Resource
from flask import jsonify
from models.agent import AgentModel
from flasgger import swag_from

class GetAgentList(Resource):
    @swag_from('../docs/webui_get_agent_list.yml')
    def get(self):
        agents = AgentModel.get_all_agents()
        return jsonify([{
                'agent_id': agent['agent_id'],
                'agent_name': agent['agent_name'],
                'ip': agent['ip'],
                'port': agent['rtsp_port'],
                'stream_uri': agent['stream_uri'],
                'last_update': agent['last_update'],
                'camera_status': agent['camera_status'],
                'frame_transmission_enabled': agent['frame_transmission_enabled']
        } for agent in agents])

class GetAgentDetails(Resource):
    @swag_from('../docs/webui_get_agent_details.yml')
    def get(self, agent_id):
        agent = AgentModel.get_agent(agent_id)
        if agent:
            return jsonify({
                'agent_id': agent['agent_id'],
                'agent_name': agent['agent_name'],
                'ip': agent['ip'],
                'port': agent['rtsp_port'],
                'stream_uri': agent['stream_uri'],
                'rtsp_allowed_ip_range': agent['rtsp_allowed_ip_range'],
                'last_update': agent['last_update'],
                'camera_status': agent['camera_status'],
                'frame_transmission_enabled': agent['frame_transmission_enabled']
            })
        else:
            return {'message': 'Agent not found'}, 404