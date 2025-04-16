import React from 'react';
import { Card, Button, Tooltip, Modal } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import EnhancedMarkdown from './EnhancedMarkdown';
import '../styles/MarkdownStyles.css';

interface ReportViewerProps {
  report: string;
  issuingUnit?: string;
  reportDate?: string;
  onDownload: () => void;
  visible?: boolean;
  onClose?: () => void;
}

const ReportViewer: React.FC<ReportViewerProps> = ({
  report,
  issuingUnit,
  reportDate,
  onDownload,
  visible = true,
  onClose
}) => {
  const reportContent = (
    <div className="report-content markdown-content">
      <EnhancedMarkdown>{report}</EnhancedMarkdown>
    </div>
  );

  return (
    <Modal
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>防汛应急报告</span>
          <div>
            {issuingUnit && <span style={{ marginRight: 16 }}>发布单位: {issuingUnit}</span>}
            {reportDate && <span>报告日期: {reportDate}</span>}
          </div>
        </div>
      }
      open={visible}
      onCancel={onClose}
      width={800}
      footer={[
        <Button key="download" type="primary" icon={<DownloadOutlined />} onClick={onDownload}>
          下载报告
        </Button>,
        <Button key="close" onClick={onClose}>
          关闭
        </Button>
      ]}
    >
      {reportContent}
    </Modal>
  );
};

export default ReportViewer; 