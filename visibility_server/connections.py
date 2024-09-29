import os
from tinydb import TinyDB
import logging

# 필요한 경우 다른 패키지 임포트 (e.g., kafka-python)

# 환경 변수 또는 설정 값 로드
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.getenv('DATABASE_FILE', os.path.join(BASE_DIR, 'agents.json'))

KAFKA_BROKER_URL = os.getenv('KAFKA_BROKER_URL', 'localhost:9092')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"Database file path: {DATABASE_FILE}")

try:
    db = TinyDB(DATABASE_FILE)
    db.truncate()
    AgentTable = db.table('agents')
    logger.info("Database initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")