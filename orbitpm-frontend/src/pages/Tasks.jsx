import React, { useState } from 'react';
import { Button, Tag, Space, Form, Input, Select, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import ReusableTable from '../components/common/ReusableTable';
import ReusableModal from '../components/common/ReusableModal';

const Tasks = () => {
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  // Mock tasks dataset
  const [tasksData, setTasksData] = useState([
    {
      id: 'task-1',
      title: 'Design high-fidelity client views',
      project: 'Alpha Redesign',
      priority: 'HIGH',
      status: 'IN_PROGRESS',
      assignee: 'Sarah Jenkins',
    },
    {
      id: 'task-2',
      title: 'Configure simpleJWT settings module',
      project: 'OrbitPM Platform',
      priority: 'CRITICAL',
      status: 'DONE',
      assignee: 'John Doe',
    },
    {
      id: 'task-3',
      title: 'Audit database performance markers',
      project: 'Mobile Core UI',
      priority: 'LOW',
      status: 'TODO',
      assignee: 'Alex Rivera',
    },
  ]);

  const columns = [
    {
      title: 'Task Title',
      dataIndex: 'title',
      key: 'title',
      render: (text) => <span style={{ fontWeight: 500 }}>{text}</span>,
    },
    {
      title: 'Project',
      dataIndex: 'project',
      key: 'project',
    },
    {
      title: 'Assignee',
      dataIndex: 'assignee',
      key: 'assignee',
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
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space size="middle">
          <a href="#complete" onClick={() => message.success(`Marked "${record.title}" as complete!`)}>Complete</a>
          <a style={{ color: '#ff4d4f' }} href="#delete" onClick={() => message.warning(`Deleted task "${record.title}"`)}>Delete</a>
        </Space>
      ),
    },
  ];

  const handleCreateTask = (values) => {
    const newTask = {
      id: `task-${Date.now()}`,
      title: values.title,
      project: values.project,
      priority: values.priority,
      status: 'TODO',
      assignee: 'Sarah Jenkins',
    };
    setTasksData([newTask, ...tasksData]);
    message.success(`Task "${values.title}" queued successfully!`);
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
            Tasks Backlog
          </h1>
          <p style={{ color: '#8c8c8c', margin: '4px 0 0 0' }}>
            Coordinate delivery velocities, allocate developer resources, and track progress.
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
          Add Task
        </Button>
      </div>

      <ReusableTable columns={columns} dataSource={tasksData} />

      <ReusableModal
        title="Add Task to Backlog"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        okText="Queue Task"
      >
        <Form form={form} layout="vertical" onFinish={handleCreateTask} requiredMark={false}>
          <Form.Item
            name="title"
            label="Task Description"
            rules={[{ required: true, message: 'Please input the task title!' }]}
          >
            <Input placeholder="e.g. Implement auth route guards" />
          </Form.Item>

          <Form.Item
            name="project"
            label="Associated Project"
            rules={[{ required: true, message: 'Please select a project!' }]}
            initialValue="Alpha Redesign"
          >
            <Select style={{ width: '100%' }}>
              <Select.Option value="Alpha Redesign">Alpha Redesign</Select.Option>
              <Select.Option value="OrbitPM Platform">OrbitPM Platform</Select.Option>
              <Select.Option value="Mobile Core UI">Mobile Core UI</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="priority"
            label="Severity Priority"
            rules={[{ required: true, message: 'Please choose task priority!' }]}
            initialValue="MEDIUM"
          >
            <Select style={{ width: '100%' }}>
              <Select.Option value="LOW">Low</Select.Option>
              <Select.Option value="MEDIUM">Medium</Select.Option>
              <Select.Option value="HIGH">High</Select.Option>
              <Select.Option value="CRITICAL">Critical</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </ReusableModal>
    </div>
  );
};

export default Tasks;
