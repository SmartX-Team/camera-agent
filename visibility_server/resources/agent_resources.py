"""
Visibility 서버와 agent들이 통신할때 사용하는 API 모음

"""

from flask import request
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
        agent_name = data.get('agent_name')
        host_ip = self.get_client_ip()
        streaming_method = data.get('streaming_method', 'RTSP').upper()
        agent_port = data.get('agent_port', 8000)

        if not agent_name or not host_ip:
            return {'message': 'agent_name and ip are required'}, 400

        agent_info = {
            'agent_name': agent_name,
            'ip': host_ip,
            'streaming_method': streaming_method,
            'agent_port': agent_port,
        }

        if streaming_method == 'RTSP':
            rtsp_port = data.get('rtsp_port')
            mount_point = data.get('mount_point', '/test')
            rtsp_allowed_ip_range = data.get('rtsp_allowed_ip_range', '0.0.0.0/0')

            if not rtsp_port:
                return {'message': 'rtsp_port is required for RTSP streaming'}, 400

            stream_uri = f'rtsp://{host_ip}:{rtsp_port}{mount_point}'

            agent_info.update({
                'rtsp_port': rtsp_port,
                'mount_point': mount_point,
                'rtsp_allowed_ip_range': rtsp_allowed_ip_range,
                'stream_uri': stream_uri,
            })

        elif streaming_method == 'KAFKA':
            kafka_topic = data.get('kafka_topic')
            bootstrap_servers = data.get('bootstrap_servers')
            frame_rate = data.get('frame_rate', 5)
            image_width = data.get('image_width', 640)
            image_height = data.get('image_height', 480)

            if not kafka_topic or not bootstrap_servers:
                return {'message': 'kafka_topic and bootstrap_servers are required for KAFKA streaming'}, 400

            agent_info.update({
                'kafka_topic': kafka_topic,
                'bootstrap_servers': bootstrap_servers,
                'frame_rate': frame_rate,
                'image_width': image_width,
                'image_height': image_height,
            })
        else:
            return {'message': f'Unsupported streaming method: {streaming_method}'}, 400

        try:
            agent_id = AgentModel.add_agent(agent_info)
            return {'message': 'Agent registered successfully', 'agent_id': agent_id}, 201
        except ValueError as ve:
            logger.error(f"Agent registration failed: {ve}")
            return {'message': str(ve)}, 400
        except Exception as e:
            logger.error(f"Agent registration failed: {e}")
            return {'message': 'Internal server error'}, 500
    
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

        # 필요에 따라 streaming_method에 따른 추가 처리 가능

        AgentModel.upsert_agent(agent_data)
        return {'message': 'Status updated successfully'}, 200


class AgentGetConfig(Resource):
    @swag_from('../docs/agent_get_config.yml')
    def get(self):
        agent_id = request.args.get('agent_id')
        if not agent_id:
            logger.error('agent_id is missing in request')
            return {'message': 'agent_id is required'}, 400

        agent = AgentModel.get_agent(agent_id)
        if not agent:
            return {'message': 'Agent not found'}, 404

        config = {
            'frame_transmission_enabled': agent.get('frame_transmission_enabled', False)
        }

        if agent.get('streaming_method') == 'RTSP':
            config.update({
                'rtsp_port': agent.get('port'),
                'mount_point': agent.get('mount_point'),
                'stream_uri': agent.get('stream_uri'),
                'rtsp_allowed_ip_range': agent.get('rtsp_allowed_ip_range'),
            })
        elif agent.get('streaming_method') == 'KAFKA':
            config.update({
                'kafka_topic': agent.get('kafka_topic'),
                'bootstrap_servers': agent.get('bootstrap_servers'),
                'frame_rate': agent.get('frame_rate'),
                'image_width': agent.get('image_width'),
                'image_height': agent.get('image_height'),
            })

        return config, 200

