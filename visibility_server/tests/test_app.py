import pytest
from app import app

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_agent_update_status(client):
    response = client.post('/agent/update_status', json={
        'agent_id': 'test_agent',
        'camera_status': [{'camera_id': 0, 'connected': True}],
        'frame_transmission_enabled': False
    })
    assert response.status_code == 200
    assert response.get_json()['message'] == 'Status updated successfully'

def test_agent_get_config(client):
    # 사전에 에이전트 상태를 업데이트하여 데이터베이스에 에이전트를 추가합니다.
    client.post('/agent/update_status', json={
        'agent_id': 'test_agent',
        'camera_status': [{'camera_id': 0, 'connected': True}],
        'frame_transmission_enabled': False
    })

    response = client.get('/agent/get_config', query_string={'agent_id': 'test_agent'})
    assert response.status_code == 200
    assert response.get_json()['frame_transmission_enabled'] == False

def test_get_camera_status(client):
    response = client.get('/api/get_camera_status')
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)

def test_set_frame_transmission(client):
    # 사전에 에이전트 상태를 업데이트하여 데이터베이스에 에이전트를 추가합니다.
    client.post('/agent/update_status', json={
        'agent_id': 'test_agent',
        'camera_status': [{'camera_id': 0, 'connected': True}],
        'frame_transmission_enabled': False
    })

    response = client.post('/api/set_frame_transmission', json={
        'agent_id': 'test_agent',
        'frame_transmission_enabled': True
    })
    assert response.status_code == 200
    assert response.get_json()['message'] == 'Frame transmission setting updated'

    # 설정이 변경되었는지 확인합니다.
    response = client.get('/agent/get_config', query_string={'agent_id': 'test_agent'})
    assert response.status_code == 200
    assert response.get_json()['frame_transmission_enabled'] == True
