$(document).ready(function() {
    const API_BASE_URL = 'http://your-backend-ip:5111/api'; // 백엔드 API 주소를 실제 IP와 포트로 변경하세요

    // Agent 목록 조회
    function fetchAgents() {
        $.ajax({
            url: `${API_BASE_URL}/agents`,
            method: 'GET',
            success: function(agents) {
                const tableBody = $('#agent-table-body');
                tableBody.empty();
                agents.forEach(function(agent) {
                    tableBody.append(`
                        <tr>
                            <td>${agent.agent_name}</td>
                            <td>${agent.ip}</td>
                            <td>${agent.port}</td>
                            <td>${agent.stream_uri}</td>
                            <td>${agent.rtsp_allowed_ip_range}</td>
                            <td>${agent.camera_status}</td>
                            <td>${agent.last_update}</td>
                            <td>${agent.frame_transmission_enabled ? 'Yes' : 'No'}</td>
                            <td>
                                <button onclick="toggleFrameTransmission(${agent.agent_id}, ${!agent.frame_transmission_enabled})">
                                    ${agent.frame_transmission_enabled ? '비활성화' : '활성화'}
                                </button>
                            </td>
                        </tr>
                    `);
                });
            },
            error: function(xhr, status, error) {
                console.error('Agent 목록을 불러오는데 실패했습니다:', error);
            }
        });
    }

    // 프레임 전송 토글
    window.toggleFrameTransmission = function(agentId, enable) {
        $.ajax({
            url: `${API_BASE_URL}/agents/${agentId}`,
            method: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify({ frame_transmission_enabled: enable }),
            success: function() {
                fetchAgents(); // 목록 새로고침
            },
            error: function(xhr, status, error) {
                console.error('프레임 전송 설정 변경에 실패했습니다:', error);
            }
        });
    };

    // 주기적으로 Agent 목록 업데이트 (예: 10초마다)
    setInterval(fetchAgents, 10000);

    // 초기 Agent 목록 로드
    fetchAgents();
});