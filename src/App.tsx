import React, { useState, useEffect, useRef } from 'react';
import { Play, Download, RefreshCw, Clock, CheckCircle, XCircle, AlertCircle, Cookie, FileText, Settings, Terminal, Zap } from 'lucide-react';
import axios from 'axios';

interface TaskStatus {
  status: string;
  start_time?: string;
  end_time?: string;
  progress?: number;
  result?: {
    success_count: number;
    fail_count: number;
    success_file: string;
    fail_file: string;
    total_processed: number;
  };
  error?: string;
  console_logs?: string[];
  current_member?: string;
  current_family?: string;
}

interface LogFile {
  filename: string;
  size: number;
  modified: string;
}

interface CookieFile {
  name: string;
  filename: string;
  modified: string;
}

interface ConsoleLog {
  timestamp: string;
  type: 'info' | 'success' | 'error' | 'warning';
  message: string;
}

function App() {
  const [startRow, setStartRow] = useState<number>(0);
  const [endRow, setEndRow] = useState<number>(100);
  const [cookieName, setCookieName] = useState<string>('');
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [taskId, setTaskId] = useState<string>('');
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [logs, setLogs] = useState<LogFile[]>([]);
  const [cookies, setCookies] = useState<CookieFile[]>([]);
  const [activeTab, setActiveTab] = useState<'run' | 'logs' | 'cookies'>('run');
  const [showLoginModal, setShowLoginModal] = useState<boolean>(false);
  const [loginParams, setLoginParams] = useState<any>(null);
  const [consoleLogs, setConsoleLogs] = useState<ConsoleLog[]>([]);
  const consoleRef = useRef<HTMLDivElement>(null);

  const API_BASE = 'http://localhost:5000/api';

  useEffect(() => {
    fetchLogs();
    fetchCookies();
    addConsoleLog('info', 'System initialized. Ready for automation tasks.');
  }, []);

  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [consoleLogs]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRunning && taskId) {
      interval = setInterval(async () => {
        try {
          const response = await axios.get(`${API_BASE}/task_status/${taskId}`);
          setTaskStatus(response.data);
          
          // Add new console logs from backend
          if (response.data.console_logs && Array.isArray(response.data.console_logs)) {
            const newLogs = response.data.console_logs.slice(consoleLogs.length);
            newLogs.forEach((logMessage: string) => {
              // Determine log type based on message content
              let logType: 'info' | 'success' | 'error' | 'warning' = 'info';
              if (logMessage.includes('✅') || logMessage.includes('🎉')) {
                logType = 'success';
              } else if (logMessage.includes('❌') || logMessage.includes('⚠️')) {
                logType = 'error';
              } else if (logMessage.includes('🔍') || logMessage.includes('📝')) {
                logType = 'warning';
              }
              
              addConsoleLog(logType, logMessage);
            });
          }
          
          // Add current processing info
          if (response.data.current_member && response.data.current_family) {
            const currentInfo = `Processing Member ID: ${response.data.current_member} | Family ID: ${response.data.current_family}`;
            if (!consoleLogs.some(log => log.message.includes(currentInfo))) {
              addConsoleLog('info', `🔄 ${currentInfo}`);
            }
          }
          
          if (response.data.status === 'completed') {
            setIsRunning(false);
            addConsoleLog('success', `🎉 Automation completed successfully! Processed ${response.data.result?.total_processed || 0} members.`);
            addConsoleLog('success', `📊 Success: ${response.data.result?.success_count || 0} | Failed: ${response.data.result?.fail_count || 0}`);
            fetchLogs();
          } else if (response.data.status === 'failed') {
            setIsRunning(false);
            addConsoleLog('error', `❌ Automation failed: ${response.data.error}`);
          }
        } catch (error) {
          console.error('Error fetching task status:', error);
          addConsoleLog('error', '❌ Failed to fetch task status');
        }
      }, 1000); // Check every second for more responsive updates
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRunning, taskId, consoleLogs.length]);

  const addConsoleLog = (type: 'info' | 'success' | 'error' | 'warning', message: string) => {
    const newLog: ConsoleLog = {
      timestamp: new Date().toLocaleTimeString(),
      type,
      message
    };
    setConsoleLogs(prev => {
      // Avoid duplicate messages
      if (prev.some(log => log.message === message && log.timestamp === newLog.timestamp)) {
        return prev;
      }
      return [...prev.slice(-99), newLog]; // Keep last 100 logs
    });
  };

  const fetchLogs = async () => {
    try {
      const response = await axios.get(`${API_BASE}/logs`);
      setLogs(response.data);
    } catch (error) {
      console.error('Error fetching logs:', error);
      addConsoleLog('error', '❌ Failed to fetch log files');
    }
  };

  const fetchCookies = async () => {
    try {
      const response = await axios.get(`${API_BASE}/cookies`);
      setCookies(response.data);
    } catch (error) {
      console.error('Error fetching cookies:', error);
      addConsoleLog('error', '❌ Failed to fetch session data');
    }
  };

  const handleRun = async () => {
    if (!cookieName.trim() || startRow >= endRow) {
      addConsoleLog('error', '❌ Invalid input parameters. Please check your configuration.');
      return;
    }

    try {
      setIsRunning(true);
      setConsoleLogs([]); // Clear previous logs
      addConsoleLog('info', `🚀 Initiating automation for session: ${cookieName}`);
      addConsoleLog('info', `📊 Processing rows ${startRow} to ${endRow}`);
      
      const response = await axios.post(`${API_BASE}/run`, {
        start_row: startRow,
        end_row: endRow,
        cookie_name: cookieName.trim()
      });

      if (response.data.status === 'started') {
        setTaskId(response.data.task_id);
        setTaskStatus({ status: 'running', progress: 0 });
        addConsoleLog('success', '✅ Automation task started successfully');
      } else if (response.data.status === 'login_required') {
        setLoginParams({ start_row: startRow, end_row: endRow, cookie_name: cookieName.trim() });
        setShowLoginModal(true);
        setIsRunning(false);
        addConsoleLog('warning', '⚠️ Session not found. Manual login required.');
      }
    } catch (error) {
      console.error('Error starting automation:', error);
      setIsRunning(false);
      addConsoleLog('error', '❌ Failed to start automation task');
    }
  };

  const handleManualLogin = async () => {
    try {
      addConsoleLog('info', '🌐 Opening browser for manual authentication...');
      const response = await axios.get(`${API_BASE}/login`, {
        params: loginParams
      });
      
      if (response.data.status === 'browser_opened') {
        addConsoleLog('success', '✅ Browser launched. Please complete authentication.');
      }
    } catch (error) {
      console.error('Error starting manual login:', error);
      addConsoleLog('error', '❌ Failed to launch authentication browser');
    }
  };

  const handleContinueAfterLogin = async () => {
    try {
      setIsRunning(true);
      addConsoleLog('info', '💾 Saving authentication session...');
      const response = await axios.post(`${API_BASE}/save_cookies`, loginParams);
      
      if (response.data.status === 'started') {
        setTaskId(response.data.task_id);
        setTaskStatus({ status: 'saving_cookies', progress: 10 });
        setShowLoginModal(false);
        addConsoleLog('success', '✅ Session saved. Starting automation...');
        fetchCookies();
      }
    } catch (error) {
      console.error('Error saving cookies:', error);
      setIsRunning(false);
      addConsoleLog('error', '❌ Failed to save session and start automation');
    }
  };

  const downloadLog = async (filename: string) => {
    try {
      addConsoleLog('info', `📥 Downloading log file: ${filename}`);
      const response = await axios.get(`${API_BASE}/logs/${filename}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      addConsoleLog('success', `✅ Downloaded: ${filename}`);
    } catch (error) {
      console.error('Error downloading log:', error);
      addConsoleLog('error', `❌ Failed to download: ${filename}`);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
      case 'saving_cookies':
        return <RefreshCw className="w-5 h-5 animate-spin text-green-400" />;
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-400" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  const getConsoleLogColor = (type: string) => {
    switch (type) {
      case 'success':
        return 'text-green-400';
      case 'error':
        return 'text-red-400';
      case 'warning':
        return 'text-yellow-400';
      default:
        return 'text-cyan-400';
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const clearConsole = () => {
    setConsoleLogs([]);
    addConsoleLog('info', '🔄 Console cleared');
  };

  // Helper function to clamp progress between 0 and 100
  const getClampedProgress = (progress?: number) => {
    if (progress === undefined) return 0;
    return Math.min(Math.max(progress, 0), 100);
  };

  return (
    <div className="min-h-screen bg-black text-green-400 font-mono">
      {/* Matrix-style background effect */}
      <div className="fixed inset-0 opacity-5 pointer-events-none">
        <div className="absolute inset-0 bg-gradient-to-b from-green-900/20 to-black"></div>
      </div>
      
      <div className="relative z-10 container mx-auto px-4 py-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8 border-b border-green-800 pb-6">
            <div className="flex items-center justify-center mb-4">
              <Terminal className="w-8 h-8 mr-3 text-green-400" />
              <h1 className="text-4xl font-bold text-green-400 tracking-wider">
                SELENIUM AUTOMATION TERMINAL
              </h1>
              <Zap className="w-8 h-8 ml-3 text-green-400" />
            </div>
            <p className="text-green-600 text-lg tracking-wide">
              ADVANCED BROWSER AUTOMATION CONTROL SYSTEM
            </p>
          </div>

          {/* Navigation Tabs */}
          <div className="flex justify-center mb-8">
            <div className="bg-gray-900 border border-green-800 rounded-lg p-1">
              <button
                onClick={() => setActiveTab('run')}
                className={`px-6 py-3 rounded-md font-medium transition-all tracking-wide ${
                  activeTab === 'run'
                    ? 'bg-green-900 text-green-400 border border-green-600'
                    : 'text-green-600 hover:text-green-400 hover:bg-gray-800'
                }`}
              >
                <Settings className="w-4 h-4 inline mr-2" />
                EXECUTE
              </button>
              <button
                onClick={() => setActiveTab('logs')}
                className={`px-6 py-3 rounded-md font-medium transition-all tracking-wide ${
                  activeTab === 'logs'
                    ? 'bg-green-900 text-green-400 border border-green-600'
                    : 'text-green-600 hover:text-green-400 hover:bg-gray-800'
                }`}
              >
                <FileText className="w-4 h-4 inline mr-2" />
                LOGS
              </button>
              <button
                onClick={() => setActiveTab('cookies')}
                className={`px-6 py-3 rounded-md font-medium transition-all tracking-wide ${
                  activeTab === 'cookies'
                    ? 'bg-green-900 text-green-400 border border-green-600'
                    : 'text-green-600 hover:text-green-400 hover:bg-gray-800'
                }`}
              >
                <Cookie className="w-4 h-4 inline mr-2" />
                SESSIONS
              </button>
            </div>
          </div>

          {/* Run Automation Tab */}
          {activeTab === 'run' && (
            <div className="space-y-8">
              {/* Configuration Panel */}
              <div className="bg-gray-900 border border-green-800 rounded-lg p-6">
                <h2 className="text-2xl font-semibold text-green-400 mb-6 tracking-wide flex items-center">
                  <Terminal className="w-6 h-6 mr-3" />
                  AUTOMATION CONFIGURATION
                </h2>
                
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-green-400 mb-2 tracking-wide">
                      SESSION IDENTIFIER
                    </label>
                    <input
                      type="text"
                      value={cookieName}
                      onChange={(e) => setCookieName(e.target.value)}
                      placeholder="user1, ward_a, admin_session..."
                      className="w-full px-4 py-3 bg-black border border-green-800 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-green-600 text-green-400 placeholder-green-700 font-mono"
                      disabled={isRunning}
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-green-400 mb-2 tracking-wide">
                        START ROW INDEX
                      </label>
                      <input
                        type="number"
                        value={startRow}
                        onChange={(e) => setStartRow(parseInt(e.target.value) || 0)}
                        className="w-full px-4 py-3 bg-black border border-green-800 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-green-600 text-green-400 font-mono"
                        disabled={isRunning}
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-green-400 mb-2 tracking-wide">
                        END ROW INDEX
                      </label>
                      <input
                        type="number"
                        value={endRow}
                        onChange={(e) => setEndRow(parseInt(e.target.value) || 0)}
                        className="w-full px-4 py-3 bg-black border border-green-800 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-green-600 text-green-400 font-mono"
                        disabled={isRunning}
                      />
                    </div>
                  </div>
                  
                  <button
                    onClick={handleRun}
                    disabled={isRunning}
                    className="w-full bg-green-900 hover:bg-green-800 disabled:bg-gray-800 disabled:text-gray-600 text-green-400 font-medium py-4 px-6 rounded-lg transition-all border border-green-600 tracking-wide flex items-center justify-center"
                  >
                    {isRunning ? (
                      <>
                        <RefreshCw className="w-5 h-5 mr-3 animate-spin" />
                        EXECUTING AUTOMATION...
                      </>
                    ) : (
                      <>
                        <Play className="w-5 h-5 mr-3" />
                        INITIATE AUTOMATION SEQUENCE
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Status Panel */}
              <div className="bg-gray-900 border border-green-800 rounded-lg p-6">
                <h2 className="text-2xl font-semibold text-green-400 mb-6 tracking-wide flex items-center">
                  <Zap className="w-6 h-6 mr-3" />
                  SYSTEM STATUS & PROGRESS
                </h2>
                
                {taskStatus ? (
                  <div className="space-y-6">
                    <div className="flex items-center space-x-4">
                      {getStatusIcon(taskStatus.status)}
                      <span className="text-xl font-medium capitalize tracking-wide text-green-400">
                        STATUS: {taskStatus.status.replace('_', ' ').toUpperCase()}
                      </span>
                    </div>
                    
                    {taskStatus.progress !== undefined && (
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm text-green-400">
                          <span>PROGRESS</span>
                          <span>{Math.round(getClampedProgress(taskStatus.progress))}%</span>
                        </div>
                        <div className="w-full bg-gray-800 rounded-full h-3 border border-green-800 overflow-hidden">
                          <div
                            className="bg-gradient-to-r from-green-600 to-green-400 h-3 rounded-full transition-all duration-300 ease-out"
                            style={{ 
                              width: `${getClampedProgress(taskStatus.progress)}%`,
                              maxWidth: '100%'
                            }}
                          ></div>
                        </div>
                      </div>
                    )}
                    
                    {taskStatus.current_member && taskStatus.current_family && (
                      <div className="bg-black border border-green-800 rounded-lg p-4">
                        <h3 className="font-medium text-green-400 mb-2 tracking-wide">CURRENT PROCESSING</h3>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <div className="text-cyan-400">Member ID:</div>
                            <div className="text-green-400 font-mono">{taskStatus.current_member}</div>
                          </div>
                          <div>
                            <div className="text-cyan-400">Family ID:</div>
                            <div className="text-green-400 font-mono">{taskStatus.current_family}</div>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {taskStatus.result && (
                      <div className="bg-black border border-green-800 rounded-lg p-4">
                        <h3 className="font-medium text-green-400 mb-3 tracking-wide">EXECUTION RESULTS</h3>
                        <div className="grid grid-cols-3 gap-4 text-sm">
                          <div className="text-center">
                            <div className="text-cyan-400 font-bold text-2xl">{taskStatus.result.total_processed}</div>
                            <div className="text-green-600">TOTAL PROCESSED</div>
                          </div>
                          <div className="text-center">
                            <div className="text-green-400 font-bold text-2xl">{taskStatus.result.success_count}</div>
                            <div className="text-green-600">SUCCESSFUL</div>
                          </div>
                          <div className="text-center">
                            <div className="text-red-400 font-bold text-2xl">{taskStatus.result.fail_count}</div>
                            <div className="text-green-600">FAILED</div>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {taskStatus.error && (
                      <div className="bg-red-900/20 border border-red-800 rounded-lg p-4">
                        <div className="flex items-center">
                          <AlertCircle className="w-5 h-5 text-red-400 mr-3" />
                          <span className="text-red-400 font-medium tracking-wide">SYSTEM ERROR</span>
                        </div>
                        <p className="text-red-300 text-sm mt-2 font-mono">{taskStatus.error}</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center text-green-600 py-8">
                    <Terminal className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p className="tracking-wide">SYSTEM READY - NO ACTIVE PROCESSES</p>
                  </div>
                )}
              </div>

              {/* Console Panel */}
              <div className="bg-gray-900 border border-green-800 rounded-lg p-6">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-2xl font-semibold text-green-400 tracking-wide flex items-center">
                    <Terminal className="w-6 h-6 mr-3" />
                    SYSTEM CONSOLE
                  </h2>
                  <button
                    onClick={clearConsole}
                    className="bg-red-900 hover:bg-red-800 text-red-400 px-4 py-2 rounded border border-red-600 text-sm tracking-wide"
                  >
                    CLEAR
                  </button>
                </div>
                
                <div 
                  ref={consoleRef}
                  className="bg-black border border-green-800 rounded-lg p-4 h-80 overflow-y-auto font-mono text-sm"
                >
                  {consoleLogs.map((log, index) => (
                    <div key={index} className="mb-1 leading-relaxed">
                      <span className="text-gray-500">[{log.timestamp}]</span>
                      <span className={`ml-2 ${getConsoleLogColor(log.type)}`}>
                        {log.message}
                      </span>
                    </div>
                  ))}
                  {consoleLogs.length === 0 && (
                    <div className="text-green-600 opacity-50">
                      Console ready for output...
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Logs Tab */}
          {activeTab === 'logs' && (
            <div className="bg-gray-900 border border-green-800 rounded-lg p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-semibold text-green-400 tracking-wide flex items-center">
                  <FileText className="w-6 h-6 mr-3" />
                  AUTOMATION LOGS
                </h2>
                <button
                  onClick={fetchLogs}
                  className="bg-green-900 hover:bg-green-800 text-green-400 px-4 py-2 rounded-lg flex items-center border border-green-600 tracking-wide"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  REFRESH
                </button>
              </div>
              
              <div className="overflow-x-auto">
                <table className="w-full table-auto">
                  <thead>
                    <tr className="bg-black border-b border-green-800">
                      <th className="px-4 py-3 text-left text-sm font-medium text-green-400 tracking-wide">FILENAME</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-green-400 tracking-wide">SIZE</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-green-400 tracking-wide">MODIFIED</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-green-400 tracking-wide">ACTION</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-green-800">
                    {logs.map((log, index) => (
                      <tr key={index} className="hover:bg-gray-800">
                        <td className="px-4 py-3 text-sm text-green-400 font-mono">{log.filename}</td>
                        <td className="px-4 py-3 text-sm text-green-600">{formatFileSize(log.size)}</td>
                        <td className="px-4 py-3 text-sm text-green-600">
                          {new Date(log.modified).toLocaleString()}
                        </td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => downloadLog(log.filename)}
                            className="bg-cyan-900 hover:bg-cyan-800 text-cyan-400 px-3 py-1 rounded text-sm flex items-center border border-cyan-600 tracking-wide"
                          >
                            <Download className="w-4 h-4 mr-1" />
                            DOWNLOAD
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                
                {logs.length === 0 && (
                  <div className="text-center text-green-600 py-8">
                    <FileText className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p className="tracking-wide">NO LOG FILES DETECTED</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Cookies Tab */}
          {activeTab === 'cookies' && (
            <div className="bg-gray-900 border border-green-800 rounded-lg p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-semibold text-green-400 tracking-wide flex items-center">
                  <Cookie className="w-6 h-6 mr-3" />
                  ACTIVE SESSIONS
                </h2>
                <button
                  onClick={fetchCookies}
                  className="bg-green-900 hover:bg-green-800 text-green-400 px-4 py-2 rounded-lg flex items-center border border-green-600 tracking-wide"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  REFRESH
                </button>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {cookies.map((cookie, index) => (
                  <div key={index} className="bg-black border border-green-800 rounded-lg p-4">
                    <div className="flex items-center mb-2">
                      <Cookie className="w-5 h-5 text-green-400 mr-2" />
                      <h3 className="font-medium text-green-400 tracking-wide">{cookie.name.toUpperCase()}</h3>
                    </div>
                    <p className="text-sm text-green-600 font-mono">
                      LAST ACCESS: {new Date(cookie.modified).toLocaleString()}
                    </p>
                  </div>
                ))}
              </div>
              
              {cookies.length === 0 && (
                <div className="text-center text-green-600 py-8">
                  <Cookie className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p className="tracking-wide">NO ACTIVE SESSIONS FOUND</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Login Modal */}
      {showLoginModal && (
        <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-green-800 rounded-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-semibold text-green-400 mb-4 tracking-wide">
              AUTHENTICATION REQUIRED
            </h3>
            <p className="text-green-600 mb-6 font-mono">
              Session "{loginParams?.cookie_name}" not found. Manual authentication required to establish secure connection.
            </p>
            <div className="flex space-x-3">
              <button
                onClick={handleManualLogin}
                className="flex-1 bg-green-900 hover:bg-green-800 text-green-400 py-2 px-4 rounded-lg border border-green-600 tracking-wide"
              >
                LAUNCH AUTH
              </button>
              <button
                onClick={handleContinueAfterLogin}
                className="flex-1 bg-cyan-900 hover:bg-cyan-800 text-cyan-400 py-2 px-4 rounded-lg border border-cyan-600 tracking-wide"
              >
                CONTINUE
              </button>
            </div>
            <button
              onClick={() => setShowLoginModal(false)}
              className="w-full mt-3 bg-red-900 hover:bg-red-800 text-red-400 py-2 px-4 rounded-lg border border-red-600 tracking-wide"
            >
              ABORT
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;