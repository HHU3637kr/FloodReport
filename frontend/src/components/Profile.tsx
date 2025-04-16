import React, { useState, useEffect } from 'react';
import { Card, Tabs, Form, Input, Button, message, Divider, Avatar, Typography, Row, Col } from 'antd';
import { UserOutlined, MailOutlined, EditOutlined, LockOutlined, SaveOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

// 定义用户类型
interface User {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
}

const Profile: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [profileForm] = Form.useForm();
  const [passwordForm] = Form.useForm();

  // 获取用户信息
  useEffect(() => {
    fetchUserInfo();
  }, []);

  // 当用户信息改变时，更新表单
  useEffect(() => {
    if (user) {
      profileForm.setFieldsValue({
        email: user.email,
        full_name: user.full_name || '',
      });
    }
  }, [user, profileForm]);

  // 从API获取用户信息
  const fetchUserInfo = async () => {
    try {
      const response = await axios.get('/api/auth/me');
      setUser(response.data);
    } catch (error) {
      console.error('获取用户信息失败:', error);
      message.error('获取用户信息失败，请重试');
    }
  };

  // 更新用户个人信息
  const handleUpdateProfile = async (values: any) => {
    setLoading(true);
    try {
      const response = await axios.put('/api/auth/me', values);
      
      // 更新本地用户信息
      setUser(response.data);
      
      // 更新localStorage中的用户信息
      localStorage.setItem('user_info', JSON.stringify(response.data));
      
      message.success('个人信息更新成功');
    } catch (error: any) {
      console.error('更新个人信息失败:', error);
      
      if (error.response) {
        message.error(error.response.data.detail || '更新失败，请重试');
      } else {
        message.error('更新失败，请检查网络连接');
      }
    } finally {
      setLoading(false);
    }
  };

  // 更新密码
  const handleUpdatePassword = async (values: any) => {
    setLoading(true);
    try {
      await axios.put('/api/auth/me/password', {
        current_password: values.current_password,
        new_password: values.new_password
      });
      
      message.success('密码更新成功');
      passwordForm.resetFields();
    } catch (error: any) {
      console.error('更新密码失败:', error);
      
      if (error.response) {
        message.error(error.response.data.detail || '更新密码失败，请重试');
      } else {
        message.error('更新密码失败，请检查网络连接');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '20px' }}>
      <Card>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Avatar 
            size={80} 
            icon={<UserOutlined />} 
            style={{ 
              backgroundColor: '#1890ff',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              margin: '0 auto 16px'
            }}
          >
            {user?.username?.charAt(0)?.toUpperCase()}
          </Avatar>
          <Title level={3}>{user?.username}</Title>
          <Text type="secondary">{user?.full_name || '未设置姓名'}</Text>
        </div>
        
        <Divider />
        
        <Tabs defaultActiveKey="profile">
          <TabPane tab="个人资料" key="profile">
            <Form
              form={profileForm}
              layout="vertical"
              onFinish={handleUpdateProfile}
            >
              <Row gutter={24}>
                <Col span={24}>
                  <Form.Item
                    name="username"
                    label="用户名"
                  >
                    <Input 
                      prefix={<UserOutlined />} 
                      disabled 
                      defaultValue={user?.username}
                    />
                  </Form.Item>
                </Col>
                
                <Col span={24}>
                  <Form.Item
                    name="email"
                    label="电子邮箱"
                    rules={[
                      { required: true, message: '请输入电子邮箱' },
                      { type: 'email', message: '请输入有效的电子邮箱' }
                    ]}
                  >
                    <Input 
                      prefix={<MailOutlined />} 
                      placeholder="请输入电子邮箱" 
                    />
                  </Form.Item>
                </Col>
                
                <Col span={24}>
                  <Form.Item
                    name="full_name"
                    label="全名"
                  >
                    <Input 
                      prefix={<UserOutlined />} 
                      placeholder="请输入全名" 
                    />
                  </Form.Item>
                </Col>
              </Row>
              
              <Form.Item>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  loading={loading}
                  icon={<SaveOutlined />}
                >
                  保存修改
                </Button>
              </Form.Item>
            </Form>
          </TabPane>
          
          <TabPane tab="修改密码" key="password">
            <Form
              form={passwordForm}
              layout="vertical"
              onFinish={handleUpdatePassword}
            >
              <Form.Item
                name="current_password"
                label="当前密码"
                rules={[{ required: true, message: '请输入当前密码' }]}
              >
                <Input.Password 
                  prefix={<LockOutlined />} 
                  placeholder="请输入当前密码" 
                />
              </Form.Item>
              
              <Form.Item
                name="new_password"
                label="新密码"
                rules={[
                  { required: true, message: '请输入新密码' },
                  { min: 6, message: '密码长度至少为6个字符' }
                ]}
              >
                <Input.Password 
                  prefix={<LockOutlined />} 
                  placeholder="请输入新密码" 
                />
              </Form.Item>
              
              <Form.Item
                name="confirm_password"
                label="确认新密码"
                dependencies={['new_password']}
                rules={[
                  { required: true, message: '请确认新密码' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('new_password') === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error('两次输入的密码不一致'));
                    },
                  }),
                ]}
              >
                <Input.Password 
                  prefix={<LockOutlined />} 
                  placeholder="请确认新密码" 
                />
              </Form.Item>
              
              <Form.Item>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  loading={loading}
                  icon={<EditOutlined />}
                >
                  更新密码
                </Button>
              </Form.Item>
            </Form>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default Profile; 