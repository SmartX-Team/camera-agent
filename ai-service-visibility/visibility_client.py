# ai_service_config_server/visibility_client.py
import requests
import logging
from config import config

logger = logging.getLogger(__name__)

def get_active_cameras_from_visibility() -> list[dict]:
    visibility_url = config.VISIBILITY_SERVER_URL
    if not visibility_url:
        logger.error("VISIBILITY_SERVER_URL is not configured. Cannot fetch active cameras.")
        return []

    active_cameras_list = []
    try:
        list_url = f"{visibility_url}/webui/get_agent_list"
        logger.debug(f"Fetching agent list from: {list_url}")
        response_list = requests.get(list_url, timeout=10)
        response_list.raise_for_status()
        agents = response_list.json()
        logger.info(f"Retrieved {len(agents)} agents from Visibility Server.")

        for agent_summary in agents:
            agent_id = agent_summary.get('agent_id')
            agent_status = agent_summary.get('status', 'unknown').lower()

            if agent_id and 'active' in agent_status :
                details_url = f"{visibility_url}/webui/agents/{agent_id}"
                logger.debug(f"Fetching details for active agent {agent_id} from: {details_url}")
                response_details = requests.get(details_url, timeout=10)
                
                if response_details.status_code == 200:
                    agent_details = response_details.json()
                    if agent_details and 'cameras' in agent_details and isinstance(agent_details['cameras'], list):
                        for cam in agent_details['cameras']:
                            cam_info_for_service = {
                                "agent_id": agent_details.get('agent_id'),
                                "agent_name": agent_details.get('agent_name'),
                                "agent_ip": agent_details.get('ip'),
                                "agent_api_port": agent_details.get('agent_port'),
                                "camera_id": cam.get('camera_id'),
                                "camera_name": cam.get('camera_name'),
                                "camera_status": cam.get('status'),
                                "camera_type": cam.get('type'),
                                "camera_environment": cam.get('environment'),
                                "stream_protocol": cam.get('stream_protocol'),
                                "stream_details": cam.get('stream_details'),
                                "resolution": cam.get('resolution'),
                                "fps": cam.get('fps')
                            }
                            active_cameras_list.append(cam_info_for_service)
                    else:
                        logger.warning(f"No camera details found for active agent {agent_id} or 'cameras' field missing/invalid.")
                elif response_details.status_code == 404:
                    logger.warning(f"Agent {agent_id} (marked active in list) not found when fetching details (404).")
                else:
                    logger.error(f"Failed to get details for agent {agent_id}. Status: {response_details.status_code}, Body: {response_details.text[:200]}")
            elif agent_id:
                 logger.debug(f"Skipping agent {agent_id} due to status: {agent_status}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Visibility Server ({visibility_url}): {e}", exc_info=True)
    except Exception as e_parse:
        logger.error(f"Error parsing response from Visibility Server: {e_parse}", exc_info=True)
        
    logger.info(f"Found {len(active_cameras_list)} active camera stream(s) from Visibility Server.")
    return active_cameras_list