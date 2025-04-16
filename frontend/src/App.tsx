import React, { useState, useEffect } from 'react';
import { Layout, Menu, Button, Tooltip, Switch, Dropdown, message, MenuProps } from 'antd';
import { useNavigate, Routes, Route, useLocation, Navigate } from 'react-router-dom';
import { 
  BookOutlined, 
  BulbOutlined,
  GithubOutlined,
  QuestionCircleOutlined,
  UserOutlined,
  LogoutOutlined,
  SettingOutlined
} from '@ant-design/icons';
import SystemMonitor from './components/SystemMonitor';
import KnowledgeBase from './components/KnowledgeBase';
import Login from './components/Login';
import Profile from './components/Profile';
import Settings from './components/Settings';
import axios from 'axios';
import './App.css';

const { Header, Content } = Layout;

// 定义用户类型
interface User {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
}

// 受保护路由组件
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  // 检查是否已登录
  const isAuthenticated = localStorage.getItem('auth_token') !== null;
  
  // 如果未登录，重定向到登录页面
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

const App: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [darkMode, setDarkMode] = useState(localStorage.getItem('darkMode') === 'true');
  const [user, setUser] = useState<User | null>(null);
  const [authenticated, setAuthenticated] = useState(false);

  // 初始化时检查用户是否已登录
  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      console.log("发现已存储的认证令牌");
      // 设置默认请求头
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      
      // 尝试加载用户信息
      const storedUser = localStorage.getItem('user_info');
      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser));
          setAuthenticated(true);
          console.log("已从localStorage恢复用户信息");
        } catch (e) {
          console.error('解析用户信息失败:', e);
          handleLogout();
        }
      } else {
        // 获取用户信息
        fetchUserInfo();
      }
    }
  }, []);

  // 保存暗黑模式设置
  useEffect(() => {
    localStorage.setItem('darkMode', darkMode.toString());
  }, [darkMode]);

  // 获取用户信息
  const fetchUserInfo = async () => {
    try {
      console.log("正在从API获取用户信息");
      const response = await axios.get('/api/auth/me');
      console.log("获取到用户信息:", response.data);
      setUser(response.data);
      setAuthenticated(true);
      localStorage.setItem('user_info', JSON.stringify(response.data));
    } catch (error) {
      console.error('获取用户信息失败:', error);
      handleLogout();
    }
  };

  // 处理登录成功
  const handleLoginSuccess = (userData: User, token: string) => {
    setUser(userData);
    setAuthenticated(true);
  };

  // 处理登出
  const handleLogout = () => {
    // 清除本地存储
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_info');
    
    // 重置状态
    setUser(null);
    setAuthenticated(false);
    
    // 清除默认请求头
    delete axios.defaults.headers.common['Authorization'];
    
    // 跳转到登录页面
    navigate('/login');
    
    message.success('已成功退出登录');
  };

  const getDefaultSelectedKey = () => {
    const path = location.pathname;
    if (path.includes('/monitor')) return 'monitor';
    if (path.includes('/profile')) return 'profile';
    if (path.includes('/settings')) return 'settings';
    return 'kb';
  };

  // 用户菜单项
  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      label: '个人资料',
      icon: <UserOutlined />,
      onClick: () => navigate('/profile')
    },
    {
      key: 'settings',
      label: '设置',
      icon: <SettingOutlined />,
      onClick: () => navigate('/settings')
    },
    {
      type: 'divider'
    },
    {
      key: 'logout',
      label: '退出登录',
      icon: <LogoutOutlined />,
      onClick: handleLogout
    }
  ];

  // 显示已登录的界面
  const renderAuthenticatedApp = () => (
    <Layout className={darkMode ? 'dark-theme' : 'light-theme'}>
      <Header className="app-header">
        <div className="header-logo">
          <img 
            src="/logo.svg" 
            alt="FloodReport" 
            style={{ height: 28, marginRight: 10 }} 
          />
          <span className="logo-text">FloodReport</span>
        </div>
        
        <Menu
          mode="horizontal"
          selectedKeys={[getDefaultSelectedKey()]}
          className="header-menu"
        >
          <Menu.Item key="kb" onClick={() => navigate('/knowledge-base')}>
            <BookOutlined /> 知识库
          </Menu.Item>
          <Menu.Item key="monitor" onClick={() => navigate('/monitor')}>
            <BulbOutlined /> 系统监控
          </Menu.Item>
          <Menu.Item key="settings" onClick={() => navigate('/settings')}>
            <SettingOutlined /> 系统设置
          </Menu.Item>
        </Menu>
        
        <div className="header-actions">
          <Tooltip title="切换主题">
            <Switch 
              checkedChildren="🌙" 
              unCheckedChildren="☀️" 
              checked={darkMode}
              onChange={setDarkMode}
              className="theme-switch"
            />
          </Tooltip>
          <Button type="text" icon={<QuestionCircleOutlined />} />
          <Button type="text" icon={<GithubOutlined />} />
          
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Button 
              type="primary" 
              shape="circle" 
              className="user-avatar"
            >
              {user?.username?.charAt(0)?.toUpperCase() || <UserOutlined />}
            </Button>
          </Dropdown>
        </div>
      </Header>
      
      <Content className="app-content">
        <Routes>
          <Route 
            path="/knowledge-base" 
            element={
              <ProtectedRoute>
                <KnowledgeBase />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/monitor" 
            element={
              <ProtectedRoute>
                <SystemMonitor />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/profile" 
            element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/settings" 
            element={
              <ProtectedRoute>
                <Settings />
              </ProtectedRoute>
            } 
          />
          <Route path="/" element={<Navigate to="/knowledge-base" replace />} />
          <Route path="*" element={<Navigate to="/knowledge-base" replace />} />
        </Routes>
      </Content>
    </Layout>
  );

  // 主应用渲染
  return (
    <Routes>
      <Route path="/login" element={
        authenticated ? 
          <Navigate to="/knowledge-base" replace /> : 
          <Login onLoginSuccess={handleLoginSuccess} />
      } />
      <Route path="*" element={
        authenticated ? 
          renderAuthenticatedApp() : 
          <Navigate to="/login" replace />
      } />
    </Routes>
  );
};

export default App;