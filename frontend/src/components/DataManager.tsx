import React, { useState, useEffect } from 'react';
import { Card, Input, List, message, Spin, Row, Col, Statistic, Space, Tag } from 'antd';
import { DatabaseOutlined, SearchOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Search } = Input;

interface SearchResult {
  category: string;
  event: {
    time?: string;
    location?: string;
    description?: string;
    [key: string]: any;
  };
  distance: number;
}

interface DataStats {
  totalDocuments: number;
  categories: string[];
  regions: string[];
}

const DataManager: React.FC = () => {
  const [query, setQuery] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [searchLoading, setSearchLoading] = useState<boolean>(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [stats, setStats] = useState<DataStats>({
    totalDocuments: 0,
    categories: [],
    regions: []
  });

  useEffect(() => {
    const fetchStats = async () => {
      setLoading(true);
      try {
        const response = await axios.get('http://localhost:8000/data-stats');
        if (response.data.status === 'success') {
          setStats(response.data.data);
        } else {
          message.error('获取数据统计信息失败');
        }
      } catch (error) {
        message.error('获取数据统计失败：' + (error instanceof Error ? error.message : '未知错误'));
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  const handleSearch = async () => {
    if (!query.trim()) {
      message.warning('请输入搜索关键词');
      return;
    }

    setSearchLoading(true);
    try {
      const response = await axios.post('http://localhost:8000/search', {
        query: query,
        k: 5
      });

      if (response.data.status === 'success') {
        setResults(response.data.data || []);
        if (response.data.data?.length === 0) {
          message.info('未找到匹配的结果');
        } else {
          message.success('搜索完成');
        }
      } else {
        message.error('搜索失败: ' + (response.data.detail || '未知错误'));
        setResults([]);
      }
    } catch (error) {
      message.error('搜索失败：' + (error instanceof Error ? error.message : '未知错误'));
      setResults([]);
    } finally {
      setSearchLoading(false);
    }
  };

  return (
    <div>
      <Card title="数据管理" extra={<DatabaseOutlined />}>
        <Spin spinning={loading}>
          <Row gutter={16} style={{ marginBottom: '16px' }}>
            <Col span={8}>
              <Card size="small">
                <Statistic title="总文档数" value={stats.totalDocuments} />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small">
                <Statistic title="地区覆盖" value={stats.regions.length} suffix="个地区" />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small">
                <Statistic title="分类统计" value={stats.categories.length} suffix="个分类" />
              </Card>
            </Col>
          </Row>
        </Spin>

        <Search
          placeholder="输入关键词搜索相似文本"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onSearch={handleSearch}
          enterButton={<><SearchOutlined /> 搜索</>}
          loading={searchLoading}
          style={{ marginBottom: '16px' }}
        />

        {searchLoading && (
          <div style={{ textAlign: 'center', margin: '20px 0' }}>
            <Spin tip="正在搜索..." />
          </div>
        )}

        {results.length > 0 && (
          <List
            style={{ marginTop: '20px' }}
            header={<div>搜索结果</div>}
            bordered
            dataSource={results}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta
                  title={
                    <Space>
                      <span>相似度：{(item.distance * 100).toFixed(2)}%</span>
                      <Tag color="blue">{item.category}</Tag>
                      {item.event.location && <Tag color="green">{item.event.location}</Tag>}
                    </Space>
                  }
                  description={
                    <div style={{ whiteSpace: 'pre-wrap' }}>
                      {item.event.time && <p>时间：{item.event.time}</p>}
                      {item.event.description && <p>描述：{item.event.description}</p>}
                      {Object.entries(item.event)
                        .filter(([key]) => !['time', 'location', 'description'].includes(key))
                        .map(([key, value]) => (
                          <p key={key}>{key}：{value}</p>
                        ))}
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
};

export default DataManager;