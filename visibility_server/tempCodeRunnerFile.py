from flask import Flask
from flask_restful import Api
from flasgger import Swagger

from resources.agent_resources import AgentUpdateStatus, AgentGetConfig
from resources.user_resources import GetCameraStatus, SetFrameTransmission

import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
api = Api(app)

# Swagger 설정
app.config['SWAGGER'] = {
    'title': 'Camera Status Visibility API',
    'uiversion': 3
}
swagger = Swagger(app)

# 로깅
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = RotatingFileHandler('logs/app.log', maxBytes=1000000, backupCount=5)
handler.setLevel(logging.INFO)

formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)

# Flask 앱의 로거 설정
app.logger = logger


# 엔드포인트 등록
api.add_resource(AgentRegister, '/agent/register')
api.add_resource(AgentUpdateStatus, '/agent/update_status')
api.add_resource(AgentGetConfig, '/agent/get_config')
api.add_resource(GetCameraStatus, '/api/get_camera_status')
api.add_resource(SetFrameTransmission, '/api/set_frame_transmission')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
