import React from 'react';
import { Table } from 'antd';

const ReusableTable = ({
  columns,
  dataSource,
  loading = false,
  pagination = {},
  onChange,
  rowKey = 'id',
  ...rest
}) => {
  return (
    <Table
      columns={columns}
      dataSource={dataSource}
      loading={loading}
      pagination={{
        showSizeChanger: true,
        showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} records`,
        position: ['bottomRight'],
        defaultPageSize: 10,
        ...pagination,
      }}
      onChange={onChange}
      rowKey={rowKey}
      style={{
        background: 'inherit',
        borderRadius: '8px',
      }}
      {...rest}
    />
  );
};

export default ReusableTable;
