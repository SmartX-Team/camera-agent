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
from datetime import datetime, timedelta, timezone # 주기적 작업에 필요

# models.agent는 AgentModel 클래스를 포함
from models.agent import AgentModel 
# models.database는 db_instance를 정의
from database import db_instance # 주기적 작업에서 직접 사용

from resources.agent_resources import AgentUpdateStatus, AgentGetConfig, AgentRegister
from resources.user_resources import GetCameraStatus, SetFrameTransmission
from resources.webui_resources import GetAgentList, GetAgentDetails, CameraFrameTransmissionControl

import logging
from logging.handlers import RotatingFileHandler

from metrics import setup_metrics # track_metric은 리소스 파일에서 직접 사용될 수 있음

app = Flask(__name__)
CORS(app)
api = Api(app)
setup_metrics(app)

# Swagger 설정
app.config['SWAGGER'] = {
    'title': 'Visibility & Agent Management API',
    'uiversion': 3,
    'specs_route': "/api/docs/"
}
swagger = Swagger(app)

# --- 로깅 설정 ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_file = os.path.join(log_dir, 'app.log')
handler = RotatingFileHandler(log_file, maxBytes=10000000, backupCount=5)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s (%(funcName)s): %(message)s')
handler.setFormatter(formatter)

app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)

logging.getLogger().addHandler(handler) # 루트 로거에 핸들러 추가
logging.getLogger().setLevel(logging.DEBUG) # 루트 로거의 레벨을 INFO로 설정 (DEBUG로 하면 더 상세)
# --- 로깅 설정 끝 ---

@app.errorhandler(Exception)
def handle_error(error):
    app.logger.error(f"Unhandled Exception: {str(error)}", exc_info=True)
    error_code = getattr(error, 'code', 500)
    return {"message": "An unexpected error occurred.", "error": str(error)}, error_code


# --- Agent 활성 상태 점검 및 자동 정리 로직 ---
AGENT_INACTIVITY_TIMEOUT_SECONDS = int(os.environ.get('AGENT_INACTIVITY_TIMEOUT_SECONDS', 300)) # 5분
AGENT_LIVENESS_CHECK_INTERVAL_SECONDS = int(os.environ.get('AGENT_LIVENESS_CHECK_INTERVAL_SECONDS', 30)) # 1분
AGENT_PURGE_THRESHOLD_DAYS = int(os.environ.get('AGENT_PURGE_THRESHOLD_DAYS', 7)) # 7일
AGENT_PURGE_THRESHOLD_SECONDS = 60
AGENT_PURGE_INTERVAL_SECONDS = int(os.environ.get('AGENT_PURGE_INTERVAL_SECONDS', 120)) # 6시간


def check_and_update_agent_liveness():
    """주기적으로 Agent 활성 상태를 점검하고 'inactive_timeout'으로 업데이트하는 함수"""
    current_logger = app.logger 
    current_logger.info("Running periodic agent liveness check...")
    try:
        all_agents = AgentModel.get_all_agents(include_summary=False)
        if not all_agents:
            current_logger.info("Liveness check: No agents found in DB.")
            return

        current_logger.info(f"Liveness check: Found {len(all_agents)} agent(s) to check.")
        now_utc = datetime.now(timezone.utc) # timezone.utc 사용
        agents_marked_inactive_this_cycle = 0
        
        for agent_doc in all_agents:
            agent_id = agent_doc.get('agent_id')
            last_update_str = agent_doc.get('last_update')
            current_agent_status = agent_doc.get('status', 'unknown')

            current_logger.debug(f"Liveness check for Agent ID: {agent_id}, LastUpdateStr: {last_update_str}, CurrentStatus: {current_agent_status}")

            if not agent_id or not last_update_str:
                current_logger.warning(f"Liveness check: Agent document missing 'agent_id' or 'last_update'. Doc: {agent_doc.get('doc_id', 'Unknown')}")
                continue
            try:
                # ISO 문자열을 파싱할 때 'Z'는 UTC를 의미하지만, fromisoformat은 이를 직접 처리하지 못할 수 있음.
                # replace('Z', '+00:00') 또는 replace('Z', '') 후 tzinfo 설정.
                # 여기서는 replace('Z', '') 후 UTC로 가정하고 tzinfo를 명시적으로 설정합니다.
                if last_update_str.endswith('Z'):
                    agent_last_update_naive = datetime.fromisoformat(last_update_str[:-1]) # 'Z' 제거
                else: # 이미 +00:00 등이 붙어있거나, 타임존 정보가 없는 경우
                    agent_last_update_naive = datetime.fromisoformat(last_update_str)
                
                # 모든 시간을 aware datetime으로 통일 (UTC)
                agent_last_update = agent_last_update_naive.replace(tzinfo=timezone.utc)

            except ValueError:
                current_logger.error(f"Liveness check: Could not parse last_update '{last_update_str}' for agent {agent_id}.")
                continue
            
            # 미래 시간 체크
            if agent_last_update > now_utc + timedelta(minutes=5):
                 current_logger.warning(f"Agent {agent_id} has a future last_update: {last_update_str}. Clock sync issue or invalid data? now_utc: {now_utc.isoformat()}")
                 # continue # 또는 현재 시간으로 간주하고 처리

            time_diff_seconds = (now_utc - agent_last_update).total_seconds()
            current_logger.debug(f"Liveness check for Agent ID: {agent_id}, ParsedLastUpdate: {agent_last_update.isoformat()}, NowUTC: {now_utc.isoformat()}, TimeDiff: {time_diff_seconds:.2f}s, TimeoutThreshold: {AGENT_INACTIVITY_TIMEOUT_SECONDS}s")
            
            is_timed_out = time_diff_seconds > AGENT_INACTIVITY_TIMEOUT_SECONDS
            can_be_marked_inactive = current_agent_status not in ['inactive_timeout', 'unreachable_timeout', 'error_timeout', 'deleted']
            current_logger.debug(f"Liveness check for Agent ID: {agent_id}, IsTimedOut: {is_timed_out}, CanBeMarkedInactive: {can_be_marked_inactive}")

            if is_timed_out and can_be_marked_inactive:
                current_logger.warning(f"Liveness check: Agent {agent_id} TIMED OUT (last update: {last_update_str}, current status: {current_agent_status}). Attempting to set status to 'inactive_timeout'.")
                
                updated_cameras_list = []
                if 'cameras' in agent_doc and isinstance(agent_doc.get('cameras'), list):
                    for cam in agent_doc['cameras']:
                        cam_copy = cam.copy()
                        cam_copy['status'] = 'unknown_timeout'
                        cam_copy['frame_transmission_enabled'] = False
                        updated_cameras_list.append(cam_copy)
                
                update_payload = {
                    'status': 'inactive_timeout', 
                    'cameras': updated_cameras_list,
                    # 'last_update'는 AgentModel.update_agent에서 자동으로 현재 시간(UTC)으로 설정될 것임
                    # 만약 AgentModel.update_agent에서 last_update를 명시적으로 받아서 처리한다면 여기서 now_utc.isoformat() 전달
                }
                # AgentModel.update_agent가 성공/실패 여부를 반환한다고 가정 (True/False)
                update_success = AgentModel.update_agent(agent_id, update_payload) 
                if update_success:
                    current_logger.info(f"Liveness check: Agent {agent_id} successfully updated to 'inactive_timeout'.")
                    agents_marked_inactive_this_cycle += 1
                else:
                    current_logger.error(f"Liveness check: Agent {agent_id} FAILED to update to 'inactive_timeout' via AgentModel.")
        
        if agents_marked_inactive_this_cycle > 0: # 변수명 수정 (agents_marked_inactive -> agents_marked_inactive_this_cycle)
            current_logger.info(f"Liveness check: Marked {agents_marked_inactive_this_cycle} agent(s) as 'inactive_timeout' in this cycle.")
        else:
            current_logger.info("Liveness check: No agents newly marked as inactive in this cycle.")

    except Exception as e:
        current_logger.error(f"Error in agent liveness checker: {e}", exc_info=True)

def purge_very_old_agents():
    """주기적으로 매우 오랫동안 비활성인 Agent를 DB에서 완전히 제거하는 함수"""
    current_logger = app.logger if app else logging.getLogger(__name__ + ".purge_agents")
    current_logger.info("Running periodic task: Purging very old inactive agents...")
    try:
        removed_ids = db_instance.purge_inactive_agents(AGENT_PURGE_THRESHOLD_SECONDS)
        if removed_ids:
            current_logger.info(f"Successfully purged {len(removed_ids)} very old inactive agent(s) from DB: {removed_ids}")
        else:
            current_logger.info("Purge task: No very old inactive agents found to remove.")
    except Exception as e:
        current_logger.error(f"Error in agent purging task: {e}", exc_info=True)


def run_periodic_tasks():
    """주기적인 작업(활성 점검, 자동 삭제)을 실행하는 스케줄러 함수"""
    current_logger = app.logger if app else logging.getLogger(__name__ + ".periodic_tasks")
    current_logger.info("Periodic task scheduler thread started.")
    
    initial_delay = 15 
    current_logger.info(f"Initial delay for periodic tasks: {initial_delay} seconds.")
    time.sleep(initial_delay) 

    last_liveness_check_time = 0.0 
    last_purge_time = 0.0       

    while True:
        current_monotonic_time = time.monotonic()
        
        try:
            if (current_monotonic_time - last_liveness_check_time) >= AGENT_LIVENESS_CHECK_INTERVAL_SECONDS:
                # Flask app 컨텍스트 내에서 실행해야 DB 접근 등에 문제가 없는 경우
                # with app.app_context():
                #    check_and_update_agent_liveness()
                # 현재 AgentModel과 db_instance는 Flask app 컨텍스트에 직접 의존하지 않으므로 바로 호출
                check_and_update_agent_liveness()
                last_liveness_check_time = current_monotonic_time
                
            if (current_monotonic_time - last_purge_time) >= AGENT_PURGE_INTERVAL_SECONDS:
                # with app.app_context():
                #    purge_very_old_agents()
                purge_very_old_agents()
                last_purge_time = current_monotonic_time
        except Exception as e_loop:
            current_logger.error(f"Exception in periodic task loop: {e_loop}", exc_info=True)
            
        next_liveness_check_in = AGENT_LIVENESS_CHECK_INTERVAL_SECONDS - (current_monotonic_time - last_liveness_check_time)
        next_purge_in = AGENT_PURGE_INTERVAL_SECONDS - (current_monotonic_time - last_purge_time)
        
        sleep_duration = max(1.0, min(next_liveness_check_in, next_purge_in, 60.0)) 
        current_logger.debug(f"Periodic tasks: Next check iteration in approx {sleep_duration:.1f} seconds.")
        time.sleep(sleep_duration)
# --- 주기적 작업 함수들 끝 ---


# --- Flask-RESTful 리소스 등록 ---
api.add_resource(AgentRegister, '/agent_register')
api.add_resource(AgentUpdateStatus, '/agent_update_status')
api.add_resource(AgentGetConfig, '/agent_get_config')

api.add_resource(GetCameraStatus, '/api/get_camera_status') # 이전 모델 기반일 수 있음, 검토 필요
api.add_resource(SetFrameTransmission, '/api/set_frame_transmission') # 이전 모델 기반, CameraFrameTransmissionControl로 대체 고려

api.add_resource(GetAgentList, '/webui/get_agent_list')
api.add_resource(GetAgentDetails, '/webui/agents/<string:agent_id>')
api.add_resource(CameraFrameTransmissionControl, '/webui/agents/<string:agent_id>/cameras/<string:camera_id>/control')


app.logger.info("Preparing to start periodic maintenance thread...")

app.logger.info(f"Thread start check: app.debug is {app.debug}")

# WERKZEUG_RUN_MAIN 환경 변수는 Flask 개발 서버의 reloader가 메인 프로세스에서만 true로 설정.
# Gunicorn 사용 시에는 일반적으로 이 변수가 설정되지 않으므로 None이 됨.
werkzeug_run_main_env = os.environ.get("WERKZEUG_RUN_MAIN")
app.logger.info(f"Thread start check: WERKZEUG_RUN_MAIN is '{werkzeug_run_main_env}'")
is_werkzeug_main_process = werkzeug_run_main_env == "true"

# 스레드 시작 조건 정의:
# 1. 디버그 모드가 아니거나 (not app.debug) -> Gunicorn 환경에서 True가 됨
# 2. 또는 Werkzeug 개발 서버의 메인 프로세스인 경우 (is_werkzeug_main_process is True)
should_start_thread = not app.debug or is_werkzeug_main_process
app.logger.info(f"Thread start check: Calculated 'should_start_thread' as: {should_start_thread}")

if should_start_thread:
    app.logger.info("Attempting to start PeriodicAgentMaintenanceThread...")
    try:
        # Gunicorn은 보통 모듈을 한 번만 로드하므로, 스레드가 이미 실행 중인지 확인하는
        # 복잡한 로직은 일반적으로 불필요. 단순하게 생성 및 시작.
        maintenance_thread = threading.Thread(target=run_periodic_tasks, daemon=True)
        maintenance_thread.name = "PeriodicAgentMaintenanceThread"
        maintenance_thread.start()
        time.sleep(0.1) # 스레드가 실제로 시작될 시간을 잠시 줍니다.
        if maintenance_thread.is_alive():
            app.logger.info("PeriodicAgentMaintenanceThread has been started successfully and is alive.")
        else:
            app.logger.error("PeriodicAgentMaintenanceThread was started but is NOT alive. It might have exited or crashed immediately.")
    except Exception as e_thread_start:
        app.logger.error(f"Exception occurred while trying to start PeriodicAgentMaintenanceThread: {e_thread_start}", exc_info=True)
else:
    app.logger.info("Skipping periodic maintenance task thread start (e.g., Werkzeug reloader child process or debug is True but not Werkzeug main process).")


#if __name__ == '__main__':
#    # Agent 유지보수 작업 스레드 시작
#    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
#        maintenance_thread = threading.Thread(target=run_periodic_tasks, daemon=True)
#        maintenance_thread.name = "PeriodicAgentMaintenanceThread"
#        maintenance_thread.start()
#    else:
#        # 개발 모드에서 Werkzeug 리로더가 두 번 실행하는 것을 방지하기 위한 로그
#        app.logger.info("Skipping periodic maintenance task thread start in Werkzeug reloader process.")
#
#    port = int(os.environ.get('FLASK_RUN_PORT', 5111))
#    # debug 모드는 환경 변수 FLASK_DEBUG=true/false 로 제어
#    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')

