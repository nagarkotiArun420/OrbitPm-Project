import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Form, Input, Button, Alert, Select, Space, message } from 'antd';
import { MailOutlined, LockOutlined, UserOutlined, PhoneOutlined, TrophyOutlined } from '@ant-design/icons';
import { useAuth } from '../context/AuthContext';

const { Option } = Select;

const Register = () => {
  const [form] = Form.useForm();
  const { register } = useAuth();
  const navigate = useNavigate();

  const [apiError, setApiError] = useState(null);
  const [loading, setLoading] = useState(false);

  const onFinish = async (values) => {
    setLoading(true);
    setApiError(null);
    const result = await register(
      values.email,
      values.password,
      values.full_name,
      values.role,
      values.phone_number
    );
    setLoading(false);

    if (result.success) {
      message.success('Account created successfully! Please sign in.');
      navigate('/login');
    } else {
      // API returns standardized validation or general errors
      const errs = result.error;
      const firstErr = typeof errs === 'string' ? errs : Object.values(errs)[0]?.[0] || 'Registration failed';
      setApiError(firstErr);
    }
  };

  return (
    <div>
      <h2
        style={{
          fontFamily: "'Outfit', sans-serif",
          color: '#ffffff',
          fontSize: '20px',
          fontWeight: 600,
          marginBottom: '20px',
          textAlign: 'center',
        }}
      >
        Create Your Account
      </h2>

      {apiError && (
        <Alert
          message={apiError}
          type="error"
          showIcon
          style={{ marginBottom: '20px', borderRadius: '8px' }}
        />
      )}

      <Form
        form={form}
        name="register_form"
        layout="vertical"
        onFinish={onFinish}
        requiredMark={false}
        initialValues={{ role: 'DEVELOPER' }}
      >
        <Form.Item
          name="full_name"
          rules={[{ required: true, message: 'Please input your full name!' }]}
        >
          <Input
            prefix={<UserOutlined style={{ color: '#94a3b8' }} />}
            placeholder="Full Name"
            size="large"
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: '#ffffff',
              borderRadius: '8px',
            }}
          />
        </Form.Item>

        <Form.Item
          name="email"
          rules={[
            { required: true, message: 'Please input your email!' },
            { type: 'email', message: 'Please input a valid email!' },
          ]}
        >
          <Input
            prefix={<MailOutlined style={{ color: '#94a3b8' }} />}
            placeholder="Work Email"
            size="large"
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: '#ffffff',
              borderRadius: '8px',
            }}
          />
        </Form.Item>

        <Form.Item
          name="role"
          rules={[{ required: true, message: 'Please select your role!' }]}
        >
          <Select
            size="large"
            placeholder="Select Workspace Role"
            style={{
              width: '100%',
            }}
            dropdownStyle={{ zIndex: 10000 }}
          >
            <Option value="DEVELOPER">Developer / Freelancer</Option>
            <Option value="MANAGER">Project Manager / Director</Option>
            <Option value="CLIENT">Client / Guest</Option>
          </Select>
        </Form.Item>

        <Form.Item name="phone_number">
          <Input
            prefix={<PhoneOutlined style={{ color: '#94a3b8' }} />}
            placeholder="Phone Number (Optional)"
            size="large"
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: '#ffffff',
              borderRadius: '8px',
            }}
          />
        </Form.Item>

        <Form.Item
          name="password"
          rules={[
            { required: true, message: 'Please input your password!' },
            { min: 6, message: 'Password must be at least 6 characters!' },
          ]}
        >
          <Input.Password
            prefix={<LockOutlined style={{ color: '#94a3b8' }} />}
            placeholder="Password"
            size="large"
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: '#ffffff',
              borderRadius: '8px',
            }}
          />
        </Form.Item>

        <Form.Item style={{ marginTop: '24px', marginBottom: '16px' }}>
          <Button
            type="primary"
            htmlType="submit"
            size="large"
            block
            loading={loading}
            style={{
              background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
              borderColor: 'transparent',
              height: '46px',
              borderRadius: '8px',
              fontWeight: 600,
              boxShadow: '0 4px 12px rgba(99, 102, 241, 0.2)',
            }}
          >
            Create Free Account
          </Button>
        </Form.Item>
      </Form>

      <div style={{ textAlign: 'center', marginTop: '20px', color: '#94a3b8', fontSize: '14px' }}>
        Already have an account?{' '}
        <Link to="/login" style={{ color: '#818cf8', fontWeight: 600 }}>
          Sign In
        </Link>
      </div>
    </div>
  );
};

export default Register;
