import React, { useState, useEffect } from 'react';
import { Card, Input, Button, message, List, Spin, Select } from 'antd';
import axios from 'axios';

const { TextArea } = Input;
const { Option } = Select;

const LinkExtractor: React.FC = () => {
  const [links, setLinks] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
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

  const handleExtract = async () => {
    if (!links.trim()) {
      message.warning('请输入需要提取的链接');
      return;
    }

    const linkList = links
      .split(/[\n\s]+/)
      .map(link => link.trim())
      .filter(link => link && (link.startsWith('http://') || link.startsWith('https://')));

    if (linkList.length === 0) {
      message.warning('未找到有效的链接');
      return;
    }

    setLoading(true);
    setResults([]);

    try {
      message.loading({ content: '正在提取链接内容...', key: 'extract' });
      const response = await axios.post('http://localhost:8000/extract', {
        urls: linkList,
        db_name: selectedDb
      }, {
        timeout: 120000
      });

      if (response.data.status === 'success') {
        setResults(response.data.data);
        message.success({ content: '链接内容提取成功', key: 'extract' });

        message.loading({ content: '正在构建向量索引...', key: 'index' });
        try {
          await axios.post('http://localhost:8000/build-index', { db_name: selectedDb });
          message.success({ content: '向量索引构建完成', key: 'index' });
        } catch (indexError) {
          message.error({ content: '向量索引构建失败: ' + (indexError as Error).message, key: 'index' });
        }
      } else {
        message.error({ content: '处理失败：' + (response.data.detail || '未知错误'), key: 'extract' });
      }
    } catch (error) {
      if (axios.isAxiosError(error)) {
        if (error.code === 'ECONNABORTED') {
          message.error({ content: '请求超时，请检查网络连接或稍后重试', key: 'extract' });
        } else if (error.response) {
          message.error({ content: '处理失败：' + (error.response.data.detail || error.message), key: 'extract' });
        } else if (error.request) {
          message.error({ content: '无法连接到服务器，请检查网络连接或后端服务是否启动', key: 'extract' });
        } else {
          message.error({ content: '请求出错：' + error.message, key: 'extract' });
        }
      } else {
        message.error({ content: '处理失败：' + (error as Error).message, key: 'extract' });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="链接提取">
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
      <TextArea
        rows={4}
        value={links}
        onChange={(e) => setLinks(e.target.value)}
        placeholder="请输入需要提取的链接，每行一个"
        style={{ marginBottom: 16 }}
      />
      <Button type="primary" onClick={handleExtract} loading={loading}>
        开始提取
      </Button>
      {results.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3>提取结果</h3>
          <Spin spinning={loading}>
            <List
              dataSource={results}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta
                    title={<a href={item.url}>{item.title || item.url}</a>}
                    description={item.text || '无内容'}
                  />
                </List.Item>
              )}
            />
          </Spin>
        </div>
      )}
    </Card>
  );
};

export default LinkExtractor;