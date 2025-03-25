import React, { useState, useEffect } from 'react';
import { Card, Input, Button, message, Spin, Typography, Space, Select } from 'antd';
import { FileTextOutlined, DownloadOutlined, SearchOutlined } from '@ant-design/icons';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

const { Search } = Input;
const { Title } = Typography;
const { Option } = Select;

const ReportGenerator: React.FC = () => {
  const [query, setQuery] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [report, setReport] = useState<string>('');
  const [databases, setDatabases] = useState<string[]>([]);
  const [selectedDb, setSelectedDb] = useState('default');

  const fetchDatabases = async () => {
    try {
      const response = await axios.get('http://localhost:8000/databases');
      if (response.data.status === 'success') {
        setDatabases(response.data.data);
        if (!response.data.data.includes('default')) {
          setDatabases(['default', ...response.data.data]);
        }
      }
    } catch (error) {
      message.error('获取数据库列表失败');
    }
  };

  useEffect(() => {
    fetchDatabases();
  }, []);

  const handleGenerate = async () => {
    if (!query.trim()) {
      message.warning('请输入报告主题');
      return;
    }

    setLoading(true);
    try {
      message.loading({ content: '正在生成报告...', key: 'report' });
      const response = await axios.post('http://localhost:8000/generate-report', {
        query: query,
        k: 5,
        db_name: selectedDb  // 添加 db_name 参数
      }, {
        timeout: 60000
      });

      if (response.data.status === 'success') {
        setReport(response.data.data);
        message.success({ content: '报告生成成功', key: 'report' });
      } else {
        message.error({ content: '报告生成失败: ' + (response.data.detail || '未知错误'), key: 'report' });
      }
    } catch (error) {
      if (axios.isAxiosError(error)) {
        if (error.code === 'ECONNABORTED') {
          message.error({ content: '请求超时，报告生成可能需要较长时间，请稍后重试', key: 'report' });
        } else if (error.response) {
          message.error({ content: '报告生成失败：' + (error.response.data.detail || error.message), key: 'report' });
        } else if (error.request) {
          message.error({ content: '无法连接到服务器，请检查网络连接或后端服务是否启动', key: 'report' });
        } else {
          message.error({ content: '请求出错：' + error.message, key: 'report' });
        }
      } else {
        message.error({ content: '报告生成失败：' + (error instanceof Error ? error.message : '未知错误'), key: 'report' });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    const blob = new Blob([report], { type: 'text/markdown' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `防汛报告_${query}_${new Date().toLocaleDateString()}.md`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    message.success('报告已导出');
  };

  return (
    <div>
      <Card
        title="报告生成"
        extra={<FileTextOutlined />}
      >
        <div style={{ marginBottom: 16 }}>
          <Select
            value={selectedDb}
            onChange={(value) => setSelectedDb(value)}
            style={{ width: 200, marginBottom: 8 }}
          >
            {databases.map(db => (
              <Option key={db} value={db}>{db}</Option>
            ))}
          </Select>
        </div>
        <Search
          placeholder="输入报告主题（如：洞庭湖洪水情况）"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onSearch={handleGenerate}
          enterButton={<><SearchOutlined /> 生成报告</>}
          loading={loading}
          style={{ marginBottom: '16px' }}
        />

        {loading && (
          <div style={{ textAlign: 'center', margin: '20px 0' }}>
            <Spin tip="正在生成报告..." />
          </div>
        )}

        {report && (
          <div style={{ marginTop: '20px' }}>
            <Space style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between' }}>
              <Title level={4}>报告预览</Title>
              <Button
                icon={<DownloadOutlined />}
                type="primary"
                onClick={handleExport}
              >
                导出报告
              </Button>
            </Space>
            <div style={{
              padding: '16px',
              border: '1px solid #f0f0f0',
              borderRadius: '4px',
              backgroundColor: '#fff',
              maxHeight: '500px',
              overflow: 'auto',
              lineHeight: '1.6'
            }}>
              <ReactMarkdown
                components={{
                  h1: ({ node, ...props }) => <h1 style={{ fontSize: '24px', margin: '16px 0' }} {...props} />,
                  h2: ({ node, ...props }) => <h2 style={{ fontSize: '20px', margin: '12px 0' }} {...props} />,
                  p: ({ node, ...props }) => <p style={{ margin: '8px 0' }} {...props} />,
                  ul: ({ node, ...props }) => <ul style={{ margin: '8px 0', paddingLeft: '20px' }} {...props} />,
                  li: ({ node, ...props }) => <li style={{ margin: '4px 0' }} {...props} />
                }}
              >
                {report}
              </ReactMarkdown>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};

export default ReportGenerator;