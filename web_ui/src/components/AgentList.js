import React, { useState, useEffect } from 'react';
import { Table, Card, CardHeader, CardContent, Badge } from '../ui/';
import { Camera, Wifi, Server } from 'lucide-react';

const AgentList = () => {
  const [agents, setAgents] = useState([]);

  useEffect(() => {
    // 실제 구현에서는 API를 호출하여 데이터를 가져옵니다.
    const fetchAgents = async () => {
      // const response = await fetch('/api/agents');
      // const data = await response.json();
      // setAgents(data);
      
      // 임시 데이터
      setAgents([
        {
          agent_id: '1',
          agent_name: 'Camera 1',
          ip: '192.168.1.100',
          port: 8080,
          stream_uri: 'rtsp://192.168.1.100:8554/stream1',
          rtsp_allowed_ip_range: '192.168.1.0/24',
          camera_status: ['active'],
          last_update: '2024-10-02T12:00:00Z',
          frame_transmission_enabled: true
        },
        // 더 많은 에이전트 데이터...
      ]);
    };

    fetchAgents();
  }, []);

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Camera Agent List</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.map((agent) => (
          <Card key={agent.agent_id}>
            <CardHeader>
              <div className="flex justify-between items-center">
                <h2 className="text-xl font-semibold">{agent.agent_name}</h2>
                <Badge variant={agent.frame_transmission_enabled ? "success" : "secondary"}>
                  {agent.frame_transmission_enabled ? "Enabled" : "Disabled"}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <p><Camera className="inline mr-2" /> Stream URI: {agent.stream_uri}</p>
                <p><Wifi className="inline mr-2" /> IP: {agent.ip}:{agent.port}</p>
                <p><Server className="inline mr-2" /> Allowed IP Range: {agent.rtsp_allowed_ip_range}</p>
                <p>Last Update: {new Date(agent.last_update).toLocaleString()}</p>
                <div>
                  Status: 
                  {agent.camera_status.map((status, index) => (
                    <Badge key={index} className="ml-2" variant="outline">{status}</Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default AgentList;