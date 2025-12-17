import React from 'react';
import { Row, Col, Card, Statistic, Progress, Space, Table, Tag, List } from 'antd';
import {
  ProjectOutlined,
  CheckSquareOutlined,
  DollarCircleOutlined,
  ClockCircleOutlined,
  ArrowUpOutlined,
  ThunderboltOutlined,
  TeamOutlined
} from '@ant-design/icons';
import { useAuth } from '../context/AuthContext';

const Dashboard = () => {
  const { user } = useAuth();

  // Mock dashboard overview statistics
  const stats = [
    {
      title: 'Active Projects',
      value: 12,
      suffix: '+2 this week',
      icon: <ProjectOutlined style={{ fontSize: '24px', color: '#6366f1' }} />,
      bg: 'rgba(99, 102, 241, 0.05)',
      color: '#6366f1',
    },
    {
      title: 'Task Completion',
      value: 84,
      suffix: '% (42/50 tasks)',
      icon: <CheckSquareOutlined style={{ fontSize: '24px', color: '#10b981' }} />,
      bg: 'rgba(16, 185, 129, 0.05)',
      color: '#10b981',
    },
    {
      title: 'Open Invoices',
      value: '$14,250',
      suffix: '3 outstanding',
      icon: <DollarCircleOutlined style={{ fontSize: '24px', color: '#f59e0b' }} />,
      bg: 'rgba(245, 158, 11, 0.05)',
      color: '#f59e0b',
    },
    {
      title: 'Active Team Members',
      value: 8,
      suffix: '4 online now',
      icon: <TeamOutlined style={{ fontSize: '24px', color: '#ec4899' }} />,
      bg: 'rgba(236, 72, 153, 0.05)',
      color: '#ec4899',
    },
  ];

  const recentTasks = [
    {
      key: '1',
      title: 'Redesign client proposal view',
      project: 'Acme Redesign',
      status: 'IN_PROGRESS',
      priority: 'HIGH',
    },
    {
      key: '2',
      title: 'Setup simpleJWT token rotation',
      project: 'OrbitPM Platform',
      status: 'DONE',
      priority: 'CRITICAL',
    },
    {
      key: '3',
      title: 'Fix responsive navigation sidebar bug',
      project: 'Nike Portal',
      status: 'TODO',
      priority: 'MEDIUM',
    },
  ];

  const recentTasksColumns = [
    {
      title: 'Task Title',
      dataIndex: 'title',
      key: 'title',
    },
    {
      title: 'Project',
      dataIndex: 'project',
      key: 'project',
    },
    {
      title: 'Priority',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority) => {
        let color = 'blue';
        if (priority === 'CRITICAL') color = 'red';
        if (priority === 'HIGH') color = 'volcano';
        if (priority === 'MEDIUM') color = 'orange';
        return <Tag color={color}>{priority}</Tag>;
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        let color = 'gold';
        if (status === 'DONE') color = 'success';
        if (status === 'IN_PROGRESS') color = 'processing';
        return <Tag color={color}>{status}</Tag>;
      },
    },
  ];

  const quickActions = [
    {
      title: 'Create New Project',
      description: 'Scaffold a new project workspace',
      icon: <ThunderboltOutlined style={{ color: '#6366f1' }} />,
    },
    {
      title: 'Add Team Member',
      description: 'Invite a designer or developer',
      icon: <TeamOutlined style={{ color: '#10b981' }} />,
    },
    {
      title: 'Generate Client Invoice',
      description: 'Bill active task hours',
      icon: <DollarCircleOutlined style={{ color: '#f59e0b' }} />,
    },
  ];

  return (
    <div>
      {/* Header welcome card */}
      <div style={{ marginBottom: '32px' }}>
        <h1
          style={{
            fontFamily: "'Outfit', sans-serif",
            fontWeight: 700,
            fontSize: '28px',
            margin: 0,
          }}
        >
          Welcome Back, {user?.full_name || 'Agile Professional'}!
        </h1>
        <p style={{ color: '#8c8c8c', margin: '4px 0 0 0' }}>
          Here is a high-level summary of your workspace activities and project deliveries.
        </p>
      </div>

      {/* Overview Statistics Cards Grid */}
      <Row gutter={[24, 24]} style={{ marginBottom: '32px' }}>
        {stats.map((stat, i) => (
          <Col xs={24} sm={12} lg={6} key={i}>
            <Card
              bordered={false}
              style={{
                borderRadius: '12px',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.02)',
                border: '1px solid rgba(0, 0, 0, 0.03)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <Statistic
                    title={
                      <span
                        style={{
                          color: '#8c8c8c',
                          fontWeight: 500,
                          fontSize: '14px',
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                        }}
                      >
                        {stat.title}
                      </span>
                    }
                    value={stat.value}
                    valueStyle={{
                      fontWeight: 700,
                      fontFamily: "'Outfit', sans-serif",
                      fontSize: '26px',
                    }}
                  />
                  <div style={{ marginTop: '4px', fontSize: '13px', color: '#8c8c8c' }}>
                    <ArrowUpOutlined style={{ color: stat.color, marginRight: '4px' }} />
                    <span style={{ fontWeight: 500, color: stat.color }}>{stat.suffix}</span>
                  </div>
                </div>

                <div
                  style={{
                    width: '54px',
                    height: '54px',
                    borderRadius: '12px',
                    backgroundColor: stat.bg,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {stat.icon}
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Nested Row: Recent Tasks + Progress Charts & Quick Actions */}
      <Row gutter={[24, 24]}>
        {/* Recent Tasks Gated Panel */}
        <Col xs={24} lg={16}>
          <Card
            title={
              <div
                style={{
                  fontFamily: "'Outfit', sans-serif",
                  fontWeight: 600,
                  fontSize: '18px',
                }}
              >
                Recent Tasks Assigned to You
              </div>
            }
            bordered={false}
            style={{
              borderRadius: '12px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.02)',
              height: '100%',
            }}
          >
            <Table
              columns={recentTasksColumns}
              dataSource={recentTasks}
              pagination={false}
              size="middle"
            />
          </Card>
        </Col>

        {/* Progress Wheel and Quick Action panel */}
        <Col xs={24} lg={8}>
          <Space direction="vertical" size="large" style={{ width: '100%', height: '100%' }}>
            {/* Project Progress Gauge */}
            <Card
              title={
                <div
                  style={{
                    fontFamily: "'Outfit', sans-serif",
                    fontWeight: 600,
                    fontSize: '16px',
                  }}
                >
                  Monthly Milestone Targets
                </div>
              }
              bordered={false}
              style={{
                borderRadius: '12px',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.02)',
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '12px 0' }}>
                <Progress
                  type="dashboard"
                  percent={78}
                  strokeColor={{
                    '0%': '#6366f1',
                    '100%': '#a855f7',
                  }}
                  strokeWidth={8}
                />
                <span
                  style={{
                    fontFamily: "'Outfit', sans-serif",
                    fontWeight: 600,
                    marginTop: '16px',
                    fontSize: '14px',
                  }}
                >
                  Project Delivery Milestone
                </span>
                <span style={{ fontSize: '12px', color: '#bfbfbf' }}>Target release: June 15, 2026</span>
              </div>
            </Card>

            {/* Quick Actions List */}
            <Card
              title={
                <div
                  style={{
                    fontFamily: "'Outfit', sans-serif",
                    fontWeight: 600,
                    fontSize: '16px',
                  }}
                >
                  Workspace Quick Actions
                </div>
              }
              bordered={false}
              style={{
                borderRadius: '12px',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.02)',
              }}
            >
              <List
                itemLayout="horizontal"
                dataSource={quickActions}
                renderItem={(item) => (
                  <List.Item style={{ cursor: 'pointer', padding: '12px 0' }}>
                    <List.Item.Meta
                      avatar={
                        <div
                          style={{
                            width: '32px',
                            height: '32px',
                            borderRadius: '8px',
                            backgroundColor: 'rgba(0,0,0,0.02)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          {item.icon}
                        </div>
                      }
                      title={<span style={{ fontWeight: 500 }}>{item.title}</span>}
                      description={<span style={{ fontSize: '12px' }}>{item.description}</span>}
                    />
                  </List.Item>
                )}
              />
            </Card>
          </Space>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
