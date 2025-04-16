import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Table, 
  Button, 
  Popconfirm, 
  message, 
  Modal, 
  Form, 
  Input, 
  Space, 
  Typography, 
  Tooltip, 
  Tag, 
  Checkbox, 
  Divider,
  List,
  Row,
  Col,
  Drawer 
} from 'antd';
import { 
  DatabaseOutlined, 
  DeleteOutlined, 
  EditOutlined, 
  PlusOutlined, 
  ExclamationCircleOutlined, 
  CheckCircleOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  AppstoreOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  StopOutlined,
  FileMarkdownOutlined
} from '@ant-design/icons';
import TextArea from 'antd/es/input/TextArea';
import ReactMarkdown from 'react-markdown';

const { Title, Text } = Typography;

interface Index {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at?: string;
  vector_count: number;
  file_size: number;
  text_files: string[];
  is_active?: boolean;
}

interface TextFile {
  filename: string;
  size: number;
  created_at: string;
  description?: string;
}

interface IndexManagerProps {
  knowledgeBaseId: string;
  buildIndex: (indexId?: string) => Promise<void>;
}

const IndexManager: React.FC<IndexManagerProps> = ({ knowledgeBaseId, buildIndex }) => {
  const [indices, setIndices] = useState<Index[]>([]);
  const [textFiles, setTextFiles] = useState<TextFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [updateModalVisible, setUpdateModalVisible] = useState(false);
  const [selectFilesDrawerVisible, setSelectFilesDrawerVisible] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<Index | null>(null);
  const [form] = Form.useForm();
  const [updateForm] = Form.useForm();
  const [searchText, setSearchText] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  
  // 添加报告生成相关状态
  const [reportModalVisible, setReportModalVisible] = useState(false);
  const [reportForm] = Form.useForm();
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportResult, setReportResult] = useState<string | null>(null);

  // 获取索引列表
  const fetchIndices = async () => {
    setLoading(true);
    try {
      // 首先获取活跃索引信息
      let activeIndexId = null;
      try {
        const activeResponse = await fetch(`/api/knowledge-base/${knowledgeBaseId}/active-index-info`);
        if (activeResponse.ok) {
          const activeData = await activeResponse.json();
          if (activeData.status === 'success' && activeData.data) {
            activeIndexId = activeData.data.original_index_id;
          }
        }
      } catch (error) {
        console.error('获取活跃索引信息失败:', error);
      }

      // 然后获取所有索引
      const response = await fetch(`/api/knowledge-base/${knowledgeBaseId}/indices`);
      if (response.ok) {
        const data = await response.json();
        if (data.status === 'success') {
          // 跳过系统生成的激活索引，并标记原始索引的激活状态
          const processedIndices = data.data
            .filter((index: Index) => index.id !== `vector_index_${knowledgeBaseId}`)
            .map((index: Index) => ({
              ...index,
              is_active: index.id === activeIndexId
            }));
          
          setIndices(processedIndices);
        } else {
          message.error('获取索引列表失败');
        }
      } else {
        message.error(`获取索引列表失败(${response.status})`);
      }
    } catch (error) {
      console.error('获取索引列表出错:', error);
      message.error('获取索引列表失败，请检查网络连接');
    } finally {
      setLoading(false);
    }
  };

  // 获取文本文件列表
  const fetchTextFiles = async () => {
    try {
      const response = await fetch(`/api/knowledge-base/${knowledgeBaseId}/text-files`);
      if (response.ok) {
        const data = await response.json();
        if (data.status === 'success') {
          setTextFiles(data.data);
        } else {
          message.error('获取文本文件列表失败');
        }
      } else {
        message.error(`获取文本文件列表失败(${response.status})`);
      }
    } catch (error) {
      console.error('获取文本文件列表出错:', error);
      message.error('获取文本文件列表失败，请检查网络连接');
    }
  };

  // 初始加载
  useEffect(() => {
    if (knowledgeBaseId) {
      fetchIndices();
      fetchTextFiles();
    }
  }, [knowledgeBaseId, refreshKey]);

  // 创建索引
  const handleCreateIndex = async (values: any) => {
    try {
      const response = await fetch(`/api/knowledge-base/${knowledgeBaseId}/indices`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          kb_id: knowledgeBaseId,
          name: values.name,
          description: values.description,
          text_files: selectedFiles
        }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success') {
          message.success('索引创建成功');
          setCreateModalVisible(false);
          form.resetFields();
          setSelectedFiles([]);
          setRefreshKey(prevKey => prevKey + 1);
        } else {
          message.error(result.detail || '创建索引失败');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        message.error(errorData.detail || `创建索引失败(${response.status})`);
      }
    } catch (error) {
      console.error('创建索引出错:', error);
      message.error('创建索引失败，请检查网络连接');
    }
  };

  // 更新索引
  const handleUpdateIndex = async (values: any) => {
    if (!selectedIndex) return;

    try {
      const response = await fetch(`/api/knowledge-base/${knowledgeBaseId}/indices/${selectedIndex.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: values.name,
          description: values.description
        }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success') {
          message.success('索引信息更新成功');
          setUpdateModalVisible(false);
          updateForm.resetFields();
          setRefreshKey(prevKey => prevKey + 1);
        } else {
          message.error(result.detail || '更新索引信息失败');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        message.error(errorData.detail || `更新索引信息失败(${response.status})`);
      }
    } catch (error) {
      console.error('更新索引信息出错:', error);
      message.error('更新索引信息失败，请检查网络连接');
    }
  };

  // 删除索引
  const handleDeleteIndex = async (indexId: string) => {
    try {
      const response = await fetch(`/api/knowledge-base/${knowledgeBaseId}/indices/${indexId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success') {
          message.success('索引删除成功');
          setRefreshKey(prevKey => prevKey + 1);
        } else {
          message.error(result.detail || '删除索引失败');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        message.error(errorData.detail || `删除索引失败(${response.status})`);
      }
    } catch (error) {
      console.error('删除索引出错:', error);
      message.error('删除索引失败，请检查网络连接');
    }
  };

  // 激活索引
  const handleActivateIndex = async (indexId: string) => {
    try {
      const response = await fetch(`/api/knowledge-base/${knowledgeBaseId}/indices/${indexId}/activate`, {
        method: 'POST',
      });

      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success') {
          message.success('索引激活成功');
          setRefreshKey(prevKey => prevKey + 1);
        } else {
          message.error(result.detail || '激活索引失败');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        message.error(errorData.detail || `激活索引失败(${response.status})`);
      }
    } catch (error) {
      console.error('激活索引出错:', error);
      message.error('激活索引失败，请检查网络连接');
    }
  };

  // 禁用索引
  const handleDeactivateIndex = async (indexId: string) => {
    try {
      const response = await fetch(`/api/knowledge-base/${knowledgeBaseId}/indices/${indexId}/deactivate`, {
        method: 'POST',
      });

      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success') {
          message.success('索引已禁用');
          setRefreshKey(prevKey => prevKey + 1);
        } else {
          message.error(result.detail || '禁用索引失败');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        message.error(errorData.detail || `禁用索引失败(${response.status})`);
      }
    } catch (error) {
      console.error('禁用索引出错:', error);
      message.error('禁用索引失败，请检查网络连接');
    }
  };

  // 打开选择文件抽屉
  const openSelectFilesDrawer = () => {
    setSelectFilesDrawerVisible(true);
  };

  // 处理文件选择变化
  const handleFileSelectionChange = (filename: string, checked: boolean) => {
    if (checked) {
      setSelectedFiles([...selectedFiles, filename]);
    } else {
      setSelectedFiles(selectedFiles.filter(f => f !== filename));
    }
  };

  // 全选或取消全选
  const handleSelectAllFiles = (checked: boolean) => {
    if (checked) {
      setSelectedFiles(textFiles.map(file => file.filename));
    } else {
      setSelectedFiles([]);
    }
  };

  // 确认选择的文件
  const confirmSelectedFiles = () => {
    setSelectFilesDrawerVisible(false);
  };

  // 打开报告生成模态框
  const openReportModal = (index: Index) => {
    setSelectedIndex(index);
    setReportModalVisible(true);
    reportForm.setFieldsValue({
      topic: '',
      issuing_unit: '防汛应急指挥部',
      report_date: new Date().toISOString().split('T')[0]
    });
  };

  // 生成报告
  const handleGenerateReport = async (values: any) => {
    if (!selectedIndex) return;
    
    setGeneratingReport(true);
    setReportResult(null);
    
    try {
      const response = await fetch(`/api/knowledge-base/${knowledgeBaseId}/generate-report`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          index_id: selectedIndex.id,
          topic: values.topic,
          issuing_unit: values.issuing_unit,
          report_date: values.report_date
        }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success') {
          setReportResult(result.data);
          message.success('报告生成成功');
        } else {
          message.error(result.detail || '生成报告失败');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        message.error(errorData.detail || `生成报告失败(${response.status})`);
      }
    } catch (error) {
      console.error('生成报告出错:', error);
      message.error('生成报告失败，请检查网络连接');
    } finally {
      setGeneratingReport(false);
    }
  };

  // 表格列定义
  const columns = [
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (isActive: boolean) => (
        isActive ? (
          <Tag color="green" icon={<CheckCircleOutlined />}>活跃</Tag>
        ) : null
      )
    },
    {
      title: '索引名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Index) => (
        <Space direction="vertical" size={0}>
          <Text strong>{text}</Text>
          {record.description && (
            <Text type="secondary" style={{ fontSize: '12px' }}>{record.description}</Text>
          )}
        </Space>
      )
    },
    {
      title: '向量数量',
      dataIndex: 'vector_count',
      key: 'vector_count',
      render: (count: number) => count.toLocaleString()
    },
    {
      title: '文件大小',
      dataIndex: 'file_size',
      key: 'file_size',
      render: (size: number) => {
        if (size < 1024) return `${size} B`;
        if (size < 1024 * 1024) return `${(size / 1024).toFixed(2)} KB`;
        return `${(size / (1024 * 1024)).toFixed(2)} MB`;
      }
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => {
        try {
          return new Date(date).toLocaleString();
        } catch (e) {
          return date;
        }
      }
    },
    {
      title: '包含文件',
      dataIndex: 'text_files',
      key: 'text_files',
      render: (files: string[]) => {
        if (!files || files.length === 0) return <Text type="secondary">所有文件</Text>;
        return (
          <Tooltip 
            title={
              <List
                size="small"
                dataSource={files.slice(0, 10)}
                renderItem={item => <List.Item>{item}</List.Item>}
                footer={files.length > 10 ? `还有 ${files.length - 10} 个文件...` : null}
              />
            } 
            placement="topLeft"
          >
            <Button type="link" size="small">
              {files.length} 个文件
            </Button>
          </Tooltip>
        );
      }
    },
    {
      title: '操作',
      key: 'action',
      render: (_text: unknown, record: Index) => (
        <Space size="small">
          {!record.is_active && (
            <Tooltip title="设为当前索引">
              <Button 
                type="text" 
                icon={<PlayCircleOutlined />} 
                onClick={() => handleActivateIndex(record.id)}
              />
            </Tooltip>
          )}
          {record.is_active && (
            <Tooltip title="禁用当前索引">
              <Popconfirm
                title="确定禁用此索引吗？"
                description="禁用后，向量搜索功能将不可用，直到激活其他索引。"
                onConfirm={() => handleDeactivateIndex(record.id)}
                okText="确认"
                cancelText="取消"
                icon={<ExclamationCircleOutlined style={{ color: 'orange' }} />}
              >
                <Button 
                  type="text" 
                  icon={<StopOutlined />} 
                  style={{ color: 'orange' }}
                />
              </Popconfirm>
            </Tooltip>
          )}
          <Tooltip title="生成报告">
            <Button 
              type="text" 
              icon={<FileMarkdownOutlined />} 
              onClick={() => openReportModal(record)}
            />
          </Tooltip>
          <Tooltip title="编辑信息">
            <Button 
              type="text" 
              icon={<EditOutlined />} 
              onClick={() => {
                setSelectedIndex(record);
                updateForm.setFieldsValue({
                  name: record.name,
                  description: record.description || ''
                });
                setUpdateModalVisible(true);
              }}
            />
          </Tooltip>
          {!record.is_active && (
            <Tooltip title="删除">
              <Popconfirm
                title="确定删除此索引吗？"
                description="删除后无法恢复，且如果该索引为当前活跃索引，将会导致向量搜索功能不可用。"
                onConfirm={() => handleDeleteIndex(record.id)}
                okText="确认"
                cancelText="取消"
                icon={<ExclamationCircleOutlined style={{ color: 'red' }} />}
              >
                <Button 
                  type="text" 
                  danger 
                  icon={<DeleteOutlined />} 
                />
              </Popconfirm>
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  // 过滤索引
  const filteredIndices = indices.filter(index => {
    if (!searchText) return true;
    return (
      index.name.toLowerCase().includes(searchText.toLowerCase()) ||
      (index.description && index.description.toLowerCase().includes(searchText.toLowerCase()))
    );
  });

  return (
    <div className="index-manager">
      <Card title="索引管理" loading={loading}>
        <Space style={{ marginBottom: 16 }} wrap>
          <Input.Search
            placeholder="搜索索引"
            allowClear
            onSearch={value => setSearchText(value)}
            onChange={e => setSearchText(e.target.value)}
            style={{ width: 200 }}
          />
          <Button 
            type="primary" 
            icon={<PlusOutlined />}
            onClick={() => {
              form.resetFields();
              setSelectedFiles([]);
              setCreateModalVisible(true);
            }}
          >
            创建索引
          </Button>
          <Button 
            icon={<ReloadOutlined />}
            onClick={() => setRefreshKey(prevKey => prevKey + 1)}
          >
            刷新
          </Button>
        </Space>

        <Table
          dataSource={filteredIndices}
          columns={columns}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: '暂无索引文件' }}
        />

        <div style={{ marginTop: 16 }}>
          <Text type="secondary">
            当前已有 {indices.length} 个索引文件。活跃索引是系统当前用于向量搜索的索引。
          </Text>
        </div>
      </Card>

      {/* 创建索引的模态框 */}
      <Modal
        title="创建新索引"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateIndex}
        >
          <Form.Item
            name="name"
            label="索引名称"
            rules={[{ required: true, message: '请输入索引名称' }]}
          >
            <Input placeholder="给索引一个描述性的名称，例如'完整知识库索引'" />
          </Form.Item>

          <Form.Item
            name="description"
            label="索引描述"
          >
            <TextArea 
              placeholder="可选：添加对此索引的描述，例如包含的内容类型、用途等" 
              rows={3}
            />
          </Form.Item>

          <Form.Item
            label="选择文本文件"
            extra="您可以选择特定的文本文件来构建索引，或者不选择任何文件使用全部可用文本文件。"
          >
            <Space>
              <Button onClick={openSelectFilesDrawer}>
                选择文件 ({selectedFiles.length ? selectedFiles.length : '全部'})
              </Button>
              {selectedFiles.length > 0 && (
                <Button type="link" onClick={() => setSelectedFiles([])}>
                  清除选择
                </Button>
              )}
            </Space>
            {selectedFiles.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <Text type="secondary">
                  已选择 {selectedFiles.length} 个文件
                </Text>
              </div>
            )}
          </Form.Item>

          <Divider />

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                创建索引
              </Button>
              <Button onClick={() => setCreateModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 更新索引信息的模态框 */}
      <Modal
        title="编辑索引信息"
        open={updateModalVisible}
        onCancel={() => setUpdateModalVisible(false)}
        footer={null}
      >
        <Form
          form={updateForm}
          layout="vertical"
          onFinish={handleUpdateIndex}
        >
          <Form.Item
            name="name"
            label="索引名称"
            rules={[{ required: true, message: '请输入索引名称' }]}
          >
            <Input placeholder="索引名称" />
          </Form.Item>

          <Form.Item
            name="description"
            label="索引描述"
          >
            <TextArea 
              placeholder="索引描述" 
              rows={3}
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                保存
              </Button>
              <Button onClick={() => setUpdateModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 选择文件的抽屉 */}
      <Drawer
        title="选择文本文件"
        placement="right"
        onClose={() => setSelectFilesDrawerVisible(false)}
        open={selectFilesDrawerVisible}
        width={600}
        extra={
          <Space>
            <Checkbox 
              checked={selectedFiles.length === textFiles.length}
              indeterminate={selectedFiles.length > 0 && selectedFiles.length < textFiles.length}
              onChange={(e) => handleSelectAllFiles(e.target.checked)}
            >
              全选
            </Checkbox>
            <Button type="primary" onClick={confirmSelectedFiles}>
              确定 ({selectedFiles.length})
            </Button>
          </Space>
        }
      >
        <div style={{ marginBottom: 16 }}>
          <Input.Search
            placeholder="搜索文件"
            allowClear
            style={{ width: '100%' }}
          />
        </div>

        <List
          dataSource={textFiles}
          renderItem={item => (
            <List.Item>
              <Checkbox
                checked={selectedFiles.includes(item.filename)}
                onChange={(e) => handleFileSelectionChange(item.filename, e.target.checked)}
                style={{ marginRight: 8 }}
              />
              <List.Item.Meta
                title={item.filename}
                description={
                  <Space direction="vertical" size={0}>
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {new Date(item.created_at).toLocaleString()} · {(item.size / 1024).toFixed(2)} KB
                    </Text>
                    {item.description && (
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {item.description}
                      </Text>
                    )}
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      </Drawer>

      {/* 报告生成模态框 */}
      <Modal
        title="基于索引生成报告"
        open={reportModalVisible}
        onCancel={() => setReportModalVisible(false)}
        width={reportResult ? 800 : 600}
        footer={null}
      >
        {reportResult ? (
          <>
            <div style={{ marginBottom: 16 }}>
              <Text>报告生成成功。您可以查看、编辑或保存此报告。</Text>
              <div style={{ marginTop: 8 }}>
                <Button 
                  type="primary" 
                  onClick={() => {
                    // 重置报告结果，返回表单界面
                    setReportResult(null);
                  }}
                  style={{ marginRight: 8 }}
                >
                  返回
                </Button>
                <Button
                  onClick={() => {
                    // 复制到剪贴板
                    navigator.clipboard.writeText(reportResult)
                      .then(() => message.success('已复制到剪贴板'))
                      .catch(() => message.error('复制失败'));
                  }}
                >
                  复制到剪贴板
                </Button>
              </div>
            </div>
            <div 
              style={{ 
                maxHeight: '70vh', 
                overflow: 'auto', 
                border: '1px solid #eee', 
                padding: 16,
                borderRadius: 4,
                backgroundColor: '#fff' 
              }}
            >
              <ReactMarkdown>{reportResult}</ReactMarkdown>
            </div>
          </>
        ) : (
          <Form
            form={reportForm}
            layout="vertical"
            onFinish={handleGenerateReport}
          >
            <Form.Item
              name="topic"
              label="报告主题"
              rules={[{ required: true, message: '请输入报告主题' }]}
            >
              <Input placeholder="输入报告主题，例如'某某地区洪水情况'" />
            </Form.Item>
            
            <Form.Item
              name="issuing_unit"
              label="发布单位"
              rules={[{ required: true, message: '请输入发布单位' }]}
            >
              <Input placeholder="报告发布单位" />
            </Form.Item>
            
            <Form.Item
              name="report_date"
              label="报告日期"
              rules={[{ required: true, message: '请选择报告日期' }]}
            >
              <Input type="date" />
            </Form.Item>
            
            <Form.Item>
              <Space>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  loading={generatingReport}
                  icon={<FileMarkdownOutlined />}
                >
                  生成报告
                </Button>
                <Button onClick={() => setReportModalVisible(false)}>
                  取消
                </Button>
              </Space>
              {selectedIndex && (
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary">
                    将使用索引 "{selectedIndex.name}" 生成报告，包含 {selectedIndex.vector_count} 条向量数据。
                  </Text>
                </div>
              )}
            </Form.Item>
          </Form>
        )}
      </Modal>
    </div>
  );
};

export default IndexManager; 