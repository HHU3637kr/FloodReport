// src/components/DatabaseManager.tsx
import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Input, message, Popconfirm } from 'antd';
import axios from 'axios';

const DatabaseManager: React.FC = () => {
  const [databases, setDatabases] = useState<string[]>([]);
  const [newDbName, setNewDbName] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchDatabases = async () => {
    setLoading(true);
    try {
      const response = await axios.get('http://localhost:8000/databases');
      if (response.data.status === 'success') {
        setDatabases(response.data.data);
      } else {
        message.error('获取数据库列表失败');
      }
    } catch (error) {
      message.error('获取数据库列表失败: ' + (error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const createDatabase = async () => {
    if (!newDbName || !newDbName.match(/^[a-zA-Z0-9]+$/)) {
      message.warning('请输入有效的数据库名称（仅限字母和数字）');
      return;
    }

    try {
      const response = await axios.post('http://localhost:8000/databases', { db_name: newDbName });
      if (response.data.status === 'success') {
        message.success('数据库创建成功');
        setNewDbName('');
        fetchDatabases();
      } else {
        message.error('创建数据库失败');
      }
    } catch (error) {
      message.error('创建数据库失败: ' + (error as Error).message);
    }
  };

  const deleteDatabase = async (dbName: string) => {
    try {
      const response = await axios.delete(`http://localhost:8000/databases/${dbName}`);
      if (response.data.status === 'success') {
        message.success('数据库删除成功');
        fetchDatabases();
      } else {
        message.error('删除数据库失败');
      }
    } catch (error) {
      message.error('删除数据库失败: ' + (error as Error).message);
    }
  };

  useEffect(() => {
    fetchDatabases();
  }, []);

  const columns = [
    {
      title: '数据库名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: { name: string }) => (
        <Popconfirm
          title="确定删除此数据库？"
          onConfirm={() => deleteDatabase(record.name)}
          okText="确定"
          cancelText="取消"
        >
          <Button type="link" danger>删除</Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <Card title="数据库管理">
      <div style={{ marginBottom: 16 }}>
        <Input
          placeholder="输入新数据库名称"
          value={newDbName}
          onChange={(e) => setNewDbName(e.target.value)}
          style={{ width: 200, marginRight: 8 }}
        />
        <Button type="primary" onClick={createDatabase}>
          创建数据库
        </Button>
      </div>
      <Table
        columns={columns}
        dataSource={databases.map((db) => ({ key: db, name: db }))}
        loading={loading}
        pagination={false}
      />
    </Card>
  );
};

export default DatabaseManager;