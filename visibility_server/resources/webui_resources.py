from flask_restful import Resource
from flask import jsonify
from models.agent import AgentModel
from flasgger import swag_from

class GetAgentList(Resource):
    @swag_from('../docs/webui_get_agent_list.yml')
    def get(self):
        agents = AgentModel.get_all_agents()
        response_data = []

        for agent in agents:
            agent_data = {
                'agent_id': agent['agent_id'],
                'agent_name': agent['agent_name'],
                'ip': agent['ip'],
                'port': agent['rtsp_port'],
                'stream_uri': agent['stream_uri'],
                'last_update': agent['last_update'],
                'camera_status': agent['camera_status'],
                'frame_transmission_enabled': agent['frame_transmission_enabled']
            }
            
            # RTSP 에이전트인 경우
            if agent['streaming_method'] == 'RTSP':
                agent_data.update({
                    'rtsp_allowed_ip_range': agent.get('rtsp_allowed_ip_range', 'N/A'),
                    'mount_point': agent.get('mount_point', 'N/A'),
                })
            
            # KAFKA 에이전트인 경우
            elif agent['streaming_method'] == 'KAFKA':
                agent_data.update({
                    'kafka_topic': agent.get('kafka_topic', 'N/A'),
                    'bootstrap_servers': agent.get('bootstrap_servers', 'N/A'),
                    'frame_rate': agent.get('frame_rate', 'N/A'),
                    'image_width': agent.get('image_width', 'N/A'),
                    'image_height': agent.get('image_height', 'N/A'),
                })

            response_data.append(agent_data)
        
        return jsonify(response_data)

class GetAgentDetails(Resource):
    @swag_from('../docs/webui_get_agent_details.yml')
    def get(self, agent_id):
        agent = AgentModel.get_agent(agent_id)
        if agent:
            agent_data = {
                'agent_id': agent['agent_id'],
                'agent_name': agent['agent_name'],
                'ip': agent['ip'],
                'port': agent['rtsp_port'],
                'stream_uri': agent['stream_uri'],
                'last_update': agent['last_update'],
                'camera_status': agent['camera_status'],
                'frame_transmission_enabled': agent['frame_transmission_enabled']
            }

            # RTSP 에이전트인 경우
            if agent['streaming_method'] == 'RTSP':
                agent_data.update({
                    'rtsp_allowed_ip_range': agent.get('rtsp_allowed_ip_range', 'N/A'),
                    'mount_point': agent.get('mount_point', 'N/A'),
                })
            
            # KAFKA 에이전트인 경우
            elif agent['streaming_method'] == 'KAFKA':
                agent_data.update({
                    'kafka_topic': agent.get('kafka_topic', 'N/A'),
                    'bootstrap_servers': agent.get('bootstrap_servers', 'N/A'),
                    'frame_rate': agent.get('frame_rate', 'N/A'),
                    'image_width': agent.get('image_width', 'N/A'),
                    'image_height': agent.get('image_height', 'N/A'),
                })

            return jsonify(agent_data)
        else:
            return {'message': 'Agent not found'}, 404
