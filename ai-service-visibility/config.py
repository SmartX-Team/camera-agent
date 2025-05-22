# ai_service_config_server/config.py
import os
from dotenv import load_dotenv

# .env 파일이 있다면 로드 (로컬 개발 시 유용)
load_dotenv()

class Config:
    # PostgreSQL 설정
    POSTGRES_HOST = os.environ.get('POSTGRES_HOST', '10.79.1.13')
    POSTGRES_PORT = int(os.environ.get('POSTGRES_PORT', 5432))
    POSTGRES_USER = os.environ.get('POSTGRES_USER', 'myuser')
    POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'netAi007!')
    POSTGRES_DB = os.environ.get('POSTGRES_DB', 'uwb')
    UWB_TABLE_NAME = os.environ.get('UWB_TABLE_NAME', 'uwb_raw')

    # Redis 설정
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost') # 실제 Redis 호스트로 변경 필요
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB_SERVICE_CONFIG = int(os.environ.get('REDIS_DB_SERVICE_CONFIG', 0)) # 서비스 설정용 DB 번호
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD') # Redis 비밀번호 (없으면 None)
    # 저장될 서비스 설정 키의 접두사 (Falcon Wrapper가 이 키를 읽음)
    # 예: "service_config:my_yolo_service"
    REDIS_SERVICE_CONFIG_KEY_PREFIX = os.environ.get('REDIS_SERVICE_CONFIG_KEY_PREFIX', 'service_configs')


    # Visibility Server API 설정
    VISIBILITY_SERVER_URL = os.environ.get('VISIBILITY_SERVER_URL', 'http://localhost:5111') # 실제 Visibility 서버 주소

    # 로깅 설정
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()

    # 이 서버 자체의 포트
    SERVICE_PORT = int(os.environ.get('AI_CONFIG_SERVICE_PORT', 5005)) # 예시 포트

    # 주기적 정리 작업 설정 (여기에 추가)
    CLEANUP_INTERVAL_MINUTES = int(os.environ.get('CLEANUP_INTERVAL_MINUTES', 1)) # 분 단위, 기본값 60분

    # 제외할 카메라 상태 목록 (동작하지 않거나 문제가 있는 상태들)
    NON_OPERATIONAL_CAMERA_STATUSES = {
        'unknown_timeout',
        'offline', # 예시: 필요에 따라 추가
        'error',   # 예시: 필요에 따라 추가
        # 필요한 상태들을 여기에 추가/제거
    }

# 전역 설정 객체
config = Config()