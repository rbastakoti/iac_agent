import { theme } from '../../theme.js';
import { useWebSocket } from '../../hooks/useWebSocket.js';

const { useState, useEffect } = React;

export function WorkspacePanel() {
    const [files, setFiles] = useState([]);
    const [workspacePath, setWorkspacePath] = useState('');
    const [loading, setLoading] = useState(true);
    
    const { sendMessage, lastMessage, connected } = useWebSocket();
    
    // Load files when WebSocket connects
    useEffect(() => {
        if (connected) {
            loadWorkspaceFiles();
        }
    }, [connected]);
    
    // Handle incoming WebSocket messages
    useEffect(() => {
        if (!lastMessage) return;
        
        try {
            const message = JSON.parse(lastMessage.data);
            
            if (message.type === 'workspace_files') {
                const filesData = message.payload.files || [];
                setFiles(filesData);
                setLoading(false);
                
                // Set workspace path from first file
                if (filesData.length > 0) {
                    const fullPath = filesData[0].full_path || '';
                    const pathParts = fullPath.split('\\');
                    pathParts.pop(); // Remove filename
                    setWorkspacePath(pathParts.join('\\'));
                }
            }
        } catch (e) {
            console.error('Error parsing workspace panel message:', e);
        }
    }, [lastMessage]);
    
    const loadWorkspaceFiles = () => {
        if (!connected) return;
        setLoading(true);
        sendMessage('list_workspace_files', {}, 'workspace_panel');
    };
    
    const handleFileClick = (filename) => {
        // Dispatch event to open file in HCL File Explorer
        window.dispatchEvent(new CustomEvent('openFileInExplorer', {
            detail: { filename }
        }));
    };
    
    const getFileIcon = (fileName) => {
        if (fileName.endsWith('.tf')) return '🔧';
        if (fileName.endsWith('.tfstate')) return '💾';
        if (fileName.endsWith('.tfvars')) return '⚙️';
        if (fileName.endsWith('.md')) return '📚';
        return '📄';
    };

    return React.createElement('div', {
        style: {
            padding: '16px',
            height: '100%',
            overflow: 'auto'
        }
    }, [
        React.createElement('div', {
            key: 'header',
            style: {
                fontSize: '11px',
                fontWeight: 'bold',
                color: theme.textMuted,
                marginBottom: '12px',
                textTransform: 'uppercase',
                letterSpacing: '1px'
            }
        }, 'Current Workspace'),
        
        React.createElement('div', {
            key: 'status',
            style: {
                padding: '8px 12px',
                background: theme.background,
                border: `1px solid ${theme.border}`,
                borderRadius: '4px',
                marginBottom: '16px',
                fontSize: '12px'
            }
        }, [
            React.createElement('div', { 
                key: 'path',
                style: { 
                    wordBreak: 'break-all',
                    fontSize: '11px'
                }
            }, `📂 ${workspacePath || 'Loading...'}`),
            React.createElement('div', { 
                key: 'status', 
                style: { 
                    marginTop: '4px', 
                    color: connected ? theme.success : theme.textMuted,
                    fontSize: '11px'
                } 
            }, connected ? `✅ ${files.length} files found` : '⏳ Connecting...')
        ]),
        
        React.createElement('div', {
            key: 'files-header',
            style: {
                fontSize: '11px',
                fontWeight: 'bold',
                color: theme.textMuted,
                marginBottom: '8px',
                textTransform: 'uppercase',
                letterSpacing: '1px'
            }
        }, 'Files'),
        
        loading ? 
            React.createElement('div', {
                style: {
                    padding: '16px',
                    textAlign: 'center',
                    color: theme.textMuted,
                    fontSize: '12px'
                }
            }, '⏳ Loading files...') :
            
        React.createElement('div', {
            key: 'files',
            style: { fontSize: '12px' }
        }, files.length > 0 ? files.map(file =>
            React.createElement('div', {
                key: file.name,
                onClick: () => handleFileClick(file.name),
                style: {
                    padding: '4px 8px',
                    cursor: 'pointer',
                    borderRadius: '3px',
                    color: theme.text,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '8px'
                },
                onMouseEnter: (e) => e.target.style.backgroundColor = theme.hover,
                onMouseLeave: (e) => e.target.style.backgroundColor = 'transparent'
            }, [
                React.createElement('div', {
                    key: 'info',
                    style: {
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        flex: 1,
                        overflow: 'hidden'
                    }
                }, [
                    React.createElement('span', { key: 'icon' }, getFileIcon(file.name)),
                    React.createElement('span', { 
                        key: 'name',
                        style: {
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                        }
                    }, file.name)
                ]),
                React.createElement('span', {
                    key: 'size',
                    style: {
                        fontSize: '10px',
                        color: theme.textMuted,
                        flexShrink: 0
                    }
                }, `${Math.round((file.size || 0) / 1024)}KB`)
            ])
        ) : React.createElement('div', {
            style: {
                padding: '16px',
                textAlign: 'center',
                color: theme.textMuted,
                fontSize: '12px'
            }
        }, '📁 No files found'))
    ]);
}