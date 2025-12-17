import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Result, Button } from 'antd';

const NotFound = () => {
  const navigate = useNavigate();

  return (
    <div
      style={{
        height: '80vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Result
        status="404"
        title={
          <span style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 700, fontSize: '48px' }}>
            404
          </span>
        }
        subTitle={
          <span style={{ color: '#8c8c8c', fontSize: '16px' }}>
            Sorry, the page you visited does not exist in your workspace.
          </span>
        }
        extra={
          <Button
            type="primary"
            size="large"
            style={{
              backgroundColor: '#6366f1',
              borderColor: '#6366f1',
              borderRadius: '6px',
            }}
            onClick={() => navigate('/dashboard')}
          >
            Return to Dashboard
          </Button>
        }
      />
    </div>
  );
};

export default NotFound;
