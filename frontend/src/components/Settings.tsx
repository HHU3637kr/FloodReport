import React, { useState, useEffect } from 'react';
import { Card, Form, Input, Button, message, Tabs, Divider, Typography, Alert, Spin, Switch } from 'antd';
import { SaveOutlined, ApiOutlined, RobotOutlined, ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

interface ModelSettings {
  understanding: {
    provider: string;
    api_key: string;
    model_name: string;
  };
  embedding: {
    provider: string;
    api_key: string;
    model_name: string;
  };
  generation: {
    provider: string;
    api_key: string;
    model_name: string;
  };
}

const Settings: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [useCustomKeys, setUseCustomKeys] = useState(false);
  const [settings, setSettings] = useState<ModelSettings | null>(null);

  // 获取当前设置
  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/system/model-settings');
      setSettings(response.data.settings);
      setUseCustomKeys(response.data.use_custom_keys);
      
      // 设置表单值
      form.setFieldsValue({
        understanding_provider: response.data.settings.understanding.provider,
        understanding_api_key: response.data.settings.understanding.api_key,
        understanding_model_name: response.data.settings.understanding.model_name,
        
        embedding_provider: response.data.settings.embedding.provider,
        embedding_api_key: response.data.settings.embedding.api_key,
        embedding_model_name: response.data.settings.embedding.model_name,
        
        generation_provider: response.data.settings.generation.provider,
        generation_api_key: response.data.settings.generation.api_key,
        generation_model_name: response.data.settings.generation.model_name,
      });
    } catch (error) {
      console.error('获取设置失败:', error);
      message.error('获取模型设置失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 保存设置
  const handleSaveSettings = async (values: any) => {
    setSaveLoading(true);
    try {
      const modelSettings = {
        understanding: {
          provider: values.understanding_provider,
          api_key: values.understanding_api_key,
          model_name: values.understanding_model_name,
        },
        embedding: {
          provider: values.embedding_provider,
          api_key: values.embedding_api_key,
          model_name: values.embedding_model_name,
        },
        generation: {
          provider: values.generation_provider,
          api_key: values.generation_api_key,
          model_name: values.generation_model_name,
        }
      };

      await axios.post('/system/model-settings', { 
        settings: modelSettings,
        use_custom_keys: useCustomKeys
      });
      
      message.success('设置已保存');
    } catch (error: any) {
      console.error('保存设置失败:', error);
      
      if (error.response) {
        message.error(error.response.data.detail || '保存失败，请重试');
      } else {
        message.error('保存失败，请检查网络连接');
      }
    } finally {
      setSaveLoading(false);
    }
  };

  const toggleUseCustomKeys = () => {
    setUseCustomKeys(!useCustomKeys);
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <p>加载设置...</p>
      </div>
    );
  }

  return (
    <Card title="系统设置">
      <Alert
        message="API密钥设置"
        description={
          <div>
            <p>您可以配置系统使用的各种模型API密钥。您可以选择使用自己的API密钥，或使用系统默认的API密钥。</p>
            <div style={{ marginTop: '10px' }}>
              <Switch 
                checked={useCustomKeys} 
                onChange={toggleUseCustomKeys} 
                checkedChildren="使用自定义API密钥" 
                unCheckedChildren="使用系统默认API密钥"
              />
              <Text style={{ marginLeft: '10px' }}>
                {useCustomKeys ? '系统将使用您提供的API密钥' : '系统将使用默认API密钥'}
              </Text>
            </div>
          </div>
        }
        type="info"
        showIcon
        style={{ marginBottom: '20px' }}
      />

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSaveSettings}
        disabled={!useCustomKeys}
      >
        <Tabs defaultActiveKey="understanding">
          <TabPane 
            tab={<span><RobotOutlined /> 理解模型</span>} 
            key="understanding"
          >
            <Form.Item 
              name="understanding_provider" 
              label="服务提供商"
              rules={[{ required: true, message: '请输入服务提供商' }]}
            >
              <Input placeholder="例如: volcengine" />
            </Form.Item>
            
            <Form.Item 
              name="understanding_api_key" 
              label="API密钥"
              rules={[{ required: true, message: '请输入API密钥' }]}
            >
              <Input.Password placeholder="输入API密钥" />
            </Form.Item>
            
            <Form.Item 
              name="understanding_model_name" 
              label="模型名称"
              rules={[{ required: true, message: '请输入模型名称' }]}
            >
              <Input placeholder="例如: ep-20250309105703-52v9q" />
            </Form.Item>
          </TabPane>
          
          <TabPane 
            tab={<span><ApiOutlined /> 嵌入模型</span>} 
            key="embedding"
          >
            <Form.Item 
              name="embedding_provider" 
              label="服务提供商"
              rules={[{ required: true, message: '请输入服务提供商' }]}
            >
              <Input placeholder="例如: aliyun" />
            </Form.Item>
            
            <Form.Item 
              name="embedding_api_key" 
              label="API密钥"
              rules={[{ required: true, message: '请输入API密钥' }]}
            >
              <Input.Password placeholder="输入API密钥" />
            </Form.Item>
            
            <Form.Item 
              name="embedding_model_name" 
              label="模型名称"
              rules={[{ required: true, message: '请输入模型名称' }]}
            >
              <Input placeholder="例如: text-embedding-v3" />
            </Form.Item>
          </TabPane>
          
          <TabPane 
            tab={<span><RobotOutlined /> 生成模型</span>} 
            key="generation"
          >
            <Form.Item 
              name="generation_provider" 
              label="服务提供商"
              rules={[{ required: true, message: '请输入服务提供商' }]}
            >
              <Input placeholder="例如: volcengine" />
            </Form.Item>
            
            <Form.Item 
              name="generation_api_key" 
              label="API密钥"
              rules={[{ required: true, message: '请输入API密钥' }]}
            >
              <Input.Password placeholder="输入API密钥" />
            </Form.Item>
            
            <Form.Item 
              name="generation_model_name" 
              label="模型名称"
              rules={[{ required: true, message: '请输入模型名称' }]}
            >
              <Input placeholder="例如: doubao-1.5-pro-32k-250115" />
            </Form.Item>
          </TabPane>
        </Tabs>

        <Divider />
        
        <Form.Item>
          <Button 
            type="primary" 
            htmlType="submit" 
            icon={<SaveOutlined />} 
            loading={saveLoading}
            disabled={!useCustomKeys}
          >
            保存设置
          </Button>
          <Button 
            style={{ marginLeft: '10px' }} 
            icon={<ReloadOutlined />} 
            onClick={fetchSettings}
          >
            刷新
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default Settings; 