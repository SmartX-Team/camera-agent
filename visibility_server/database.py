import os
import uuid
from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware

class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        # 환경 변수 또는 설정 값 로드
        DATABASE_FILE = os.getenv('DATABASE_FILE', 'agents.json')
        self.db = TinyDB(DATABASE_FILE, storage=CachingMiddleware(JSONStorage))
        self.agent_table = self.db.table('agents')

    def add_agent(self, agent_name, ip, port, camera_data):
        # UUID 함수로 자동 ID 생성
        agent_id = str(uuid.uuid4())
        self.agent_table.insert({
            'agent_id': agent_id,
            'agent_name': agent_name,
            'ip': ip,
            'port': port,
            'camera_data': camera_data
        })
        return agent_id

    def get_agent_by_id(self, agent_id):
        Agent = Query()
        return self.agent_table.search(Agent.agent_id == agent_id)

    def update_agent_cameras(self, agent_id, new_camera_data):
        Agent = Query()
        self.agent_table.update({'camera_data': new_camera_data}, Agent.agent_id == agent_id)

    def update_agent(self, agent_id, agent_data):
        Agent = Query()
        self.agent_table.update(agent_data, Agent.agent_id == agent_id)

    def delete_agent(self, agent_id):
        Agent = Query()
        self.agent_table.remove(Agent.agent_id == agent_id)

    def get_all_agents(self):
        return self.agent_table.all()

    def get_agent_by_name(self, agent_name):
        Agent = Query()
        return self.agent_table.search(Agent.agent_name == agent_name)
