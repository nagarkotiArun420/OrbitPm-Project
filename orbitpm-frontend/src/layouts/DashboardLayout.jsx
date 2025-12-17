import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation, Link } from 'react-router-dom';
import { Layout, Menu, Button, Avatar, Dropdown, Space, ConfigProvider, theme as antdTheme } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  DashboardOutlined,
  ProjectOutlined,
  CheckSquareOutlined,
  TeamOutlined,
  FileTextOutlined,
  BellOutlined,
  UserOutlined,
  LogoutOutlined,
  SunOutlined,
  MoonOutlined,
  RocketOutlined
} from '@ant-design/icons';
import { useAuth } from '../context/AuthContext';
import { useAppTheme } from '../context/ThemeContext';

const { Header, Sider, Content, Footer } = Layout;

const DashboardLayout = () => {
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useAppTheme();
  const navigate = useNavigate();
  const location = useLocation();

  const isDark = theme === 'dark';

  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: '/projects',
      icon: <ProjectOutlined />,
      label: 'Projects',
    },
    {
      key: '/tasks',
      icon: <CheckSquareOutlined />,
      label: 'Tasks',
    },
    {
      key: '/teams',
      icon: <TeamOutlined />,
      label: 'Teams',
    },
    {
      key: '/invoices',
      icon: <FileTextOutlined />,
      label: 'Invoices',
    },
  ];

  const handleMenuClick = ({ key }) => {
    navigate(key);
  };

  const userMenu = {
    items: [
      {
        key: 'profile',
        label: (
          <div style={{ padding: '4px 8px' }}>
            <div style={{ fontWeight: 600 }}>{user?.full_name}</div>
            <div style={{ fontSize: '12px', color: '#8c8c8c' }}>{user?.role}</div>
          </div>
        ),
      },
      {
        type: 'divider',
      },
      {
        key: 'logout',
        label: 'Sign Out',
        icon: <LogoutOutlined />,
        danger: true,
        onClick: () => {
          logout();
          navigate('/login');
        },
      },
    ],
  };

  return (
    <ConfigProvider
      theme={{
        algorithm: isDark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
        token: {
          colorPrimary: '#6366f1', // OrbitPM Indigo Theme
          fontFamily: "'Inter', sans-serif",
          borderRadius: 8,
        },
      }}
    >
      <Layout style={{ minHeight: '100vh' }}>
        {/* Responsive Collapsible Sidebar */}
        <Sider
          trigger={null}
          collapsible
          collapsed={collapsed}
          breakpoint="lg"
          onBreakpoint={(broken) => {
            setCollapsed(broken);
          }}
          theme={isDark ? 'dark' : 'light'}
          style={{
            boxShadow: isDark ? 'none' : '2px 0 8px 0 rgba(29,35,41,.05)',
            zIndex: 10,
            position: 'sticky',
            top: 0,
            height: '100vh',
          }}
        >
          {/* Logo container */}
          <div
            style={{
              height: '64px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: collapsed ? 'center' : 'flex-start',
              padding: '0 24px',
              borderBottom: `1px solid ${isDark ? '#303030' : '#f0f0f0'}`,
              overflow: 'hidden',
              gap: '12px',
            }}
          >
            <RocketOutlined style={{ fontSize: '20px', color: '#6366f1' }} />
            {!collapsed && (
              <span
                style={{
                  fontFamily: "'Outfit', sans-serif",
                  fontWeight: 700,
                  fontSize: '18px',
                  color: isDark ? '#ffffff' : '#1f1f1f',
                  letterSpacing: '-0.5px',
                }}
              >
                Orbit<span style={{ color: '#6366f1' }}>PM</span>
              </span>
            )}
          </div>

          <Menu
            theme={isDark ? 'dark' : 'light'}
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={handleMenuClick}
            style={{ borderRight: 0, marginTop: '16px' }}
          />
        </Sider>

        <Layout>
          {/* Top Navbar Header */}
          <Header
            style={{
              padding: '0 24px',
              background: isDark ? '#141414' : '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              boxShadow: isDark ? 'none' : '0 1px 4px rgba(0,21,41,.08)',
              borderBottom: `1px solid ${isDark ? '#303030' : '#f0f0f0'}`,
              position: 'sticky',
              top: 0,
              zIndex: 9,
            }}
          >
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              style={{ fontSize: '16px', width: 64, height: 64 }}
            />

            <Space size="large">
              {/* Theme Toggle Button */}
              <Button
                type="text"
                shape="circle"
                icon={isDark ? <SunOutlined style={{ color: '#fadb14' }} /> : <MoonOutlined />}
                onClick={toggleTheme}
              />

              {/* Notification icon */}
              <Button type="text" shape="circle" icon={<BellOutlined />} />

              {/* Account Dropdown */}
              <Dropdown menu={userMenu} placement="bottomRight" trigger={['click']}>
                <Space style={{ cursor: 'pointer' }}>
                  <Avatar
                    style={{ backgroundColor: '#6366f1' }}
                    icon={<UserOutlined />}
                    src={user?.avatar}
                  />
                  {!collapsed && (
                    <span style={{ fontWeight: 500, color: isDark ? '#d9d9d9' : '#595959' }}>
                      {user?.full_name}
                    </span>
                  )}
                </Space>
              </Dropdown>
            </Space>
          </Header>

          {/* Main Content Area */}
          <Content
            style={{
              margin: '24px 24px 0',
              padding: '24px',
              background: isDark ? '#1f1f1f' : '#ffffff',
              borderRadius: '8px',
              minHeight: '280px',
              boxShadow: isDark ? 'none' : '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
            }}
          >
            <Outlet />
          </Content>

          <Footer style={{ textAlign: 'center', color: '#bfbfbf', fontSize: '13px' }}>
            OrbitPM ©2026. Scalable SaaS Workflows.
          </Footer>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
};

export default DashboardLayout;
