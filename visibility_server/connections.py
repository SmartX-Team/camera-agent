import os
from tinydb import TinyDB
# 필요한 경우 다른 패키지 임포트 (e.g., kafka-python)

# 환경 변수 또는 설정 값 로드
DATABASE_FILE = os.getenv('DATABASE_FILE', 'agents.json')
KAFKA_BROKER_URL = os.getenv('KAFKA_BROKER_URL', 'localhost:9092')

# 데이터베이스 초기화
db = TinyDB(DATABASE_FILE)
AgentTable = db.table('agents')