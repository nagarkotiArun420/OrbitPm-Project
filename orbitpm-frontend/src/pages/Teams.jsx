import React, { useState } from 'react';
import { Button, Tag, Space, Form, Input, Select, message } from 'antd';
import { PlusOutlined, MailOutlined } from '@ant-design/icons';
import ReusableTable from '../components/common/ReusableTable';
import ReusableModal from '../components/common/ReusableModal';

const Teams = () => {
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  // Mock teams dataset
  const [teamsData, setTeamsData] = useState([
    {
      id: 'team-1',
      name: 'Sarah Jenkins',
      email: 'sarah.j@orbitpm.com',
      role: 'MANAGER',
      status: 'ACTIVE',
    },
    {
      id: 'team-2',
      name: 'Alex Rivera',
      email: 'alex.r@orbitpm.com',
      role: 'DEVELOPER',
      status: 'ACTIVE',
    },
    {
      id: 'team-3',
      name: 'John Doe',
      email: 'john.doe@client.com',
      role: 'CLIENT',
      status: 'INACTIVE',
    },
  ]);

  const columns = [
    {
      title: 'Full Name',
      dataIndex: 'name',
      key: 'name',
      render: (text) => <span style={{ fontWeight: 600 }}>{text}</span>,
    },
    {
      title: 'Email Address',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: 'Workspace Role',
      dataIndex: 'role',
      key: 'role',
      render: (role) => {
        let color = 'default';
        if (role === 'ADMIN') color = 'magenta';
        if (role === 'MANAGER') color = 'purple';
        if (role === 'DEVELOPER') color = 'indigo';
        if (role === 'CLIENT') color = 'orange';
        return <Tag color={color}>{role}</Tag>;
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'ACTIVE' ? 'success' : 'default'}>{status}</Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space size="middle">
          <a href="#ping" onClick={() => message.info(`Notified ${record.name}`)}>Notify</a>
          <a style={{ color: '#ff4d4f' }} href="#deactivate" onClick={() => message.warning(`Suspended member ${record.name}`)}>Deactivate</a>
        </Space>
      ),
    },
  ];

  const handleInviteMember = (values) => {
    const newMember = {
      id: `team-${Date.now()}`,
      name: values.name,
      email: values.email,
      role: values.role,
      status: 'ACTIVE',
    };
    setTeamsData([...teamsData, newMember]);
    message.success(`Invitation sent to ${values.email}!`);
    setModalOpen(false);
    form.resetFields();
  };

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '28px',
        }}
      >
        <div>
          <h1 style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 700, fontSize: '26px', margin: 0 }}>
            Team Roster
          </h1>
          <p style={{ color: '#8c8c8c', margin: '4px 0 0 0' }}>
            Invite designers, allocate project permissions, and organize workflow roles.
          </p>
        </div>

        <Button
          type="primary"
          icon={<PlusOutlined />}
          size="large"
          style={{
            backgroundColor: '#6366f1',
            borderColor: '#6366f1',
            borderRadius: '6px',
          }}
          onClick={() => setModalOpen(true)}
        >
          Invite Member
        </Button>
      </div>

      <ReusableTable columns={columns} dataSource={teamsData} />

      <ReusableModal
        title="Invite Workspace Member"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        okText="Send Invitation"
      >
        <Form form={form} layout="vertical" onFinish={handleInviteMember} requiredMark={false}>
          <Form.Item
            name="name"
            label="Full Name"
            rules={[{ required: true, message: 'Please input their full name!' }]}
          >
            <Input placeholder="e.g. Liam Henderson" />
          </Form.Item>

          <Form.Item
            name="email"
            label="Work Email Address"
            rules={[
              { required: true, message: 'Please input their email!' },
              { type: 'email', message: 'Please input a valid email!' },
            ]}
          >
            <Input prefix={<MailOutlined />} placeholder="e.g. liam@agency.com" />
          </Form.Item>

          <Form.Item
            name="role"
            label="Workspace Permission Role"
            rules={[{ required: true, message: 'Please choose a role!' }]}
            initialValue="DEVELOPER"
          >
            <Select style={{ width: '100%' }}>
              <Select.Option value="DEVELOPER">Developer / Freelancer</Select.Option>
              <Select.Option value="MANAGER">Project Manager</Select.Option>
              <Select.Option value="CLIENT">Client Partner</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </ReusableModal>
    </div>
  );
};

export default Teams;
