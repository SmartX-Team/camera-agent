$(document).ready(function() {
    const API_BASE_URL = 'http://10.32.187.108:5111'; // 백엔드 API 주소
    let currentAgentId = null;

    function formatCameraStatus(cameraStatus) {
        if (!cameraStatus || cameraStatus.length === 0) {
            return 'No cameras';
        }
        return cameraStatus.map(camera => {
            if (camera.device) {
                return `Device: ${camera.device}`;
            }
            return JSON.stringify(camera);
        }).join('<br>');
    }

    function fetchAgents() {
        $.ajax({
            url: `${API_BASE_URL}/webui/get_agent_list`,
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
                            <td>
                                <button onclick="showAgentDetails('${agent.agent_id}')">상세보기</button>
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

    window.showAgentDetails = function(agentId) {
        currentAgentId = agentId;
        $.ajax({
            url: `${API_BASE_URL}/webui/agents/${agentId}`,
            method: 'GET',
            success: function(agent) {
                const detailsContent = `
                    <table>
                        <tr><th>Agent ID</th><td>${agent.agent_id}</td></tr>
                        <tr><th>이름</th><td>${agent.agent_name}</td></tr>
                        <tr><th>IP</th><td>${agent.ip}</td></tr>
                        <tr><th>Port</th><td>${agent.port}</td></tr>
                        <tr><th>Stream URI</th><td>${agent.stream_uri}</td></tr>
                        <tr><th>허용된 IP 범위</th><td>${agent.rtsp_allowed_ip_range || 'N/A'}</td></tr>
                        <tr><th>카메라 상태</th><td>${formatCameraStatus(agent.camera_status)}</td></tr>
                        <tr><th>마지막 업데이트</th><td>${agent.last_update}</td></tr>
                        <tr><th>프레임 전송</th><td>${agent.frame_transmission_enabled ? '활성화' : '비활성화'}</td></tr>
                    </table>
                `;
                $('#agent-details').html(detailsContent);
                $('#agent-controls').show();
                $('#toggleFrameTransmission').text(agent.frame_transmission_enabled ? '프레임 전송 비활성화' : '프레임 전송 활성화');
                $('#video-preview').hide();
            },
            error: function(xhr, status, error) {
                console.error('Agent 상세 정보를 불러오는데 실패했습니다:', error);
            }
        });
    };

    $('#toggleFrameTransmission').click(function() {
        if (currentAgentId) {
            $.ajax({
                url: `${API_BASE_URL}/webui/agents/${currentAgentId}`,
                method: 'GET',
                success: function(agent) {
                    toggleFrameTransmission(currentAgentId, !agent.frame_transmission_enabled);
                },
                error: function(xhr, status, error) {
                    console.error('Agent 정보를 불러오는데 실패했습니다:', error);
                }
            });
        }
    });

    function toggleFrameTransmission(agentId, enable) {
        $.ajax({
            url: `${API_BASE_URL}/api/set_frame_transmission`,  
            method: 'POST',  
            contentType: 'application/json',
            data: JSON.stringify({
                agent_id: agentId,
                frame_transmission_enabled: enable
            }),
            success: function(response) {
                console.log('프레임 전송 설정이 변경되었습니다:', response);
                showAgentDetails(agentId); // 상세 정보 새로고침
            },
            error: function(xhr, status, error) {
                console.error('프레임 전송 설정 변경에 실패했습니다:', error);
                alert('프레임 전송 설정 변경에 실패했습니다. 다시 시도해 주세요.');
            }
        });
    }

    $('#openVideoStream').click(function() {
        if (currentAgentId) {
            $.ajax({
                url: `${API_BASE_URL}/agents/${currentAgentId}`,
                method: 'GET',
                success: function(agent) {
                    openVideoStream(agent.stream_uri);
                },
                error: function(xhr, status, error) {
                    console.error('Agent 정보를 불러오는데 실패했습니다:', error);
                }
            });
        }
    });

    function openVideoStream(streamUri) {
        const videoPlayer = document.getElementById('videoPlayer');
        
        if (Hls.isSupported()) {
            const hls = new Hls();
            hls.loadSource(streamUri);
            hls.attachMedia(videoPlayer);
            hls.on(Hls.Events.MANIFEST_PARSED, function() {
                videoPlayer.play();
            });
        } else if (videoPlayer.canPlayType('application/vnd.apple.mpegurl')) {
            videoPlayer.src = streamUri;
            videoPlayer.addEventListener('loadedmetadata', function() {
                videoPlayer.play();
            });
        }

        $('#video-preview').show();
    }

    setInterval(fetchAgents, 10000); // 10초마다 Agent 목록 업데이트
    fetchAgents(); // 초기 Agent 목록 로드
});