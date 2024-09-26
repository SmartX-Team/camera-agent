from tinydb import Query
from connections import AgentTable

class AgentModel:
    @staticmethod
    def upsert_agent(agent_data):
        AgentTable.upsert(agent_data, Query().agent_id == agent_data['agent_id'])

    @staticmethod
    def get_agent(agent_id):
        return AgentTable.get(Query().agent_id == agent_id)

    @staticmethod
    def update_agent(agent_id, data):
        AgentTable.update(data, Query().agent_id == agent_id)

    @staticmethod
    def get_all_agents():
        return AgentTable.all()
