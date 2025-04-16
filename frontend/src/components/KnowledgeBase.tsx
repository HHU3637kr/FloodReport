import React, { useState, useEffect } from 'react';
import { 
  Button, 
  Input, 
  Card, 
  message, 
  Modal, 
  Form, 
  Typography, 
  Tooltip,
  Dropdown,
  Empty,
  Space,
  Spin,
  Badge,
  Divider
} from 'antd';
import { 
  PlusOutlined, 
  EllipsisOutlined, 
  EditOutlined,
  DeleteOutlined,
  SettingOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  SearchOutlined,
  DatabaseOutlined,
  ArrowRightOutlined
} from '@ant-design/icons';
import KnowledgeBaseDetail from './KnowledgeBaseDetail';
import './KnowledgeBase.css';

const { Title, Paragraph, Text } = Typography;

interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  createdAt: string;
}

const KnowledgeBase: React.FC = () => {
  const [databases, setDatabases] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCreateModalVisible, setIsCreateModalVisible] = useState(false);
  const [isEditModalVisible, setIsEditModalVisible] = useState(false);
  const [currentDb, setCurrentDb] = useState<KnowledgeBase | null>(null);
  const [selectedDb, setSelectedDb] = useState<KnowledgeBase | null>(null);
  const [detailLoadError, setDetailLoadError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [form] = Form.useForm();
  const [createForm] = Form.useForm();

  useEffect(() => {
    fetchDatabases();
  }, []);

  const fetchDatabases = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/knowledge-base');
      if (response.ok) {
        const data = await response.json();
        setDatabases(data);
      } else {
        message.error('获取知识库列表失败');
      }
    } catch (error) {
      message.error('获取知识库列表失败，请检查网络连接');
    } finally {
      setLoading(false);
    }
  };

  const showCreateModal = () => {
    createForm.resetFields();
    setIsCreateModalVisible(true);
  };

  const handleCreateDatabase = async () => {
    try {
      const values = await createForm.validateFields();
      setLoading(true);
      
      const response = await fetch('/api/knowledge-base', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: values.name,
          description: values.description,
        }),
      });

      if (response.ok) {
        message.success('知识库创建成功！');
        setIsCreateModalVisible(false);
        fetchDatabases();
      } else {
        const error = await response.json();
        message.error(error.detail || '创建失败，请重试');
      }
    } catch (error) {
      message.error('创建失败，请检查输入');
    } finally {
      setLoading(false);
    }
  };

  const showEditModal = (db: KnowledgeBase) => {
    setCurrentDb(db);
    form.setFieldsValue({
      name: db.name,
      description: db.description,
    });
    setIsEditModalVisible(true);
  };

  const handleUpdate = async () => {
    try {
      const values = await form.validateFields();
      const response = await fetch(`/api/knowledge-base/${currentDb?.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(values),
      });

      if (response.ok) {
        message.success('更新成功');
        setIsEditModalVisible(false);
        fetchDatabases();
      } else {
        const error = await response.json();
        message.error(error.detail || '更新失败');
      }
    } catch (error) {
      message.error('更新失败，请重试');
    }
  };

  const handleDelete = (db: KnowledgeBase) => {
    Modal.confirm({
      title: '确认删除',
      content: (
        <div>
          <p>确定要删除知识库 <Text strong>{db.name}</Text> 吗？</p>
          <p style={{ color: '#ff4d4f' }}>此操作不可恢复，所有相关数据将被永久删除。</p>
        </div>
      ),
      okText: '确认删除',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          const response = await fetch(`/api/knowledge-base/${db.id}`, {
            method: 'DELETE',
          });

          if (response.ok) {
            message.success('删除成功');
            fetchDatabases();
            if (selectedDb?.id === db.id) {
              setSelectedDb(null);
            }
          } else {
            const error = await response.json();
            message.error(error.detail || '删除失败');
          }
        } catch (error) {
          message.error('删除失败，请重试');
        }
      },
    });
  };

  const handleManageDb = (db: KnowledgeBase) => {
    try {
      setDetailLoadError(null);
      setSelectedDb(db);
    } catch (error) {
      console.error('切换到知识库详情页失败:', error);
      message.error('打开知识库详情失败，请重试');
    }
  };

  const filteredDatabases = databases.filter(db => 
    db.name.toLowerCase().includes(searchText.toLowerCase()) || 
    db.description.toLowerCase().includes(searchText.toLowerCase())
  );

  if (selectedDb) {
    if (detailLoadError) {
      return (
        <div className="knowledge-base-container">
          <Card title="错误" className="error-card">
            <div style={{ textAlign: 'center', padding: '30px 0' }}>
              <Title level={3}>加载知识库详情时出错</Title>
              <Paragraph>{detailLoadError}</Paragraph>
              <Button type="primary" onClick={() => setSelectedDb(null)}>
                返回知识库列表
              </Button>
            </div>
          </Card>
        </div>
      );
    }
    
    return (
      <KnowledgeBaseDetail
        knowledgeBase={selectedDb}
        onBack={() => setSelectedDb(null)}
        onError={(error) => setDetailLoadError(error)}
      />
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>知识库</Title>
        <Space>
          <Input
            placeholder="搜索知识库"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            style={{ width: 240 }}
            allowClear
          />
          <Button 
            type="primary" 
            icon={<PlusOutlined />} 
            onClick={showCreateModal}
          >
            创建知识库
          </Button>
        </Space>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Spin size="large" />
          <Paragraph style={{ marginTop: 16 }}>正在加载知识库...</Paragraph>
        </div>
      ) : filteredDatabases.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            searchText ? '没有找到匹配的知识库' : '暂无知识库，点击"创建知识库"按钮开始创建'
          }
        >
          {!searchText && (
            <Button type="primary" icon={<PlusOutlined />} onClick={showCreateModal}>
              创建知识库
            </Button>
          )}
        </Empty>
      ) : (
        <div className="knowledge-base-grid">
          {filteredDatabases.map(db => (
            <Card
              key={db.id}
              className="kb-card-new"
              hoverable
              actions={[
                <Button 
                  type="primary" 
                  key="manage" 
                  block 
                  onClick={() => handleManageDb(db)}
                >
                  管理
                </Button>
              ]}
              extra={
                <Dropdown
                  menu={{
                    items: [
                      {
                        key: 'edit',
                        icon: <EditOutlined />,
                        label: '编辑',
                        onClick: () => showEditModal(db)
                      },
                      {
                        key: 'delete',
                        icon: <DeleteOutlined />,
                        label: '删除',
                        danger: true,
                        onClick: () => handleDelete(db)
                      }
                    ]
                  }}
                  placement="bottomRight"
                  trigger={['click']}
                >
                  <Button type="text" icon={<EllipsisOutlined />} />
                </Dropdown>
              }
            >
              <div onClick={() => handleManageDb(db)} style={{ cursor: 'pointer' }}>
                <Card.Meta 
                  title={db.name} 
                  description={db.description || '无描述'}
                />
                <Divider style={{ margin: '12px 0' }} />
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Space>
                    <Badge status="processing" color="#52c41a" />
                    <Text>状态: 正常</Text>
                  </Space>
                  <Space>
                    <ClockCircleOutlined /> 
                    <Text type="secondary">创建于: {new Date(db.createdAt).toLocaleString()}</Text>
                  </Space>
                  <Space>
                    <FileTextOutlined />
                    <Text type="secondary">文档数量: 0</Text>
                  </Space>
                </Space>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* 创建知识库模态框 */}
      <Modal
        title="创建新知识库"
        open={isCreateModalVisible}
        onOk={handleCreateDatabase}
        onCancel={() => setIsCreateModalVisible(false)}
        okText="创建"
        cancelText="取消"
        okButtonProps={{ loading }}
      >
        <Form
          form={createForm}
          layout="vertical"
        >
          <Form.Item
            name="name"
            label="知识库名称"
            rules={[{ required: true, message: '请输入知识库名称' }]}
          >
            <Input placeholder="请输入知识库名称" prefix={<DatabaseOutlined />} />
          </Form.Item>
          <Form.Item
            name="description"
            label="知识库描述"
          >
            <Input.TextArea
              placeholder="请输入知识库描述（选填）"
              rows={4}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑知识库模态框 */}
      <Modal
        title="编辑知识库"
        open={isEditModalVisible}
        onOk={handleUpdate}
        onCancel={() => setIsEditModalVisible(false)}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="知识库名称"
            rules={[{ required: true, message: '请输入知识库名称' }]}
          >
            <Input placeholder="请输入知识库名称" prefix={<DatabaseOutlined />} />
          </Form.Item>
          <Form.Item
            name="description"
            label="知识库描述"
          >
            <Input.TextArea
              placeholder="请输入知识库描述（选填）"
              rows={4}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default KnowledgeBase; 