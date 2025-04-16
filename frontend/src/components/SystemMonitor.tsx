import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Timeline, Alert, Progress, Space, Spin, Tag, Descriptions } from 'antd';
import { CheckCircleOutlined, SyncOutlined, ClockCircleOutlined, FileTextOutlined, ReloadOutlined, DesktopOutlined } from '@ant-design/icons';
import axios from 'axios';

interface SystemInfo {
  os: string;
  version: string;
  architecture: string;
}

interface SystemStats {
  knowledgeBaseCount: number;
  textCount: number;
  systemInfo: SystemInfo;
  lastUpdate: string;
}

const SystemMonitor: React.FC = () => {
  const [stats, setStats] = useState<SystemStats>({
    knowledgeBaseCount: 0,
    textCount: 0,
    systemInfo: {
      os: '',
      version: '',
      architecture: ''
    },
    lastUpdate: new Date().toLocaleString()
  });

  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');

  const fetchSystemStatus = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.get('/system/system-status');
      if (response.data.status === 'success') {
        setStats(response.data.stats);
        setLogs(response.data.logs || []);
      } else {
        setError('获取系统状态失败：' + (response.data.detail || '未知错误'));
      }
    } catch (error) {
      setError('获取系统状态失败：' + (error instanceof Error ? error.message : '网络错误'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSystemStatus();
    const interval = setInterval(fetchSystemStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <Card 
        title="系统监控" 
        extra={
          <Space>
            <span>上次更新：{stats.lastUpdate}</span>
            <ReloadOutlined onClick={fetchSystemStatus} style={{ cursor: 'pointer' }}/>
          </Space>
        }
      >
        <Spin spinning={loading}>
          {error && (
            <Alert
              message="错误"
              description={error}
              type="error"
              showIcon
              style={{ marginBottom: '16px' }}
            />
          )}

          <Row gutter={16}>
            <Col span={12}>
              <Card>
                <Statistic
                  title="知识库数量"
                  value={stats.knowledgeBaseCount}
                  prefix={<CheckCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card>
                <Statistic
                  title="文本数据量"
                  value={stats.textCount}
                  prefix={<FileTextOutlined />}
                />
              </Card>
            </Col>
          </Row>

          <Card style={{ marginTop: '20px' }}>
            <Descriptions title="系统信息" bordered>
              <Descriptions.Item label="操作系统" span={3}>
                <Tag color="blue" icon={<DesktopOutlined />}>
                  {stats.systemInfo.os} {stats.systemInfo.version} ({stats.systemInfo.architecture})
                </Tag>
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card style={{ marginTop: '20px' }}>
            <Alert
              message="系统日志"
              description={`最后更新时间: ${stats.lastUpdate}`}
              type="info"
              showIcon
            />
            {logs.length > 0 ? (
              <Timeline style={{ marginTop: '20px' }}>
                {logs.map((log, index) => (
                  <Timeline.Item key={index} dot={<ClockCircleOutlined />}>
                    {log}
                  </Timeline.Item>
                ))}
              </Timeline>
            ) : (
              <div style={{ textAlign: 'center', margin: '20px 0' }}>
                暂无日志记录
              </div>
            )}
          </Card>
        </Spin>
      </Card>
    </div>
  );
};

export default SystemMonitor;