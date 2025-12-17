import React from 'react';
import { Spin } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';

const LoadingSpinner = ({ tip = 'Loading OrbitPM...', fullScreen = false }) => {
  const antIcon = (
    <LoadingOutlined
      style={{
        fontSize: fullScreen ? 48 : 24,
        color: '#6366f1', // OrbitPM primary indigo
      }}
      spin
    />
  );

  const content = (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: fullScreen ? '100vh' : '150px',
        width: '100%',
        gap: '16px',
      }}
    >
      <Spin indicator={antIcon} />
      {tip && (
        <span
          style={{
            color: '#8c8c8c',
            fontWeight: 500,
            fontSize: fullScreen ? '16px' : '14px',
            fontFamily: "'Outfit', sans-serif",
          }}
        >
          {tip}
        </span>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(250, 250, 250, 0.9)',
          zIndex: 9999,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backdropFilter: 'blur(8px)',
        }}
      >
        {content}
      </div>
    );
  }

  return content;
};

export default LoadingSpinner;
