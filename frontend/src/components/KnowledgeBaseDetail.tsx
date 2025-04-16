import React, { useState, useEffect, useRef } from 'react';
import { Card, Tabs, Button, Input, Table, Tag, Modal, message, Tooltip, List, Typography, Collapse, Progress, Space, Avatar, Spin, Menu, Empty } from 'antd';
import { 
  EyeOutlined, 
  UploadOutlined, 
  FileTextOutlined, 
  HistoryOutlined, 
  DeleteOutlined, 
  DownloadOutlined, 
  CaretRightOutlined, 
  ConsoleSqlOutlined, 
  SendOutlined, 
  RobotOutlined, 
  UserOutlined, 
  SettingOutlined, 
  PlusOutlined, 
  DatabaseOutlined, 
  ApartmentOutlined, 
  MessageOutlined, 
  ClearOutlined, 
  SyncOutlined,
  CloudDownloadOutlined,
  ArrowLeftOutlined,
  LoadingOutlined
} from '@ant-design/icons';
import TextArea from 'antd/lib/input/TextArea';
import ReactMarkdown from 'react-markdown';
import IndexManager from './IndexManager';
import ReportViewer from './ReportViewer';
import EnhancedMarkdown from './EnhancedMarkdown';
import '../styles/MarkdownStyles.css';
import './KnowledgeBaseDetail.css';

interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  createdAt: string;
}

interface ExtractedContent {
  url: string;
  title: string;
  content: string;
  extracted_time: string;
  structured_data: {
    rainfall: any[];
    water_condition: any[];
    disaster_impact: any[];
    measures: any[];
    raw_text: string;
  };
}

interface ReportHistory {
  id: string;
  query: string;
  report: string;
  created_at: string;
  issuing_unit?: string;
  report_date?: string;
}

interface UrlProgressItem {
  url: string;
  status: string; // 'pending' | 'extracting' | 'completed' | 'failed' | 'error'
  progress: number;
  message?: string;
}

interface Message {
  role: string; // "user" | "assistant"
  content: string;
  timestamp: string;
}

interface ChatHistory {
  id: string;
  title: string;
  messages: Message[];
  messages_count?: number;
  created_at: string;
  updated_at: string;
  kb_id: string;
}

interface Props {
  knowledgeBase: KnowledgeBase;
  onBack: () => void;
  onError?: (error: string) => void;
}

const KnowledgeBaseDetail: React.FC<Props> = ({ knowledgeBase, onBack, onError }) => {
  const [activeTab, setActiveTab] = useState('contents');
  const [urls, setUrls] = useState('');
  const [extractLoading, setExtractLoading] = useState(false);
  const [extractProgress, setExtractProgress] = useState<{
    current: number, 
    total: number, 
    currentUrl: string, 
    status: string,
    taskId?: string,
    urlProgress?: UrlProgressItem[]
  } | null>(null);
  const [contents, setContents] = useState<ExtractedContent[]>([]);
  const [contentsLoading, setContentsLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState<string | null>(null);
  const [reportQuery, setReportQuery] = useState('');
  const [issuingUnit, setIssuingUnit] = useState('');
  const [reportDate, setReportDate] = useState('');
  const [reportLoading, setReportLoading] = useState(false);
  const [generatedReport, setGeneratedReport] = useState('');
  const [showReportViewer, setShowReportViewer] = useState(false);
  const [reportHistory, setReportHistory] = useState<ReportHistory[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showLogConsole, setShowLogConsole] = useState(false);
  const [logMessages, setLogMessages] = useState<string[]>([]);
  const [logPolling, setLogPolling] = useState<boolean>(false);
  const [thinkingDots, setThinkingDots] = useState<string>('');
  const logRef = useRef<HTMLDivElement>(null);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [currentChatHistory, setCurrentChatHistory] = useState<Message[]>([]);
  const [allChatHistories, setAllChatHistories] = useState<ChatHistory[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [showChatHistory, setShowChatHistory] = useState(false);
  const [chatHistoryLoading, setChatHistoryLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const [showReportModal, setShowReportModal] = useState(false);
  const [reportModalQuery, setReportModalQuery] = useState('');
  const [reportModalUnit, setReportModalUnit] = useState('');
  const [reportModalDate, setReportModalDate] = useState('');

  useEffect(() => {
    const loadData = async () => {
      setPageLoading(true);
      setLoadError(null);
      try {
        await Promise.all([
          fetchContents(),
          fetchReportHistory()
        ]);
      } catch (error) {
        console.error('加载知识库数据出错:', error);
        const errorMessage = error instanceof Error ? error.message : '未知错误';
        setLoadError(`加载知识库数据失败: ${errorMessage}`);
        if (onError) {
          onError(`加载知识库数据失败: ${errorMessage}`);
        }
      } finally {
        setPageLoading(false);
      }
    };
    
    loadData();
  }, [knowledgeBase.id, onError]);

  useEffect(() => {
    let intervalId: number;
    if (logPolling) {
      intervalId = window.setInterval(() => {
        setThinkingDots(prev => {
          if (prev.length >= 3) return '';
          return prev + '·';
        });
      }, 600);
    }
    return () => {
      if (intervalId) window.clearInterval(intervalId);
    };
  }, [logPolling]);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logMessages]);

  useEffect(() => {
    if (activeTab === 'chat') {
      fetchChatHistory();
    }
  }, [activeTab, knowledgeBase.id]);
  
  useEffect(() => {
    // 聊天结束后滚动到底部
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [currentChatHistory]);

  const fetchContents = async () => {
    setContentsLoading(true);
    try {
      const response = await fetch(`/api/knowledge-base/${knowledgeBase.id}/contents`);
      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success') {
          setContents(result.data || []);
        } else {
          message.warning(result.message || '获取内容返回了空数据');
          setContents([]);
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        message.error(errorData.detail || '获取内容失败');
        setContents([]);
      }
    } catch (error) {
      console.error('获取知识库内容出错:', error);
      message.error('获取内容失败，请检查网络连接');
      setContents([]);
    } finally {
      setContentsLoading(false);
    }
  };

  const fetchReportHistory = async () => {
    setHistoryLoading(true);
    try {
      const response = await fetch(`/api/knowledge-base/${knowledgeBase.id}/reports`);
      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success') {
          // 验证返回的数据格式
          if (Array.isArray(result.data)) {
            // 过滤掉格式无效的报告
            const validReports = result.data.filter((report: any) => {
              const isValid = report && 
                typeof report === 'object' && 
                report.id && 
                report.report && 
                typeof report.report === 'string';
              
              if (!isValid) {
                console.warn('发现无效报告格式:', report);
              }
              return isValid;
            });
            
            setReportHistory(validReports);
            
            // 记录过滤情况
            if (validReports.length < result.data.length) {
              console.warn(`从${result.data.length}个报告中过滤掉了${result.data.length - validReports.length}个无效报告`);
            }
          } else {
            console.error('API返回的报告数据不是数组格式:', result.data);
            message.warning('获取报告历史返回了无效格式的数据');
            setReportHistory([]);
          }
        } else {
          message.warning(result.message || '获取报告历史返回了空数据');
          setReportHistory([]);
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        message.error(errorData.detail || '获取报告历史失败');
        setReportHistory([]);
      }
    } catch (error) {
      console.error('获取报告历史记录出错:', error);
      message.error('获取报告历史记录失败，请检查网络连接');
      setReportHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  const addLogMessage = (message: string) => {
    setLogMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`]);
  };

  const handleExtract = async () => {
    if (!urls.trim()) {
      message.error('请输入要提取的链接');
      return;
    }

    const urlList = urls.split('\n').filter(url => url.trim());
    if (urlList.length === 0) {
      message.error('请输入有效的链接');
      return;
    }

    setExtractLoading(true);
    setLogMessages([]);
    
    // 初始化每个URL的进度状态
    const initialUrlProgress: UrlProgressItem[] = urlList.map(url => ({
      url,
      status: 'pending',
      progress: 0,
      message: '等待处理'
    }));
    
    setExtractProgress({ 
      current: 0, 
      total: urlList.length, 
      currentUrl: '', 
      status: '准备提取...',
      urlProgress: initialUrlProgress
    });
    
    addLogMessage(`开始提取 ${urlList.length} 个链接...`);
    
    try {
      const response = await fetch('/extract', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          urls: urlList,
          db_name: knowledgeBase.id,
        }),
      });

      if (response.ok) {
        // 获取任务ID
        const result = await response.json();
        if (result.status === 'success' && result.task_id) {
          // 更新进度状态，包含任务ID
          addLogMessage(`任务已启动，ID: ${result.task_id}`);
          
          setExtractProgress(prev => ({
            ...prev!,
            taskId: result.task_id,
            status: '任务已启动'
          }));
          
          // 开始轮询进度
          pollExtractProgress(result.task_id, urlList);
          
          message.success('链接提取任务已启动');
        } else if (result.status === 'success') {
          // 兼容旧版API，没有任务ID的情况
          message.success('链接提取成功');
          setUrls('');
          fetchContents();
          // 移除自动构建索引
          // await buildIndex();
          message.info('文本已提取完成，如需使用向量搜索功能，请手动点击"构建索引"按钮');
          setExtractLoading(false);
          setExtractProgress(null);
        } else {
          message.error(result.detail || '提取失败，请检查链接格式');
          setExtractLoading(false);
          setExtractProgress(null);
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        message.error(errorData.detail || `提取失败(${response.status})`);
        setExtractLoading(false);
        setExtractProgress(null);
      }
    } catch (error) {
      console.error('链接提取出错:', error);
      message.error('提取失败，请检查网络连接');
      setExtractLoading(false);
      setExtractProgress(null);
    }
  };

  const fetchBackendLogs = async (taskId: string) => {
    try {
      const response = await fetch(`/extract/logs/${taskId}`);
      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success' && result.data) {
          // 将后端日志转换为前端显示格式，去除文件路径等敏感信息
          const processedLogs = result.data.map((log: string) => {
            // 提取时间和日志级别
            const match = log.match(/(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}.\d+)\s+\|\s+(\w+)\s+\|\s+(.+)/);
            if (match) {
              const [_, timestamp, level, message] = match;
              // 移除文件路径和行号
              const cleanMessage = message.replace(/\S+:\S+:\d+(\s+)?-(\s+)?/, '');
              return `[${level}] ${cleanMessage}`;
            }
            return log;
          });
          setLogMessages(processedLogs);
        }
      }
    } catch (error) {
      console.error('获取后端日志失败:', error);
    }
  };

  const pollExtractProgress = async (taskId: string, urlList: string[]) => {
    let completed = false;
    let pollTimer: number | null = null;
    
    // 开启日志轮询
    setLogPolling(true);
    
    const checkProgress = async () => {
      if (completed) {
        return;
      }
      
      try {
        // 获取任务进度
        const response = await fetch(`/extract/progress/${taskId}`);
        
        // 同时获取最新日志
        await fetchBackendLogs(taskId);
        
        if (response.ok) {
          const progress = await response.json();
          
          // 更新URL进度
          if (extractProgress?.urlProgress) {
            const updatedUrlProgress = [...extractProgress.urlProgress];
            
            // 检查是否已完成
            const isCompleted = progress.status === '完成' || 
                                progress.status === 'completed' || 
                                progress.status.toLowerCase() === 'finished' ||
                                progress.status.toLowerCase() === 'complete';
            
            // 检查是否失败
            const isFailed = progress.status === '失败' || 
                             progress.status === 'failed' || 
                             progress.status.toLowerCase() === 'failed' ||
                             progress.status.toLowerCase() === 'error';
            
            // 当前处理的URL
            if (progress.current_url && progress.current > 0 && progress.current <= updatedUrlProgress.length) {
              const currentIndex = progress.current - 1;
              
              // 更新之前的URL为已完成
              for (let i = 0; i < currentIndex; i++) {
                if (updatedUrlProgress[i].status !== 'completed' && 
                    updatedUrlProgress[i].status !== 'failed' &&
                    updatedUrlProgress[i].status !== 'error') {
                  updatedUrlProgress[i].status = 'completed';
                  updatedUrlProgress[i].progress = 100;
                  updatedUrlProgress[i].message = '提取完成';
                  addLogMessage(`链接 "${updatedUrlProgress[i].url}" 提取完成`);
                }
              }
              
              // 更新当前URL为提取中
              if (updatedUrlProgress[currentIndex].status === 'pending') {
                updatedUrlProgress[currentIndex].status = 'extracting';
                updatedUrlProgress[currentIndex].message = '正在提取';
                addLogMessage(`开始提取链接 "${updatedUrlProgress[currentIndex].url}"`);
              }
              
              // 更新当前URL的进度（使用更精细的进度指示）
              updatedUrlProgress[currentIndex].progress = 50; // 简化处理，提取中设为50%
            }
            
            // 如果已完成，更新所有URL为已完成
            if (isCompleted) {
              for (let i = 0; i < updatedUrlProgress.length; i++) {
                if (updatedUrlProgress[i].status !== 'completed') {
                  updatedUrlProgress[i].status = 'completed';
                  updatedUrlProgress[i].progress = 100;
                  updatedUrlProgress[i].message = '提取完成';
                }
              }
              
              // 确保总进度显示为完成
              progress.current = updatedUrlProgress.length;
            }
            
            // 如果失败，更新未完成的URL为失败
            if (isFailed) {
              for (let i = progress.current; i < updatedUrlProgress.length; i++) {
                if (updatedUrlProgress[i].status !== 'completed') {
                  updatedUrlProgress[i].status = 'failed';
                  updatedUrlProgress[i].progress = 0;
                  updatedUrlProgress[i].message = '提取失败';
                }
              }
            }
            
            // 更新界面显示的进度
            setExtractProgress(prev => ({
              ...prev!,
              current: progress.current,
              total: progress.total,
              currentUrl: progress.current_url || '',
              status: progress.status,
              urlProgress: updatedUrlProgress
            }));
          }
          
          addLogMessage(`进度更新: ${progress.current}/${progress.total}, 状态: ${progress.status}`);
          
          // 任务完成条件判断
          if (progress.status === '完成' || 
              progress.status === 'completed' || 
              progress.status.toLowerCase() === 'finished' ||
              progress.status.toLowerCase() === 'complete') {
            completed = true;
            setExtractLoading(false);
            setLogPolling(false);
            
            // 更新所有URL为已完成
            if (extractProgress?.urlProgress) {
              const finalUrlProgress = extractProgress.urlProgress.map(item => ({
                ...item,
                status: 'completed',
                progress: 100,
                message: '提取完成'
              }));
              
              setExtractProgress(prev => ({
                ...prev!,
                current: urlList.length,
                total: urlList.length,
                urlProgress: finalUrlProgress
              }));
            }
            
            addLogMessage('所有链接提取完成');
            
            // 刷新内容列表
            fetchContents();
            message.success('链接提取完成');
            // 添加手动构建索引的提示
            message.info('如需使用向量搜索功能，请手动点击"构建索引"按钮');
            setUrls('');
            
            // 清除定时器
            if (pollTimer) {
              clearTimeout(pollTimer);
              pollTimer = null;
            }
          } else if (progress.status === '失败' || 
                     progress.status === 'failed' || 
                     progress.status.toLowerCase() === 'failed' ||
                     progress.status.toLowerCase() === 'error') {
            completed = true;
            setExtractLoading(false);
            setLogPolling(false);
            
            // 更新所有未完成的URL为失败
            if (extractProgress?.urlProgress) {
              const failedUrlProgress = [...extractProgress.urlProgress];
              failedUrlProgress.forEach((item, index) => {
                if (index >= progress.current) {
                  item.status = 'failed';
                  item.message = '提取失败';
                  addLogMessage(`链接 "${item.url}" 提取失败`);
                }
              });
              
              setExtractProgress(prev => ({
                ...prev!,
                urlProgress: failedUrlProgress
              }));
            }
            
            message.error(`提取失败: ${progress.error || '未知错误'}`);
            addLogMessage(`任务失败: ${progress.error || '未知错误'}`);
            
            // 清除定时器
            if (pollTimer) {
              clearTimeout(pollTimer);
              pollTimer = null;
            }
          } else {
            // 继续轮询
            pollTimer = setTimeout(checkProgress, 1000);
          }
        } else {
          console.warn(`无法获取提取进度(${response.status})，将重试`);
          pollTimer = setTimeout(checkProgress, 2000); // 失败后增加等待时间
        }
      } catch (error) {
        console.error('获取提取进度出错:', error);
        pollTimer = setTimeout(checkProgress, 2000); // 出错后增加等待时间
      }
    };
    
    // 立即开始第一次检查
    checkProgress();
    
    // 组件卸载时清理定时器
    return () => {
      if (pollTimer) {
        clearTimeout(pollTimer);
      }
      setLogPolling(false);
    };
  };

  const buildIndex = async (indexId?: string) => {
    try {
      const response = await fetch(`/api/knowledge-base/${knowledgeBase.id}/build-index`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          kb_id: knowledgeBase.id,
          index_id: indexId
        }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success') {
          message.success(indexId ? '索引激活成功' : '索引构建成功');
        } else if (result.status === 'warning') {
          message.warning(result.message || '索引构建完成，但有警告');
        } else {
          message.error(result.message || '索引构建失败');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        message.error(errorData.detail || `索引构建失败(${response.status})`);
      }
    } catch (error) {
      console.error('索引操作出错:', error);
      message.error('索引操作失败，请稍后重试');
    }
  };

  const fetchChatHistory = async () => {
    setChatHistoryLoading(true);
    try {
      const response = await fetch(`/api/knowledge-base/${knowledgeBase.id}/chat-history`);
      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success') {
          setAllChatHistories(result.data || []);
        }
      }
    } catch (error) {
      console.error('获取聊天历史失败:', error);
    } finally {
      setChatHistoryLoading(false);
    }
  };
  
  const loadChatHistory = async (chatId: string) => {
    try {
      const response = await fetch(`/api/knowledge-base/${knowledgeBase.id}/chat-history/${chatId}`);
      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success' && result.data.messages) {
          setCurrentChatHistory(result.data.messages);
          setCurrentChatId(chatId);
        }
      }
    } catch (error) {
      console.error('加载聊天历史详情失败:', error);
      message.error('无法加载聊天记录');
    }
  };
  
  const saveChatHistory = async () => {
    if (currentChatHistory.length === 0) return;
    
    try {
      // 创建或更新聊天历史
      const firstUserMessage = currentChatHistory.find(msg => msg.role === 'user')?.content || '新对话';
      const title = firstUserMessage.length > 30 ? `${firstUserMessage.substring(0, 30)}...` : firstUserMessage;
      
      const chatData: ChatHistory = {
        id: currentChatId || '',
        title,
        messages: currentChatHistory,
        created_at: currentChatId ? '' : new Date().toISOString(),
        updated_at: new Date().toISOString(),
        kb_id: knowledgeBase.id
      };
      
      const response = await fetch(`/api/knowledge-base/${knowledgeBase.id}/chat-history`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(chatData),
      });
      
      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success' && result.data.id) {
          setCurrentChatId(result.data.id);
          fetchChatHistory();
        }
      }
    } catch (error) {
      console.error('保存聊天历史失败:', error);
    }
  };
  
  const deleteChatHistory = async (chatId: string) => {
    try {
      const response = await fetch(`/api/knowledge-base/${knowledgeBase.id}/chat-history/${chatId}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        message.success('聊天记录已删除');
        fetchChatHistory();
        
        // 如果删除的是当前聊天，则清空当前聊天
        if (chatId === currentChatId) {
          setCurrentChatHistory([]);
          setCurrentChatId(null);
        }
      }
    } catch (error) {
      console.error('删除聊天历史失败:', error);
      message.error('删除聊天记录失败');
    }
  };
  
  const handleSendMessage = async () => {
    if (!chatInput.trim()) {
      message.warning('请输入消息内容');
      return;
    }
    
    // 添加用户消息到聊天历史
    const userMessage: Message = {
      role: 'user',
      content: chatInput,
      timestamp: new Date().toISOString()
    };
    
    setCurrentChatHistory(prev => [...prev, userMessage]);
    setChatLoading(true);
    setChatInput('');
    
    try {
      // 调用聊天API
      const response = await fetch(`/api/knowledge-base/${knowledgeBase.id}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: chatInput,
          kb_id: knowledgeBase.id,
          k: 5,
          chat_history: currentChatHistory.slice(-10) // 只发送最近10条对话记录
        }),
      });
      
      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success') {
          // 如果是报告生成请求
          if (result.is_report) {
            // 添加通知
            message.success('报告生成成功');
            
            // 设置报告内容和相关信息
            setGeneratedReport(result.data);
            setIssuingUnit(result.issuing_unit || '');
            setReportDate(result.report_date || '');
            setShowReportViewer(true);
            
            // 添加助手消息到聊天历史
            const assistantMessage: Message = {
              role: 'assistant',
              content: `我已经为您生成了一份报告。\n\n${result.data}`,
              timestamp: result.timestamp || new Date().toISOString()
            };
            
            setCurrentChatHistory(prev => [...prev, assistantMessage]);
            
            // 添加报告完成消息
            const reportMessage: Message = {
              role: 'assistant',
              content: `报告已生成完成。\n\n您可以<a href="#" class="view-report-link" data-report-id="${Date.now()}">点击这里查看完整报告</a>`,
              timestamp: new Date().toISOString()
            };
            setCurrentChatHistory(prev => [...prev, reportMessage]);
            
            // 添加事件监听器以处理报告链接点击
            setTimeout(() => {
              const reportLinks = document.querySelectorAll('.view-report-link');
              reportLinks.forEach(link => {
                link.addEventListener('click', (e) => {
                  e.preventDefault();
                  setShowReportViewer(true);
                });
              });
            }, 100);
          } else {
            // 常规回答
            const assistantMessage: Message = {
              role: 'assistant',
              content: result.data,
              timestamp: result.timestamp || new Date().toISOString()
            };
            
            setCurrentChatHistory(prev => [...prev, assistantMessage]);
          }
          
          // 保存聊天历史
          await saveChatHistory();
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        message.error(errorData.detail || '请求失败');
        
        // 添加错误消息
        const errorMessage: Message = {
          role: 'assistant',
          content: `抱歉，我无法处理您的请求。${errorData.detail || '发生了错误，请稍后再试。'}`,
          timestamp: new Date().toISOString()
        };
        
        setCurrentChatHistory(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('发送消息失败:', error);
      message.error('发送消息失败，请检查网络连接');
      
      // 添加错误消息
      const errorMessage: Message = {
        role: 'assistant',
        content: '抱歉，我无法连接到服务器。请检查您的网络连接或稍后再试。',
        timestamp: new Date().toISOString()
      };
      
      setCurrentChatHistory(prev => [...prev, errorMessage]);
    } finally {
      setChatLoading(false);
    }
  };
  
  const startNewChat = () => {
    setCurrentChatHistory([]);
    setCurrentChatId(null);
    setShowChatHistory(false);
  };

  const handleGenerateReport = async () => {
    if (!reportQuery.trim()) {
      message.error('请输入报告生成提示');
      return;
    }

    if (reportDate.trim()) {
      const datePattern = /^\d{4}年\d{2}月\d{2}日$/;
      if (!datePattern.test(reportDate)) {
        message.error('报告日期格式必须为 "YYYY年MM月DD日"，例如 "2025年03月28日"');
        return;
      }
    }

    setReportLoading(true);
    try {
      const response = await fetch(`/api/knowledge-base/${knowledgeBase.id}/generate-report`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: reportQuery,
          k: 5,
          issuing_unit: issuingUnit || undefined,
          report_date: reportDate || undefined,
          save_history: true  // 保存到历史记录
        }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success') {
          setGeneratedReport(result.data);
          setShowReportViewer(true);
          message.success('报告生成成功');
          // 刷新历史记录
          fetchReportHistory();
        }
      }
    } catch (error) {
      message.error('报告生成失败');
    } finally {
      setReportLoading(false);
    }
  };

  const handleDownload = (report: string, date?: string) => {
    try {
      if (!report || typeof report !== 'string') {
        message.warning('没有可下载的报告或报告格式无效');
        return;
      }

      const blob = new Blob([report], { type: 'text/markdown' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      
      // 处理日期格式
      let fileDate;
      try {
        fileDate = date ? date.replace(/年|月|日/g, '') : 
                  reportDate ? reportDate.replace(/年|月|日/g, '') : 
                  new Date().toISOString().split('T')[0].replace(/-/g, '');
      } catch (dateError) {
        console.warn('日期格式处理出错:', dateError);
        fileDate = new Date().toISOString().split('T')[0].replace(/-/g, '');
      }
      
      a.download = `防汛报告_${fileDate}.md`;
      document.body.appendChild(a);
      a.click();
      
      // 清理资源
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }, 100);
      
      message.success('报告下载成功');
    } catch (error) {
      console.error('下载报告出错:', error);
      message.error('下载报告失败，请稍后重试');
    }
  };

  const loadHistoryReport = (historyItem: ReportHistory) => {
    try {
      // 格式验证
      if (!historyItem || typeof historyItem !== 'object') {
        message.error('报告数据格式无效');
        return;
      }

      // 报告内容验证
      if (!historyItem.report || typeof historyItem.report !== 'string') {
        message.error('报告内容无效，可能是格式损坏');
        console.error('无效的报告内容:', historyItem);
        return;
      }

      setReportQuery(historyItem.query || '');
      setIssuingUnit(historyItem.issuing_unit || '');
      setReportDate(historyItem.report_date || '');
      setGeneratedReport(historyItem.report);
      setShowReportViewer(true);
      
      // 确保切换到报告标签页
      setActiveTab('report');
      message.success('已加载历史报告');
    } catch (error) {
      console.error('加载历史报告出错:', error);
      message.error('加载历史报告失败，可能是格式损坏');
    }
  };

  const handleCloseReportViewer = () => {
    setShowReportViewer(false);
  };

  const deleteHistoryReport = async (reportId: string) => {
    if (!reportId) {
      message.error('删除失败：报告ID无效');
      return;
    }
    
    try {
      const response = await fetch(`/api/knowledge-base/${knowledgeBase.id}/reports/${reportId}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        const result = await response.json().catch(() => ({ status: 'success' }));
        if (result.status === 'success') {
          message.success('删除历史报告成功');
          fetchReportHistory();
        } else {
          message.warning(result.message || '删除历史报告成功，但后端返回状态异常');
          fetchReportHistory();
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        message.error(errorData.detail || `删除历史报告失败(${response.status})`);
      }
    } catch (error) {
      console.error('删除历史报告出错:', error);
      message.error('删除历史报告失败，请检查网络连接');
    }
  };

  const handleDeleteContent = async (url: string) => {
    try {
      setDeleteLoading(url);
      const response = await fetch(`/api/knowledge-base/${knowledgeBase.id}/contents`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success') {
          message.success('内容删除成功');
          // 从本地状态中移除
          setContents(prev => prev.filter(item => item.url !== url));
        } else {
          message.error(result.message || '删除失败');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        message.error(errorData.detail || `删除失败(${response.status})`);
      }
    } catch (error) {
      console.error('删除内容出错:', error);
      message.error('删除内容失败，请检查网络连接');
    } finally {
      setDeleteLoading(null);
    }
  };

  const renderStructuredData = (data: ExtractedContent['structured_data']) => {
    const counts = {
      rainfall: data.rainfall.length,
      water_condition: data.water_condition.length,
      disaster_impact: data.disaster_impact.length,
      measures: data.measures.length
    };

    return (
      <div className="structured-data-tags">
        {Object.entries(counts).map(([key, count]) => (
          count > 0 && (
            <Tag color="blue" key={key}>
              {key}: {count}
            </Tag>
          )
        ))}
      </div>
    );
  };

  const contentColumns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record: ExtractedContent) => (
        <a href={record.url} target="_blank" rel="noopener noreferrer">
          {text || record.url}
        </a>
      )
    },
    {
      title: '提取时间',
      dataIndex: 'extracted_time',
      key: 'extracted_time',
      render: (text: string) => new Date(text).toLocaleString()
    },
    {
      title: '结构化数据',
      dataIndex: 'structured_data',
      key: 'structured_data',
      render: renderStructuredData
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: ExtractedContent) => (
        <div>
          <Tooltip title="查看详情">
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => {
                Modal.info({
                  title: '内容详情',
                  width: 800,
                  content: (
                    <div style={{ maxHeight: '60vh', overflow: 'auto' }}>
                      <h3>基本信息</h3>
                      <div style={{ marginBottom: '16px' }}>
                        <p><strong>URL:</strong> {record.url}</p>
                        <p><strong>标题:</strong> {record.title}</p>
                        <p><strong>提取时间:</strong> {new Date(record.extracted_time).toLocaleString()}</p>
                      </div>
                      
                      <h3>结构化数据</h3>
                      <div style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', marginBottom: '16px' }}>
                        {Object.entries(record.structured_data).map(([category, items]) => (
                          category !== 'raw_text' ? (
                            <div key={category} style={{ marginBottom: '12px' }}>
                              <h4 style={{ margin: '8px 0' }}>{category} ({Array.isArray(items) ? items.length : 0}项)</h4>
                              {Array.isArray(items) && items.length > 0 ? (
                                <pre style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
                                  {JSON.stringify(items, null, 2)}
                                </pre>
                              ) : (
                                <p style={{ color: '#999' }}>无数据</p>
                              )}
                            </div>
                          ) : null
                        ))}
                        
                        {record.structured_data.raw_text && (
                          <div style={{ marginBottom: '12px' }}>
                            <h4 style={{ margin: '8px 0' }}>原始文本摘要</h4>
                            <p style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
                              {record.structured_data.raw_text.length > 300 
                                ? record.structured_data.raw_text.substring(0, 300) + '...' 
                                : record.structured_data.raw_text}
                            </p>
                          </div>
                        )}
                      </div>
                      
                      <h3>原始内容</h3>
                      <div style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px' }}>
                        <div style={{ maxHeight: '300px', overflow: 'auto' }}>
                          <pre style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
                            {record.content}
                          </pre>
                        </div>
                      </div>
                    </div>
                  ),
                });
              }}
            >
              查看详情
            </Button>
          </Tooltip>
          <Tooltip title="删除">
            <Button
              type="link"
              danger
              loading={deleteLoading === record.url}
              onClick={() => {
                Modal.confirm({
                  title: '确认删除',
                  content: '确定要删除这条内容吗？相关的索引和向量数据也会被清理。',
                  okText: '确认',
                  okType: 'danger',
                  cancelText: '取消',
                  onOk: () => handleDeleteContent(record.url)
                });
              }}
            >
              删除
            </Button>
          </Tooltip>
        </div>
      )
    }
  ];

  const tabItems = [
    {
      key: 'contents',
      label: '知识库内容',
      icon: <DatabaseOutlined />,
      children: (
        <div className="tab-content">
          <Card title="链接提取" className="extract-card">
            <div className="extract-form">
              <TextArea
                placeholder="请输入要提取的链接，每行一个"
                value={urls}
                onChange={e => setUrls(e.target.value)}
                rows={3}
                autoSize={{ minRows: 3, maxRows: 5 }}
                disabled={extractLoading}
              />
              <div className="extract-hint">
                提示：每行输入一个链接，支持HTTP和HTTPS链接
              </div>
              <Button
                type="primary"
                icon={<CloudDownloadOutlined />}
                loading={extractLoading}
                onClick={handleExtract}
                disabled={extractLoading}
              >
                开始提取
              </Button>
            </div>
            
            {extractProgress && (
              <div className="extract-progress">
                <div className="progress-header">
                  <span>总体进度: {extractProgress.current}/{extractProgress.total}</span>
                  <span>{Math.round((extractProgress.current / extractProgress.total) * 100)}%</span>
                </div>
                <Progress 
                  percent={Math.round((extractProgress.current / extractProgress.total) * 100)} 
                  size="small" 
                  status={extractLoading ? "active" : "normal"}
                />
                <div className="progress-status">
                  <div>状态: {extractProgress.status}</div>
                  {extractProgress.currentUrl && (
                    <div>当前处理: {extractProgress.currentUrl}</div>
                  )}
                </div>
                
                {extractProgress.urlProgress && extractProgress.urlProgress.length > 0 && (
                  <Collapse 
                    bordered={false}
                    defaultActiveKey={[]}
                    className="url-progress-collapse"
                  >
                    <Collapse.Panel 
                      header={<span>链接提取详情 ({extractProgress.current}/{extractProgress.total})</span>} 
                      key="1"
                    >
                      <List
                        size="small"
                        dataSource={extractProgress.urlProgress}
                        className="url-progress-list"
                        renderItem={(item, index) => (
                          <List.Item>
                            <div className="url-progress-item">
                              <Typography.Text ellipsis title={item.url}>
                                {index + 1}. {item.url}
                              </Typography.Text>
                              <Tag color={
                                item.status === 'success' ? 'success' : 
                                item.status === 'error' ? 'error' : 
                                item.status === 'processing' ? 'processing' : 'default'
                              }>
                                {item.status === 'success' ? '成功' : 
                                 item.status === 'error' ? '失败' : 
                                 item.status === 'processing' ? '处理中' : '等待中'}
                              </Tag>
                            </div>
                            {item.message && (
                              <div className="url-message">
                                {item.message}
                              </div>
                            )}
                          </List.Item>
                        )}
                      />
                    </Collapse.Panel>
                  </Collapse>
                )}
              </div>
            )}
          </Card>
          
          <div className="log-section">
            <Card 
              title="提取日志" 
              extra={
                <Button 
                  type="text" 
                  icon={<ClearOutlined />} 
                  onClick={() => setLogMessages([])}
                >
                  清空
                </Button>
              }
              className="log-card"
            >
              <div className="log-content" ref={logRef}>
                {logMessages.length > 0 ? (
                  logMessages.map((msg, index) => (
                    <div key={index} className="log-line">
                      {msg}
                    </div>
                  ))
                ) : (
                  <div className="empty-log">暂无日志信息</div>
                )}
                {logPolling && (
                  <div className="thinking">
                    处理中{thinkingDots}
                  </div>
                )}
              </div>
            </Card>
          </div>
          
          <Card 
            title="知识库内容列表" 
            extra={
              <Button 
                type="primary" 
                icon={<SyncOutlined />} 
                onClick={fetchContents}
                loading={contentsLoading}
              >
                刷新
              </Button>
            }
            className="content-list-card"
          >
            <Table
              dataSource={contents}
              columns={contentColumns}
              rowKey="url"
              loading={contentsLoading}
              locale={{ emptyText: <Empty description="暂无内容" /> }}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </div>
      )
    },
    {
      key: 'indices',
      label: '目录引管理',
      icon: <ApartmentOutlined />,
      children: (
        <IndexManager knowledgeBaseId={knowledgeBase.id} buildIndex={buildIndex} />
      )
    },
    {
      key: 'chat',
      label: '智能问答',
      icon: <MessageOutlined />,
      children: (
        <div className="chat-container">
          <div className="chat-layout">
            {currentChatHistory.length === 0 ? (
              <div className="chat-empty">
                <div className="chat-empty-icon">
                  <RobotOutlined />
                </div>
                <Typography.Title level={4}>智能问答</Typography.Title>
                <div className="chat-empty-text">
                  您可以向AI助手询问与知识库相关的问题，获取基于知识库的专业回答。
                </div>
                <div className="chat-empty-suggestions">
                  <div className="suggestion-tag" onClick={() => setChatInput('这个知识库包含哪些主要内容？')}>
                    这个知识库包含哪些主要内容？
                  </div>
                  <div className="suggestion-tag" onClick={() => setChatInput('最近的洪水情况如何？')}>
                    最近的洪水情况如何？
                  </div>
                  <div className="suggestion-tag" onClick={() => setChatInput('哪些地区受灾最严重？')}>
                    哪些地区受灾最严重？
                  </div>
                  <div className="suggestion-tag" onClick={() => setChatInput('目前采取了哪些防灾措施？')}>
                    目前采取了哪些防灾措施？
                  </div>
                </div>
              </div>
            ) : (
              <div className="chat-messages">
                {currentChatHistory.map((message, index) => (
                  <div 
                    key={index} 
                    className={`message-bubble message-${message.role}`}
                  >
                    {message.role === 'assistant' && (
                      <div className="message-avatar">
                        <RobotOutlined />
                      </div>
                    )}
                    <div className="message-content">
                      <div className="markdown-content">
                        <EnhancedMarkdown>
                          {message.content}
                        </EnhancedMarkdown>
                      </div>
                      <div className="message-time">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                    {message.role === 'user' && (
                      <div className="message-avatar">
                        <UserOutlined />
                      </div>
                    )}
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>
            )}
            <div className="chat-input-area">
              <div className="chat-input-wrapper">
                <TextArea
                  placeholder="请输入您的问题，Enter键发送，Shift+Enter换行"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onPressEnter={(e) => {
                    if (!e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  disabled={chatLoading}
                  autoSize={{ minRows: 1, maxRows: 4 }}
                  autoFocus
                />
                <Button
                  type="primary"
                  className="chat-send-button"
                  icon={chatLoading ? <LoadingOutlined /> : <SendOutlined />}
                  onClick={handleSendMessage}
                  disabled={!chatInput.trim() || chatLoading}
                />
              </div>
              <div className="chat-options">
                <span>
                  {showChatHistory ? (
                    <Button 
                      type="link" 
                      size="small" 
                      onClick={() => setShowChatHistory(false)}
                      icon={<CaretRightOutlined />}
                    >
                      隐藏历史对话
                    </Button>
                  ) : (
                    <Button 
                      type="link" 
                      size="small" 
                      onClick={() => setShowChatHistory(true)}
                      icon={<HistoryOutlined />}
                    >
                      查看历史对话
                    </Button>
                  )}
                </span>
                <span>
                  <Button 
                    type="link" 
                    size="small" 
                    onClick={() => {
                      setCurrentChatHistory([]);
                      setCurrentChatId(null);
                    }}
                    icon={<ClearOutlined />}
                  >
                    清空当前对话
                  </Button>
                  <Button
                    type="link"
                    size="small"
                    onClick={() => {
                      // 打开报告生成弹窗
                      const lastUserMessage = currentChatHistory.find(msg => msg.role === 'user')?.content || '';
                      setReportModalQuery(lastUserMessage);
                      setReportModalUnit('');
                      setReportModalDate('');
                      setShowReportModal(true);
                    }}
                    icon={<FileTextOutlined />}
                    disabled={currentChatHistory.length < 2}
                  >
                    生成报告
                  </Button>
                </span>
              </div>
              {showChatHistory && (
                <div className="chat-history-list">
                  <List
                    loading={chatHistoryLoading}
                    dataSource={allChatHistories}
                    renderItem={(item) => (
                      <div
                        className={`chat-history-item ${currentChatId === item.id ? 'active' : ''}`}
                        onClick={() => loadChatHistory(item.id)}
                      >
                        <span>
                          <HistoryOutlined style={{ marginRight: 8 }} />
                          <Typography.Text ellipsis style={{ maxWidth: 200 }}>
                            {item.title}
                          </Typography.Text>
                        </span>
                        <span>
                          <Button
                            type="text"
                            size="small"
                            icon={<DeleteOutlined />}
                            onClick={(e) => {
                              e.stopPropagation();
                              Modal.confirm({
                                title: '确认删除',
                                content: '确定要删除这个聊天记录吗？',
                                onOk: () => deleteChatHistory(item.id)
                              });
                            }}
                          />
                        </span>
                      </div>
                    )}
                    locale={{ emptyText: '暂无历史对话' }}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )
    },
    {
      key: 'report',
      label: '历史报告',
      icon: <FileTextOutlined />,
      children: (
        <div className="tab-content">
          {generatedReport && showReportViewer && (
            <ReportViewer 
              report={generatedReport}
              issuingUnit={issuingUnit}
              reportDate={reportDate}
              onDownload={() => handleDownload(generatedReport, reportDate)}
              visible={showReportViewer}
              onClose={handleCloseReportViewer}
            />
          )}
          
          <Card title={<div><HistoryOutlined /> 历史报告</div>} loading={historyLoading}>
            {reportHistory.length > 0 ? (
              <List
                itemLayout="vertical"
                dataSource={reportHistory}
                pagination={{ pageSize: 5 }}
                renderItem={item => {
                  // 验证和安全访问
                  const isValidReport = item && typeof item === 'object' && item.report && typeof item.report === 'string';
                  const reportContent = isValidReport ? item.report : '无效报告内容';
                  const reportSubstring = isValidReport ? 
                    (reportContent.length > 200 ? reportContent.substring(0, 200) + '...' : reportContent) 
                    : '无效报告内容';
                  
                  return (
                    <List.Item
                      key={item?.id || 'unknown'}
                      actions={[
                        <Button 
                          type="link" 
                          key="view" 
                          onClick={() => {
                            if (isValidReport) {
                              loadHistoryReport(item);
                            } else {
                              message.error('无效的报告内容，无法加载');
                            }
                          }}
                          disabled={!isValidReport}
                        >
                          <EyeOutlined /> 查看
                        </Button>,
                        <Button 
                          type="link" 
                          key="download" 
                          onClick={() => {
                            if (isValidReport) {
                              handleDownload(item.report, item.report_date);
                            } else {
                              message.error('无效的报告内容，无法下载');
                            }
                          }}
                          disabled={!isValidReport}
                        >
                          <DownloadOutlined /> 下载
                        </Button>,
                        <Button 
                          type="link" 
                          key="delete" 
                          danger 
                          onClick={() => {
                            if (item?.id) {
                              deleteHistoryReport(item.id);
                            } else {
                              message.error('无效的报告ID，无法删除');
                            }
                          }}
                        >
                          <DeleteOutlined /> 删除
                        </Button>
                      ]}
                    >
                      <List.Item.Meta
                        title={<Typography.Text ellipsis>{item?.query || '未知查询'}</Typography.Text>}
                        description={
                          <div>
                            <div>生成时间: {item?.created_at ? new Date(item.created_at).toLocaleString() : '未知时间'}</div>
                            {item?.issuing_unit && <div>发布单位: {item.issuing_unit}</div>}
                            {item?.report_date && <div>报告日期: {item.report_date}</div>}
                          </div>
                        }
                      />
                      <Typography.Paragraph ellipsis={{ rows: 2 }} className="report-preview markdown-content">
                        {isValidReport ? (
                          <div className="preview-content">
                            {reportSubstring}
                          </div>
                        ) : (
                          '无效的报告内容'
                        )}
                      </Typography.Paragraph>
                    </List.Item>
                  );
                }}
              />
            ) : (
              <div style={{ textAlign: 'center', padding: '20px 0' }}>
                暂无历史报告记录
              </div>
            )}
          </Card>
        </div>
      )
    },
  ];

  return (
    <div className="knowledge-base-detail">
      {pageLoading ? (
        <Card loading={true}>
          <div style={{ textAlign: 'center', padding: '50px 0' }}>
            加载中...
          </div>
        </Card>
      ) : loadError ? (
        <Card title="错误" className="error-card">
          <div style={{ textAlign: 'center', padding: '30px 0' }}>
            <h3>加载知识库详情时出错</h3>
            <p>{loadError}</p>
            <Button type="primary" onClick={onBack}>
              返回知识库列表
            </Button>
          </div>
        </Card>
      ) : (
        <div className="kb-detail-container">
          <div className="kb-detail-header">
            <Button icon={<ArrowLeftOutlined />} onClick={onBack}>返回</Button>
            <Typography.Title level={4}>{knowledgeBase.name}</Typography.Title>
            <div className="kb-header-info">创建时间: {new Date(knowledgeBase.createdAt).toLocaleString()}</div>
          </div>

          <div className="kb-detail-layout">
            <div className="kb-sidebar">
              <Menu
                mode="inline"
                selectedKeys={[activeTab]}
                onClick={({ key }) => setActiveTab(key)}
                className="kb-sidebar-menu"
              >
                {tabItems.map(item => (
                  <Menu.Item key={item.key} icon={item.icon}>
                    {item.label}
                  </Menu.Item>
                ))}
              </Menu>
            </div>

            <div className="kb-content">
              {tabItems.find(item => item.key === activeTab)?.children}
            </div>
          </div>
        </div>
      )}
      
      {/* 报告生成弹窗 */}
      <Modal
        title="生成报告"
        open={showReportModal}
        onCancel={() => setShowReportModal(false)}
        footer={[
          <Button key="cancel" onClick={() => setShowReportModal(false)}>
            取消
          </Button>,
          <Button 
            key="submit" 
            type="primary" 
            loading={reportLoading}
            onClick={() => {
              if (!reportModalQuery.trim()) {
                message.error('请输入报告查询内容');
                return;
              }
              
              setReportLoading(true);
              
              // 显示一个请求中的消息
              const processingMessage: Message = {
                role: 'assistant',
                content: '正在为您生成报告，请稍候...',
                timestamp: new Date().toISOString()
              };
              setCurrentChatHistory(prev => [...prev, processingMessage]);
              
              // 关闭弹窗
              setShowReportModal(false);
              
              // 调用报告生成API
              fetch(`/api/knowledge-base/${knowledgeBase.id}/generate-report`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                  query: reportModalQuery,
                  k: 5,
                  issuing_unit: reportModalUnit || undefined,
                  report_date: reportModalDate || undefined,
                  save_history: true
                }),
              })
              .then(response => response.json())
              .then(result => {
                if (result.status === 'success') {
                  // 移除处理中消息
                  setCurrentChatHistory(prev => prev.filter(msg => 
                    !(msg.role === 'assistant' && msg.content === '正在为您生成报告，请稍候...')
                  ));
                  
                  // 添加报告完成消息
                  const reportMessage: Message = {
                    role: 'assistant',
                    content: `报告已生成完成。\n\n您可以<a href="#" class="view-report-link" data-report-id="${Date.now()}">点击这里查看完整报告</a>`,
                    timestamp: new Date().toISOString()
                  };
                  setCurrentChatHistory(prev => [...prev, reportMessage]);
                  
                  // 添加事件监听器以处理报告链接点击
                  setTimeout(() => {
                    const reportLinks = document.querySelectorAll('.view-report-link');
                    reportLinks.forEach(link => {
                      link.addEventListener('click', (e) => {
                        e.preventDefault();
                        setShowReportViewer(true);
                      });
                    });
                  }, 100);
                  
                  // 设置报告内容和相关信息
                  setGeneratedReport(result.data);
                  setIssuingUnit(result.issuing_unit || reportModalUnit || '');
                  setReportDate(result.report_date || reportModalDate || '');
                  setShowReportViewer(true);
                  
                  // 刷新历史记录
                  fetchReportHistory();
                  message.success('报告生成成功');
                } else {
                  // 移除处理中消息
                  setCurrentChatHistory(prev => prev.filter(msg => 
                    !(msg.role === 'assistant' && msg.content === '正在为您生成报告，请稍候...')
                  ));
                  
                  // 添加失败消息
                  const errorMessage: Message = {
                    role: 'assistant',
                    content: `抱歉，报告生成失败: ${result.message || '未知错误'}`,
                    timestamp: new Date().toISOString()
                  };
                  setCurrentChatHistory(prev => [...prev, errorMessage]);
                  message.error('报告生成失败');
                }
                setReportLoading(false);
              })
              .catch(error => {
                console.error('报告生成失败:', error);
                
                // 移除处理中消息
                setCurrentChatHistory(prev => prev.filter(msg => 
                  !(msg.role === 'assistant' && msg.content === '正在为您生成报告，请稍候...')
                ));
                
                // 添加错误消息
                const errorMessage: Message = {
                  role: 'assistant',
                  content: '抱歉，报告生成过程中发生错误，请稍后重试。',
                  timestamp: new Date().toISOString()
                };
                setCurrentChatHistory(prev => [...prev, errorMessage]);
                message.error('报告生成失败，请稍后重试');
                setReportLoading(false);
              });
            }}
          >
            生成
          </Button>
        ]}
      >
        <div style={{ marginBottom: 16 }}>
          <Typography.Text strong>报告查询内容</Typography.Text>
          <Input.TextArea
            placeholder="请输入报告查询内容，例如：南京市洪水情况"
            value={reportModalQuery}
            onChange={e => setReportModalQuery(e.target.value)}
            autoSize={{ minRows: 3, maxRows: 5 }}
            style={{ marginTop: 8 }}
          />
        </div>
        <div style={{ marginBottom: 16 }}>
          <Typography.Text strong>发布单位（可选）</Typography.Text>
          <Input
            placeholder="请输入报告发布单位，例如：南京市防汛指挥部"
            value={reportModalUnit}
            onChange={e => setReportModalUnit(e.target.value)}
            style={{ marginTop: 8 }}
          />
        </div>
        <div>
          <Typography.Text strong>报告日期（可选）</Typography.Text>
          <Input
            placeholder="格式：YYYY年MM月DD日，例如：2025年04月15日"
            value={reportModalDate}
            onChange={e => setReportModalDate(e.target.value)}
            style={{ marginTop: 8 }}
          />
        </div>
      </Modal>
    </div>
  );
};

export default KnowledgeBaseDetail; 