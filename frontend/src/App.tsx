import React, { useState } from 'react';
import { Layout, Menu } from 'antd';
import { useNavigate, Routes, Route, useLocation } from 'react-router-dom';
import { UploadOutlined, DatabaseOutlined, FileTextOutlined, DashboardOutlined } from '@ant-design/icons';
import LinkExtractor from './components/LinkExtractor';
import DataManager from './components/DataManager';
import ReportGenerator from './components/ReportGenerator';
import SystemMonitor from './components/SystemMonitor';
import './App.css';

const { Header, Content, Sider } = Layout;

const App: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // 根据当前路径设置默认选中的菜单项
  const getDefaultSelectedKey = () => {
    const path = location.pathname;
    if (path.includes('/data')) return '2';
    if (path.includes('/report')) return '3';
    if (path.includes('/monitor')) return '4';
    return '1';
  };

  const handleMenuClick = (key: string) => {
    switch (key) {
      case '1':
        navigate('/');
        break;
      case '2':
        navigate('/data');
        break;
      case '3':
        navigate('/report');
        break;
      case '4':
        navigate('/monitor');
        break;
    }
  };

  return (
    <Layout>
      <Header style={{
        padding: '0 24px',
        background: '#fff',
        borderBottom: '1px solid #f0f0f0',
        position: 'fixed',
        width: '100%',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        height: '64px'
      }}>
        <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 500 }}>防汛应急报告生成系统</h1>
      </Header>
      <Layout style={{ marginTop: '64px', minHeight: 'calc(100vh - 64px)' }}>
        <Sider
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
          style={{
            background: '#001529',
            position: 'fixed',
            left: 0,
            top: '64px',
            height: 'calc(100vh - 64px)',
            zIndex: 999
          }}
          breakpoint="lg"
          collapsedWidth="80"
          width={240}
        >
          <Menu
            theme="dark"
            selectedKeys={[getDefaultSelectedKey()]}
            mode="inline"
            onClick={({ key }) => handleMenuClick(key)}
            items={[
              {
                key: '1',
                icon: <UploadOutlined />,
                label: '链接提取',
              },
              {
                key: '2',
                icon: <DatabaseOutlined />,
                label: '数据管理',
              },
              {
                key: '3',
                icon: <FileTextOutlined />,
                label: '报告生成',
              },
              {
                key: '4',
                icon: <DashboardOutlined />,
                label: '系统监控',
              },
            ]}
          />
        </Sider>
        <Layout style={{
          marginLeft: collapsed ? '80px' : '240px',
          transition: 'margin-left 0.2s',
          padding: '24px',
          background: '#f0f2f5'
        }}>
          <Content style={{
            padding: '24px',
            background: '#fff',
            borderRadius: '4px',
            minHeight: 'calc(100vh - 112px)',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)'
          }}>
            <Routes>
              <Route path="/" element={<LinkExtractor />} />
              <Route path="/data" element={<DataManager />} />
              <Route path="/report" element={<ReportGenerator />} />
              <Route path="/monitor" element={<SystemMonitor />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
};

export default App;