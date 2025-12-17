import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Form, Input, Button, Alert, Checkbox } from 'antd';
import { MailOutlined, LockOutlined } from '@ant-design/icons';
import { useAuth } from '../context/AuthContext';

const Login = () => {
  const [form] = Form.useForm();
  const { login } = useAuth();
  const navigate = useNavigate();
  
  const [apiError, setApiError] = useState(null);
  const [loading, setLoading] = useState(false);

  const onFinish = async (values) => {
    setLoading(true);
    setApiError(null);
    const result = await login(values.email, values.password);
    setLoading(false);
    
    if (result.success) {
      navigate('/dashboard');
    } else {
      setApiError(result.error);
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
        Sign In to Your Workspace
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
        name="login_form"
        layout="vertical"
        onFinish={onFinish}
        requiredMark={false}
        initialValues={{ remember: true }}
      >
        <Form.Item
          name="email"
          rules={[
            { required: true, message: 'Please input your email!' },
            { type: 'email', message: 'Please input a valid email address!' },
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
          name="password"
          rules={[{ required: true, message: 'Please input your password!' }]}
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

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '24px',
          }}
        >
          <Form.Item name="remember" valuePropName="checked" noStyle>
            <Checkbox style={{ color: '#94a3b8', fontSize: '13px' }}>Remember me</Checkbox>
          </Form.Item>
          <a style={{ color: '#818cf8', fontSize: '13px', fontWeight: 500 }} href="#forgot">
            Forgot password?
          </a>
        </div>

        <Form.Item style={{ marginBottom: '16px' }}>
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
            Sign In
          </Button>
        </Form.Item>
      </Form>

      <div style={{ textAlign: 'center', marginTop: '20px', color: '#94a3b8', fontSize: '14px' }}>
        Don't have an account?{' '}
        <Link to="/register" style={{ color: '#818cf8', fontWeight: 600 }}>
          Create one now
        </Link>
      </div>
    </div>
  );
};

export default Login;
