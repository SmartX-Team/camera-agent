"""


현재 이 코드는 카메라 상태 가시성 API 서버로 시작해서, 지금은 Agent 관리를 위한 서버로 용도가 확장됨


Flask 기반 메인 app.py 파일임

프로젝트 구조는 

resources 폴더에 실제 엔드포인트 호출시 처리하는 로직 구현

DB 연결해서 처리하는 작업은 models 폴더에 있는 agent.py와 database.py 에 묶여있는데 
현재 데이터 모델에 비즈니스 로직이랑 데이터베이스 로직이 밀접하게 연결되어 있음
개발 속도를 빠르게 할 수 있다는 장점이 있는데, 만약 팔콘 구현한걸 이후에도 쭉 사용한다면 유지보수를 위해 로직을 논리적으로 명확히 분리해두길 바람

주석 작성일 240927 송인용


"""

import os
from flask import Flask
from flask_restful import Api
from flask_cors import CORS
from flasgger import Swagger


import threading
import time
from datetime import datetime, timedelta

from models.agent import AgentModel # DB에 등록된 agent 정보 조회용

from resources.agent_resources import AgentUpdateStatus, AgentGetConfig, AgentRegister
from resources.user_resources import GetCameraStatus, SetFrameTransmission
from resources.webui_resources import GetAgentList, GetAgentDetails, CameraFrameTransmissionControl

import logging
from logging.handlers import RotatingFileHandler

#metrics.py 에서 정의한 메트릭 설정 함수들 import
from metrics import setup_metrics, track_metric, update_agent_metrics, record_camera_status

app = Flask(__name__)
CORS(app)
api = Api(app)
setup_metrics(app)

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

@app.errorhandler(Exception)
def handle_error(error):
    app.logger.error(f"An error occurred: {str(error)}")
    return {"error": str(error)}, getattr(error, 'code', 500)


# --- Agent 활성 상태 점검 로직 ---
AGENT_LIVENESS_TIMEOUT_SECONDS = 100  # 예: 100초 동안 업데이트 없으면 비활성 간주
AGENT_CHECK_INTERVAL_SECONDS = 180 # 예: 3분에 한번 (180초) 점검


# 이런 함수들은 나중에 시간되면 다시 모듈화해서 꼭 분리해두기바람 귀찮아서 남기고감
def check_agent_liveness_periodically():
    """주기적으로 Agent 활성 상태를 점검하고 업데이트하는 함수"""
    app.logger.info("Agent liveness checker thread started.")
    while True:
        # Flask 애플리케이션 컨텍스트 내에서 DB 작업을 수행해야 할 경우 app.app_context() 사용
        # 현재 AgentModel은 Flask 앱 컨텍스트에 직접 의존하지 않으므로 바로 사용 가능
        try:
            app.logger.info("Running agent liveness check...")
            all_agents = AgentModel.get_all_agents(include_summary=False)
            if not all_agents:
                app.logger.info("No agents found to check for liveness.")
            else:
                now_utc = datetime.utcnow() # UTC 시간 기준으로 통일
                
                for agent_doc in all_agents:
                    agent_id = agent_doc.get('agent_id')
                    last_update_str = agent_doc.get('last_update')
                    current_agent_status = agent_doc.get('status', 'unknown')

                    if not last_update_str:
                        app.logger.warning(f"Agent {agent_id} has no 'last_update' timestamp. Skipping liveness check.")
                        continue

                    try:
                        # AgentModel이 datetime.utcnow().isoformat()으로 저장하므로, fromisoformat 사용
                        agent_last_update = datetime.fromisoformat(last_update_str)
                        # 만약 last_update가 naive datetime이라면 (시간대 정보 없음), now_utc도 naive하게 만들어야 함.
                        # 하지만 isoformat()은 보통 시간대 정보를 포함하거나 Z로 UTC를 나타냄.
                        # fromisoformat은 이를 잘 처리함.
                    except ValueError:
                        app.logger.error(f"Could not parse last_update timestamp '{last_update_str}' for agent {agent_id}. Skipping.")
                        continue
                    
                    if (now_utc - agent_last_update) > timedelta(seconds=AGENT_LIVENESS_TIMEOUT_SECONDS):
                        if current_agent_status not in ['inactive', 'unreachable', 'error_timeout']: # 이미 비활성이 아니면 변경
                            app.logger.warning(f"Agent {agent_id} timed out (last update: {last_update_str}). Setting status to 'inactive_timeout'.")
                            
                            updated_cameras_list = []
                            if 'cameras' in agent_doc and isinstance(agent_doc.get('cameras'), list):
                                for cam in agent_doc['cameras']:
                                    cam_copy = cam.copy() # 원본 수정을 피하기 위해 복사본 사용
                                    cam_copy['status'] = 'unknown' # 또는 'inactive'
                                    cam_copy['frame_transmission_enabled'] = False
                                    # cam_copy['last_update'] = now_utc.isoformat() # 카메라 상태 변경 시각도 업데이트
                                    updated_cameras_list.append(cam_copy)
                            
                            update_payload = {
                                'status': 'inactive_timeout', # 타임아웃으로 인한 비활성 상태 명시
                                'cameras': updated_cameras_list, # 변경된 카메라 정보
                                'last_update': now_utc.isoformat() # Agent 자체의 last_update도 갱신
                            }
                            AgentModel.update_agent(agent_id, update_payload)
                    # else: # Agent가 활성 상태 (타임아웃되지 않음)
                        # 만약 'inactive_timeout' 상태였다가 다시 업데이트가 들어오면
                        # AgentRegister나 AgentUpdateStatus에서 'active'로 변경해줄 것임.
                        # pass

        except Exception as e:
            app.logger.error(f"Error in agent liveness checker thread: {e}", exc_info=True)
        
        time.sleep(AGENT_CHECK_INTERVAL_SECONDS)


# 리소스 등록 전에 메트릭 데코레이터 적용
AgentRegister.post = track_metric(AgentRegister.post)
AgentUpdateStatus.post = track_metric(AgentUpdateStatus.post)
AgentGetConfig.get = track_metric(AgentGetConfig.get)
GetCameraStatus.get = track_metric(GetCameraStatus.get)
SetFrameTransmission.post = track_metric(SetFrameTransmission.post)
GetAgentList.get = track_metric(GetAgentList.get)
GetAgentDetails.get = track_metric(GetAgentDetails.get)


# 엔드포인트 등록 (agent가 호출하는 api들은 /agent/ , 유저가 agent에 호출하는 api들은 /api/ 엔드 포인트로, webui 에서의 view 기능들은 /webui/  분리함)
api.add_resource(AgentRegister, '/agent_register')
api.add_resource(AgentUpdateStatus, '/agent_update_status')
api.add_resource(AgentGetConfig, '/agent_get_config')

api.add_resource(GetCameraStatus, '/api/get_camera_status')
api.add_resource(SetFrameTransmission, '/api/set_frame_transmission')

api.add_resource(GetAgentList, '/webui/get_agent_list')
api.add_resource(GetAgentDetails, '/webui/agents/<string:agent_id>')
#api.add_resource(UpdateAgentFrameTransmission, '/webui/agents/<string:agent_id>/frame_transmission')
api.add_resource(CameraFrameTransmissionControl, '/webui/agents/<string:agent_id>/cameras/<string:camera_id>/control')

if __name__ == '__main__':
    # Agent 활성 상태 점검 스레드 시작
    # 개발 서버의 리로더가 스레드를 두 번 실행하는 것을 방지하기 위해 Werkzeug 환경 변수 확인
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        liveness_checker_thread = threading.Thread(target=check_agent_liveness_periodically, daemon=True)
        liveness_checker_thread.start()


    port = int(os.environ.get('FLASK_RUN_PORT', 5111))
    app.run(host='0.0.0.0', port=port)