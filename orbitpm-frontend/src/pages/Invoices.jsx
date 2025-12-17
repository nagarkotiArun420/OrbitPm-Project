import React, { useState } from 'react';
import { Button, Tag, Space, Form, Input, Select, InputNumber, DatePicker, message } from 'antd';
import { PlusOutlined, DollarOutlined } from '@ant-design/icons';
import ReusableTable from '../components/common/ReusableTable';
import ReusableModal from '../components/common/ReusableModal';

const Invoices = () => {
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  // Mock invoices dataset
  const [invoicesData, setInvoicesData] = useState([
    {
      id: 'inv-1001',
      project: 'Alpha Redesign',
      client: 'John Doe',
      amount: 4500.00,
      status: 'PAID',
      dueDate: '2026-05-15',
    },
    {
      id: 'inv-1002',
      project: 'Mobile Core UI',
      client: 'Alex Rivera',
      amount: 2500.00,
      status: 'UNPAID',
      dueDate: '2026-06-01',
    },
    {
      id: 'inv-1003',
      project: 'Stripe Billings Sync',
      client: 'John Doe',
      amount: 7250.00,
      status: 'OVERDUE',
      dueDate: '2026-04-30',
    },
  ]);

  const columns = [
    {
      title: 'Invoice ID',
      dataIndex: 'id',
      key: 'id',
      render: (text) => <span style={{ fontWeight: 600 }}>{text}</span>,
    },
    {
      title: 'Associated Project',
      dataIndex: 'project',
      key: 'project',
    },
    {
      title: 'Client Partner',
      dataIndex: 'client',
      key: 'client',
    },
    {
      title: 'Billing Amount',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount) => `$${amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}`,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        let color = 'default';
        if (status === 'PAID') color = 'success';
        if (status === 'UNPAID') color = 'processing';
        if (status === 'OVERDUE') color = 'error';
        return <Tag color={color}>{status}</Tag>;
      },
    },
    {
      title: 'Due Date',
      dataIndex: 'dueDate',
      key: 'dueDate',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space size="middle">
          <a href="#send" onClick={() => message.info(`Dispatched invoice ${record.id} to client!`)}>Dispatch</a>
          {record.status !== 'PAID' && (
            <a style={{ color: '#52c41a' }} href="#pay" onClick={() => message.success(`Marked invoice ${record.id} as Paid!`)}>Mark Paid</a>
          )}
        </Space>
      ),
    },
  ];

  const handleGenerateInvoice = (values) => {
    const newInvoice = {
      id: `inv-${Math.floor(1000 + Math.random() * 9000)}`,
      project: values.project,
      client: values.client,
      amount: values.amount,
      status: 'UNPAID',
      dueDate: values.dueDate ? values.dueDate.format('YYYY-MM-DD') : '2026-06-15',
    };
    setInvoicesData([newInvoice, ...invoicesData]);
    message.success(`Invoice "${newInvoice.id}" issued successfully!`);
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
            Billing Ledger
          </h1>
          <p style={{ color: '#8c8c8c', margin: '4px 0 0 0' }}>
            Generate professional client invoices, log payments, and track outstanding ledger balances.
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
          Issue Invoice
        </Button>
      </div>

      <ReusableTable columns={columns} dataSource={invoicesData} />

      <ReusableModal
        title="Issue New Client Invoice"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        okText="Issue Invoice"
      >
        <Form form={form} layout="vertical" onFinish={handleGenerateInvoice} requiredMark={false}>
          <Form.Item
            name="project"
            label="Associated Project"
            rules={[{ required: true, message: 'Please select a project!' }]}
            initialValue="Alpha Redesign"
          >
            <Select style={{ width: '100%' }}>
              <Select.Option value="Alpha Redesign">Alpha Redesign</Select.Option>
              <Select.Option value="Mobile Core UI">Mobile Core UI</Select.Option>
              <Select.Option value="Stripe Billings Sync">Stripe Billings Sync</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="client"
            label="Client Partner"
            rules={[{ required: true, message: 'Please specify the client name!' }]}
          >
            <Input placeholder="e.g. Alexander Rivera" />
          </Form.Item>

          <Form.Item
            name="amount"
            label="Billing Amount ($ USD)"
            rules={[{ required: true, message: 'Please input a billing amount!' }]}
          >
            <InputNumber
              prefix={<DollarOutlined />}
              style={{ width: '100%' }}
              min={0}
              placeholder="e.g. 5000.00"
            />
          </Form.Item>

          <Form.Item
            name="dueDate"
            label="Payment Due Date"
            rules={[{ required: true, message: 'Please select a payment due date!' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </ReusableModal>
    </div>
  );
};

export default Invoices;
