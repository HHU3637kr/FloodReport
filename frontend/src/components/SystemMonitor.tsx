import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Timeline, Alert, Progress, Space, Spin } from 'antd';
import { CheckCircleOutlined, SyncOutlined, ClockCircleOutlined, FileTextOutlined, ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';

interface SystemStats {
  processedLinks: number;
  totalLinks: number;
  vectorCount: number;
  reportCount: number;
  systemLoad: number;
  isIndexing: boolean;
  lastUpdate: string;
}

const SystemMonitor: React.FC = () => {
  const [stats, setStats] = useState<SystemStats>({
    processedLinks: 0,
    totalLinks: 0,
    vectorCount: 0,
    reportCount: 0,
    systemLoad: 0,
    isIndexing: false,
    lastUpdate: new Date().toLocaleString()
  });

  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');

  const fetchSystemStatus = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.get('http://localhost:8000/system-status');
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

  const progressPercent = Math.round((stats.processedLinks / Math.max(stats.totalLinks, 1)) * 100);

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
            <Col span={6}>
              <Card>
                <Statistic
                  title="已处理链接"
                  value={stats.processedLinks}
                  suffix={`/${stats.totalLinks}`}
                  prefix={<CheckCircleOutlined />}
                />
                <Progress
                  percent={progressPercent}
                  size="small"
                  status={progressPercent === 100 ? 'success' : 'active'}
                  style={{ marginTop: '8px' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="向量数据量"
                  value={stats.vectorCount}
                  prefix={<SyncOutlined spin={stats.isIndexing} />}
                  suffix={stats.isIndexing ? '更新中' : '已同步'}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="生成报告数"
                  value={stats.reportCount}
                  prefix={<FileTextOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="系统负载"
                  value={stats.systemLoad}
                  suffix="%"
                  valueStyle={{ color: stats.systemLoad > 80 ? '#cf1322' : (stats.systemLoad > 50 ? '#faad14' : '#3f8600') }}
                />
                <Progress 
                  percent={stats.systemLoad} 
                  size="small"
                  status={stats.systemLoad > 80 ? 'exception' : (stats.systemLoad > 50 ? 'normal' : 'success')}
                  style={{ marginTop: '8px' }}
                />
              </Card>
            </Col>
          </Row>

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