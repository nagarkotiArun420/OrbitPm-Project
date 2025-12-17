import React from 'react';
import { Outlet, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Card, Space } from 'antd';
import { RocketOutlined } from '@ant-design/icons';

const AuthLayout = () => {
  const { user } = useAuth();

  // If user is already authenticated, directly bypass and redirect to dashboard
  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #311042 100%)',
        position: 'relative',
        overflow: 'hidden',
        padding: '24px',
      }}
    >
      {/* Decorative Blur Spheres for Premium Aesthetics */}
      <div
        style={{
          position: 'absolute',
          width: '400px',
          height: '400px',
          background: 'radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, rgba(0,0,0,0) 70%)',
          top: '-10%',
          right: '5%',
          zIndex: 1,
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: '500px',
          height: '500px',
          background: 'radial-gradient(circle, rgba(168, 85, 247, 0.1) 0%, rgba(0,0,0,0) 70%)',
          bottom: '-10%',
          left: '5%',
          zIndex: 1,
        }}
      />

      <Card
        bordered={false}
        className="glass-card smooth-transition"
        style={{
          width: '100%',
          maxWidth: '450px',
          zIndex: 2,
          borderRadius: '16px',
          background: 'rgba(255, 255, 255, 0.03)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.3)',
          backdropFilter: 'blur(16px)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <Space direction="vertical" size="small">
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '12px',
                background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 8px 16px rgba(99, 102, 241, 0.3)',
              }}
            >
              <RocketOutlined style={{ fontSize: '22px', color: '#ffffff' }} />
            </div>
            <h1
              style={{
                margin: '12px 0 4px 0',
                color: '#ffffff',
                fontFamily: "'Outfit', sans-serif",
                fontWeight: 700,
                fontSize: '28px',
                letterSpacing: '-0.5px',
              }}
            >
              Orbit<span style={{ color: '#818cf8' }}>PM</span>
            </h1>
            <p style={{ margin: 0, color: '#94a3b8', fontSize: '14px' }}>
              Project & Workflow management for modern digital agencies
            </p>
          </Space>
        </div>

        <Outlet />
      </Card>
    </div>
  );
};

export default AuthLayout;
