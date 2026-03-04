import { theme } from '../../theme.js';

const { useState, useEffect, useRef } = React;

export function DirectTerminal() {
    const terminalRef = useRef(null);
    const [terminal, setTerminal] = useState(null);
    const [fitAddon, setFitAddon] = useState(null);
    const [ptySessionId, setPtySessionId] = useState(null);
    const ptySessionIdRef = useRef(null);
    const [connectionStatus, setConnectionStatus] = useState('initializing');
    const [retryCount, setRetryCount] = useState(0);

    useEffect(() => {
        initializeTerminal();
        
        return () => {
            if (terminal) {
                terminal.dispose();
            }
        };
    }, []);

    const initializeTerminal = async () => {
        // Wait for libraries to load
        await waitForLibraries();
        
        if (!window.Terminal || !window.FitAddon) {
            setConnectionStatus('error');
            showErrorMessage('Terminal libraries not available');
            return;
        }

        try {
            // Create terminal instance with enhanced configuration
            const term = new window.Terminal({
                theme: {
                    background: '#0c0c0c',
                    foreground: '#cccccc',
                    cursor: '#cccccc',
                    selection: '#264f78',
                    black: '#0c0c0c',
                    red: '#c50f1f',
                    green: '#13a10e',
                    yellow: '#c19c00',
                    blue: '#0037da',
                    magenta: '#881798',
                    cyan: '#3a96dd',
                    white: '#cccccc',
                    brightBlack: '#767676',
                    brightRed: '#e74856',
                    brightGreen: '#16c60c',
                    brightYellow: '#f9f1a5',
                    brightBlue: '#3b78ff',
                    brightMagenta: '#b4009e',
                    brightCyan: '#61d6d6',
                    brightWhite: '#f2f2f2'
                },
                fontFamily: 'Consolas, "Courier New", monospace',
                fontSize: 14,
                lineHeight: 1.2,
                cursorBlink: true,
                cursorStyle: 'block',
                scrollback: 10000,
                allowTransparency: false,
                macOptionIsMeta: true
            });

            // Add fit addon
            const fit = new window.FitAddon.FitAddon();
            term.loadAddon(fit);

            // Add web links addon if available
            if (window.WebLinksAddon) {
                const webLinks = new window.WebLinksAddon.WebLinksAddon();
                term.loadAddon(webLinks);
            }

            // Open terminal in container
            term.open(terminalRef.current);
            fit.fit();
            
            // Show welcome message
            term.writeln('\x1b[32mIaC Agent Terminal\x1b[0m');
            term.writeln('\x1b[90mConnecting to shell...\x1b[0m');

            // Handle user input with better error handling
            term.onData(data => {
                if (ptySessionIdRef.current && window.wsManager?.connected) {
                    try {
                        window.wsManager.send({
                            type: 'pty_write',
                            payload: {
                                pty_session_id: ptySessionIdRef.current,
                                data: data
                            }
                        });
                    } catch (error) {
                        console.error('Error sending input to terminal:', error);
                        showTerminalError('Failed to send input to terminal');
                    }
                } else if (!ptySessionIdRef.current) {
                    showTerminalError('Terminal session not established');
                } else if (!window.wsManager?.connected) {
                    showTerminalError('WebSocket disconnected');
                }
            });

            // Handle terminal resize with better error handling
            term.onResize(({ cols, rows }) => {
                if (ptySessionIdRef.current && window.wsManager?.connected) {
                    try {
                        window.wsManager.send({
                            type: 'pty_resize',
                            payload: {
                                pty_session_id: ptySessionIdRef.current,
                                cols: cols,
                                rows: rows
                            }
                        });
                    } catch (error) {
                        console.error('Error resizing terminal:', error);
                    }
                }
            });

            setTerminal(term);
            setFitAddon(fit);
            setConnectionStatus('terminal_ready');

            // Start PTY session
            startPTYSession();

        } catch (error) {
            console.error('Failed to initialize terminal:', error);
            setConnectionStatus('error');
            setRetryCount(prev => prev + 1);
        }
    };
    
    const showTerminalError = (message) => {
        if (terminal) {
            terminal.writeln(`\r\n\x1b[31m[Error] ${message}\x1b[0m`);
            terminal.scrollToBottom();
        }
    };
    
    const showErrorMessage = (message) => {
        if (terminal) {
            terminal.writeln(`\r\n\x1b[31m${message}\x1b[0m\r\n`);
            terminal.scrollToBottom();
        }
        console.error(message);
    };

    const waitForLibraries = () => {
        return new Promise((resolve, reject) => {
            let attempts = 0;
            const maxAttempts = 20; // 2 seconds total

            const checkLibraries = () => {
                if (window.Terminal && window.FitAddon) {
                    resolve();
                } else if (attempts >= maxAttempts) {
                    reject(new Error('xterm.js libraries failed to load'));
                } else {
                    attempts++;
                    setTimeout(checkLibraries, 100);
                }
            };

            checkLibraries();
        });
    };

    const startPTYSession = async () => {
        // Wait for WebSocket connection
        if (!window.wsManager?.connected) {
            if (retryCount < 10) {
                setTimeout(() => {
                    setRetryCount(prev => prev + 1);
                    startPTYSession();
                }, 1000);
                return;
            } else {
                setConnectionStatus('error');
                showErrorMessage('WebSocket connection failed after multiple attempts');
                return;
            }
        }

        setConnectionStatus('connecting');
        
        try {
            // Get terminal dimensions
            const cols = terminal?.cols || 80;
            const rows = terminal?.rows || 24;
            
            // Send PTY spawn request to main WebSocket endpoint
            window.wsManager.send({
                type: 'pty_spawn',
                payload: {
                    shell: 'powershell.exe',  // Explicitly specify PowerShell
                    cwd: null,
                    cols: cols,
                    rows: rows
                }
            });
        } catch (error) {
            console.error('Error starting PTY session:', error);
            setConnectionStatus('error');
            showErrorMessage(`Failed to start terminal: ${error.message}`);
        }
    };

    // Handle window resize
    useEffect(() => {
        const handleResize = () => {
            if (fitAddon && terminal) {
                setTimeout(() => fitAddon.fit(), 100);
            }
        };

        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, [fitAddon, terminal]);

    // Handle WebSocket messages
    useEffect(() => {
        const handlePTYSpawn = (data) => {
            if (data.success) {
                setPtySessionId(data.pty_session_id);
                ptySessionIdRef.current = data.pty_session_id;
                setConnectionStatus('connected');
                setRetryCount(0);  // Reset retry count on success
                
                if (terminal) {
                    terminal.clear();
                    terminal.writeln('\x1b[32m✓ Terminal session established\x1b[0m');
                    terminal.writeln('\x1b[90mPress any key to continue...\x1b[0m\r\n');
                    terminal.scrollToBottom();
                }
            } else {
                setConnectionStatus('error');
                const errorMsg = data.error || 'Unknown error occurred';
                showErrorMessage(`Failed to spawn shell: ${errorMsg}`);
                
                // Auto-retry on certain errors
                if (retryCount < 3 && (errorMsg.includes('winpty') || errorMsg.includes('connection'))) {
                    setTimeout(() => {
                        setRetryCount(prev => prev + 1);
                        initializeTerminal();
                    }, 2000);
                }
            }
        };

        const handlePTYOutput = (data) => {
            if (terminal && ptySessionIdRef.current === data.pty_session_id) {
                try {
                    terminal.write(data.data);
                    // Auto-scroll to bottom to show latest content
                    terminal.scrollToBottom();
                } catch (error) {
                    console.error('Error writing to terminal:', error);
                    showTerminalError('Terminal display error');
                }
            }
        };
        
        const handleConnectionLost = () => {
            setConnectionStatus('disconnected');
            if (terminal) {
                terminal.writeln('\r\n\x1b[31m[Connection Lost] Attempting to reconnect...\x1b[0m\r\n');
                terminal.scrollToBottom();
            }
            
            // Clean up current session
            setPtySessionId(null);
            ptySessionIdRef.current = null;
            
            // Attempt to reconnect after delay
            setTimeout(() => {
                if (retryCount < 5) {
                    setRetryCount(prev => prev + 1);
                    startPTYSession();
                }
            }, 3000);
        };

        // Set global message handlers
        window.handlePTYSpawn = handlePTYSpawn;
        window.handlePTYOutput = handlePTYOutput;
        window.handleConnectionLost = handleConnectionLost;

        return () => {
            window.handlePTYSpawn = null;
            window.handlePTYOutput = null;
            window.handleConnectionLost = null;
        };
    }, [terminal, retryCount]);

    const getStatusColor = () => {
        switch (connectionStatus) {
            case 'connected': return '#4ec9b0';
            case 'connecting': return '#ffa500';
            case 'disconnected': return '#ff6b6b';
            case 'error': return '#f44747';
            case 'terminal_ready': return '#569cd6';
            default: return '#cccccc';
        }
    };

    const getStatusText = () => {
        switch (connectionStatus) {
            case 'connected': return '● Connected';
            case 'connecting': return '● Connecting...';
            case 'disconnected': return '● Disconnected';
            case 'terminal_ready': return '● Ready';
            case 'error': return `● Error ${retryCount > 0 ? `(${retryCount})` : ''}`;
            default: return '● Initializing...';
        }
    };
    
    const canRetry = () => {
        return ['error', 'disconnected'].includes(connectionStatus) && retryCount < 5;
    };
    
    const handleRetry = () => {
        setConnectionStatus('initializing');
        setRetryCount(0);
        setPtySessionId(null);
        ptySessionIdRef.current = null;
        initializeTerminal();
    };
    
    const handleClearTerminal = () => {
        if (terminal) {
            terminal.clear();
            terminal.writeln('\x1b[32mTerminal cleared\x1b[0m');
            terminal.scrollToBottom();
        }
    };

    return React.createElement('div', {
        style: {
            background: theme.background,
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            borderRadius: '6px',
            border: `1px solid ${theme.border}`
        }
    }, [
        // Header
        React.createElement('div', {
            key: 'header',
            style: {
                background: theme.panel,
                color: theme.textMuted,
                padding: '8px 16px',
                borderBottom: `1px solid ${theme.border}`,
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                flexShrink: 0
            }
        }, [
            React.createElement('div', {
                key: 'icon',
                style: { color: theme.accent }
            }, '⚡'),
            React.createElement('span', { 
                key: 'title' 
            }, 'Terminal'),
            React.createElement('span', {
                key: 'status',
                style: {
                    marginLeft: 'auto',
                    fontSize: '10px',
                    color: getStatusColor(),
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                }
            }, [
                getStatusText(),
                // Terminal controls
                connectionStatus === 'connected' && React.createElement('button', {
                    key: 'clear',
                    onClick: handleClearTerminal,
                    title: 'Clear Terminal',
                    style: {
                        background: 'none',
                        border: 'none',
                        color: theme.textMuted,
                        cursor: 'pointer',
                        fontSize: '10px',
                        padding: '2px 4px',
                        borderRadius: '2px'
                    }
                }, '🗑'),
                canRetry() && React.createElement('button', {
                    key: 'retry-btn',
                    onClick: handleRetry,
                    title: 'Retry Connection',
                    style: {
                        background: theme.accent,
                        border: 'none',
                        color: 'white',
                        cursor: 'pointer',
                        fontSize: '10px',
                        padding: '2px 6px',
                        borderRadius: '2px'
                    }
                }, '↻')
            ])
        ]),

        // Terminal container
        React.createElement('div', {
            key: 'terminal',
            ref: terminalRef,
            style: {
                flex: 1,
                minHeight: 0,
                background: '#0c0c0c',
                overflow: 'hidden'
            }
        }),

        // Error/Loading overlay
        (['error', 'disconnected', 'connecting'].includes(connectionStatus)) && React.createElement('div', {
            key: 'overlay',
            style: {
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(0, 0, 0, 0.8)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 10
            }
        }, React.createElement('div', {
            style: {
                background: theme.panel,
                color: theme.text,
                textAlign: 'center',
                fontFamily: 'Consolas, monospace',
                fontSize: '14px',
                padding: '24px',
                borderRadius: '8px',
                border: `2px solid ${getStatusColor()}`,
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)'
            }
        }, [
            React.createElement('div', {
                key: 'icon',
                style: { fontSize: '24px', marginBottom: '12px', color: getStatusColor() }
            }, connectionStatus === 'connecting' ? '⏳' : connectionStatus === 'error' ? '⚠️' : '📡'),
            React.createElement('div', {
                key: 'title',
                style: { fontSize: '16px', marginBottom: '8px', fontWeight: 'bold' }
            }, 
                connectionStatus === 'connecting' ? 'Connecting to Terminal' :
                connectionStatus === 'error' ? 'Terminal Connection Failed' : 
                'Terminal Disconnected'
            ),
            React.createElement('div', {
                key: 'message',
                style: { marginBottom: '16px', opacity: 0.8 }
            }, 
                connectionStatus === 'connecting' ? 'Setting up PowerShell session...' :
                connectionStatus === 'error' ? `Attempt ${retryCount}/5 failed` :
                'Connection to terminal lost'
            ),
            connectionStatus !== 'connecting' && React.createElement('div', {
                key: 'actions',
                style: { display: 'flex', gap: '8px', justifyContent: 'center' }
            }, [
                canRetry() && React.createElement('button', {
                    key: 'retry',
                    onClick: handleRetry,
                    style: {
                        padding: '8px 16px',
                        background: theme.accent,
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '12px'
                    }
                }, 'Retry Connection'),
                React.createElement('button', {
                    key: 'console',
                    onClick: () => {
                        console.log('Terminal state:', {
                            connectionStatus,
                            retryCount,
                            ptySessionId,
                            wsConnected: window.wsManager?.connected
                        });
                    },
                    style: {
                        padding: '8px 16px',
                        background: 'transparent',
                        color: theme.textMuted,
                        border: `1px solid ${theme.border}`,
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '12px'
                    }
                }, 'Debug Info')
            ])
        ]))
    ]);
}
