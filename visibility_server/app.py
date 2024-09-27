"""

Flask 기반 메인 app.py 파일임

프로젝트 구조는 

resources 폴더에 실제 엔드포인트 호출시 처리하는 로직 구현

DB 연결해서 처리하는 작업은 models 폴더에 있는 agent.py와 database.py 에 묶여있는데 
현재 데이터 모델에 비즈니스 로직이랑 데이터베이스 로직이 밀접하게 연결되어 있음
개발 속도를 빠르게 할 수 있다는 장점이 있는데, 만약 팔콘 구현한걸 이후에도 쭉 사용한다면 유지보수를 위해 로직을 논리적으로 명확히 분리해두길 바람

주석 작성일 240927 송인용


"""


from flask import Flask
from flask_restful import Api
from flasgger import Swagger

from resources.agent_resources import AgentUpdateStatus, AgentGetConfig, AgentRegister
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


log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, 'app.log')

handler = RotatingFileHandler(log_file, maxBytes=1000000, backupCount=5)
handler.setLevel(logging.INFO)

formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
handler.setFormatter(formatter)

# 로깅
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Flask 앱의 로거 설정
app.logger = logger


# 엔드포인트 등록 (agent가 호출하는 api들은 /agent/ , 일반 유저가 호출하는 api들은 /api/ 엔드 포인트로 분리함)
api.add_resource(AgentRegister, '/agent/register')
api.add_resource(AgentUpdateStatus, '/agent/update_status')
api.add_resource(AgentGetConfig, '/agent/get_config')
api.add_resource(GetCameraStatus, '/api/get_camera_status')
api.add_resource(SetFrameTransmission, '/api/set_frame_transmission')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
