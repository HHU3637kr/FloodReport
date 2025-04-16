import React, { useState } from 'react';
import { Form, Input, Button, Card, Typography, message, Checkbox, Divider } from 'antd';
import { UserOutlined, LockOutlined, LoginOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import '../styles/Login.css';

const { Title, Text } = Typography;

interface LoginProps {
  onLoginSuccess: (user: any, token: string) => void;
}

const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const handleLogin = async (values: any) => {
    setLoading(true);
    try {
      console.log("尝试登录:", values.username);
      
      // 构建请求头
      const headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
      };
      
      // 构建表单数据
      const params = new URLSearchParams();
      params.append('username', values.username);
      params.append('password', values.password);
      
      // 发送登录请求
      const response = await axios.post('/api/auth/login', params, { headers });
      
      console.log("登录响应:", response.data);
      
      // 处理成功登录
      const { access_token, user } = response.data;
      
      // 保存令牌到localStorage
      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('user_info', JSON.stringify(user));
      
      // 设置默认请求头
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      // 通知父组件登录成功
      onLoginSuccess(user, access_token);
      
      message.success('登录成功！');
      
      // 跳转到知识库页面
      navigate('/knowledge-base');
    } catch (error: any) {
      console.error('登录失败:', error);
      
      if (error.response) {
        const { status, data } = error.response;
        if (status === 401) {
          message.error('用户名或密码错误');
        } else {
          message.error(data.detail || '登录失败，请重试');
        }
      } else {
        message.error('登录失败，请检查网络连接');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <Card className="login-card">
        <div className="login-header">
          <img src="/logo.svg" alt="FloodReport" className="login-logo" />
          <Title level={3}>防汛应急报告生成系统</Title>
          <Text type="secondary">登录您的账户以继续</Text>
        </div>
        
        <Form
          form={form}
          name="login"
          onFinish={handleLogin}
          layout="vertical"
          requiredMark={false}
          className="login-form"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input 
              prefix={<UserOutlined />} 
              placeholder="用户名" 
              size="large"
            />
          </Form.Item>
          
          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password 
              prefix={<LockOutlined />} 
              placeholder="密码" 
              size="large"
            />
          </Form.Item>
          
          <Form.Item name="remember" valuePropName="checked">
            <Checkbox>记住我</Checkbox>
          </Form.Item>
          
          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              icon={<LoginOutlined />}
              block
              size="large"
              className="login-button"
            >
              登录
            </Button>
          </Form.Item>
        </Form>
        
        <Divider />
        
        <div className="login-info">
          <Text type="secondary">默认管理员账号: admin</Text>
          <Text type="secondary">默认密码: admin123</Text>
        </div>
      </Card>
    </div>
  );
};

export default Login; 