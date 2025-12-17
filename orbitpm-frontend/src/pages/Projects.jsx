import React, { useState } from 'react';
import { Button, Tag, Space, Form, Input, Select, message } from 'antd';
import { PlusOutlined, FileSearchOutlined } from '@ant-design/icons';
import ReusableTable from '../components/common/ReusableTable';
import ReusableModal from '../components/common/ReusableModal';

const Projects = () => {
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();
  
  // Mock projects dataset
  const [projectsData, setProjectsData] = useState([
    {
      id: 'proj-1',
      name: 'Alpha Redesign',
      description: ' Nike corporate portal overhaul and Tailwind build.',
      status: 'ACTIVE',
      owner: 'Sarah Jenkins',
      progress: 60,
    },
    {
      id: 'proj-2',
      name: 'Mobile Core UI',
      description: 'Building shared component libraries for iOS/Android.',
      status: 'PLANNING',
      owner: 'Alex Rivera',
      progress: 10,
    },
    {
      id: 'proj-3',
      name: 'Stripe Billings Sync',
      description: 'Integrating recurrent metering and multi-currency billing.',
      status: 'COMPLETED',
      owner: 'John Doe',
      progress: 100,
    },
  ]);

  const columns = [
    {
      title: 'Project Name',
      dataIndex: 'name',
      key: 'name',
      render: (text) => <span style={{ fontWeight: 600, color: '#6366f1' }}>{text}</span>,
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'Manager',
      dataIndex: 'owner',
      key: 'owner',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        let color = 'gold';
        if (status === 'ACTIVE') color = 'processing';
        if (status === 'COMPLETED') color = 'success';
        if (status === 'ON_HOLD') color = 'default';
        return <Tag color={color}>{status}</Tag>;
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space size="middle">
          <a href="#view" onClick={() => message.info(`Viewing details for ${record.name}`)}>View</a>
          <a style={{ color: '#ff4d4f' }} href="#archive" onClick={() => message.warning(`Archived ${record.name}`)}>Archive</a>
        </Space>
      ),
    },
  ];

  const handleCreateProject = (values) => {
    const newProj = {
      id: `proj-${Date.now()}`,
      name: values.name,
      description: values.description,
      status: values.status,
      owner: 'Sarah Jenkins',
      progress: 0,
    };
    setProjectsData([newProj, ...projectsData]);
    message.success(`Project "${values.name}" created successfully!`);
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
            Projects Workspace
          </h1>
          <p style={{ color: '#8c8c8c', margin: '4px 0 0 0' }}>
            Monitor milestones, edit scope boundaries, and bill client projects.
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
          onClick={() => setCollapsed => setModalOpen(true)}
        >
          Create Project
        </Button>
      </div>

      {/* Reusable table implementation */}
      <ReusableTable columns={columns} dataSource={projectsData} />

      {/* Creation Modal Implementation */}
      <ReusableModal
        title="Scaffold a New Project"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        okText="Scaffold Project"
      >
        <Form form={form} layout="vertical" onFinish={handleCreateProject} requiredMark={false}>
          <Form.Item
            name="name"
            label="Project Title"
            rules={[{ required: true, message: 'Please input the project title!' }]}
          >
            <Input placeholder="e.g. Acme Website Overhaul" />
          </Form.Item>

          <Form.Item name="description" label="Scope Description">
            <Input.TextArea placeholder="Outline key milestones and deliverables..." rows={4} />
          </Form.Item>

          <Form.Item
            name="status"
            label="Initial Status"
            rules={[{ required: true, message: 'Please select an initial status!' }]}
            initialValue="PLANNING"
          >
            <Select style={{ width: '100%' }}>
              <Select.Option value="PLANNING">Planning / Scoping</Select.Option>
              <Select.Option value="ACTIVE">Active Work</Select.Option>
              <Select.Option value="ON_HOLD">On Hold</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </ReusableModal>
    </div>
  );
};

export default Projects;
