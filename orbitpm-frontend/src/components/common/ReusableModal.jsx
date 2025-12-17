import React from 'react';
import { Modal } from 'antd';

const ReusableModal = ({
  title,
  open,
  onCancel,
  onOk,
  confirmLoading = false,
  children,
  width = 520,
  okText = 'Confirm',
  cancelText = 'Cancel',
  ...rest
}) => {
  return (
    <Modal
      title={
        <div style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 600, fontSize: '18px' }}>
          {title}
        </div>
      }
      open={open}
      onCancel={onCancel}
      onOk={onOk}
      confirmLoading={confirmLoading}
      width={width}
      okText={okText}
      cancelText={cancelText}
      okButtonProps={{
        style: {
          backgroundColor: '#6366f1', // OrbitPM Primary
          borderColor: '#6366f1',
        },
      }}
      destroyOnClose
      {...rest}
    >
      <div style={{ padding: '8px 0', minHeight: '60px' }}>{children}</div>
    </Modal>
  );
};

export default ReusableModal;
