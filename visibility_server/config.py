import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

DATABASE_FILE = os.getenv('DATABASE_FILE', 'agents.json')
SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
