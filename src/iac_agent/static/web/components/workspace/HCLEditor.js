import { theme } from '../../theme.js';
import { useWebSocket } from '../../hooks/useWebSocket.js';

const { useState, useEffect, useRef } = React;

export function HCLEditor() {
    // Core state
    const [workspaceFiles, setWorkspaceFiles] = useState([]);
    const [selectedFile, setSelectedFile] = useState(null);
    const [fileContent, setFileContent] = useState('');
    const [editedContent, setEditedContent] = useState('');
    const [isDirty, setIsDirty] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [saveStatus, setSaveStatus] = useState(null);
    const [error, setError] = useState(null);
    
    // File creation state
    const [showNewFileDialog, setShowNewFileDialog] = useState(false);
    const [newFileName, setNewFileName] = useState('');
    const [newFileContent, setNewFileContent] = useState('');
    const [selectedFolder, setSelectedFolder] = useState('');
    
    // Expanded folders for tree view
    const [expandedFolders, setExpandedFolders] = useState(new Set());
    
    // Sidebar collapse state - collapsed by default
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true);
    
    const { sendMessage, lastMessage, connected } = useWebSocket();
    const editorRef = useRef(null);

    // Load workspace files on mount
    useEffect(() => {
        if (connected) {
            loadWorkspaceFiles();
        }
    }, [connected]);

    // Handle WebSocket messages
    useEffect(() => {
        if (!lastMessage) return;
        
        try {
            const message = JSON.parse(lastMessage.data);
            handleWebSocketMessage(message);
        } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
        }
    }, [lastMessage]);

    const handleWebSocketMessage = (message) => {
        console.log('🔔 HCLEditor received message:', message);
        
        switch (message.type) {
            case 'workspace_files':
                setWorkspaceFiles(message.payload.files || []);
                setIsLoading(false);
                console.log('📁 Loaded workspace files:', message.payload.files?.length || 0);
                break;
                
            case 'workspace_file_content':
                const { filename, content } = message.payload;
                setFileContent(content);
                setEditedContent(content);
                setIsDirty(false);
                setSelectedFile(filename);
                console.log(`📄 Opened file: ${filename} (${content.length} chars)`);
                
                // Auto-save when opening file
                setTimeout(() => {
                    saveFile();
                }, 100);
                break;
                
            case 'file_saved':
                setIsDirty(false);
                clearSaveStatusAfterDelay();
                console.log(`💾 Saved file: ${message.payload.filename}`);
                // Refresh file list to show new files
                loadWorkspaceFiles();
                break;
                
            case 'file_created':
                setSaveStatus({ type: 'success', message: `Created ${message.payload.filename}` });
                setShowNewFileDialog(false);
                setNewFileName('');
                setNewFileContent('');
                clearSaveStatusAfterDelay();
                // Open the newly created file
                openFile(message.payload.filename);
                // Refresh file list
                loadWorkspaceFiles();
                break;
                
            case 'error':
                const errorMsg = message.payload?.message || 'An error occurred';
                setError(errorMsg);
                setSaveStatus({ type: 'error', message: errorMsg });
                clearSaveStatusAfterDelay();
                break;
        }
    };

    const clearSaveStatusAfterDelay = () => {
        setTimeout(() => {
            setSaveStatus(null);
            setError(null);
        }, 3000);
    };

    const loadWorkspaceFiles = () => {
        if (!connected) return;
        setIsLoading(true);
        console.log('📂 Loading workspace files...');
        sendMessage('list_workspace_files', {}, 'hcl_editor');
    };

    const openFile = (filename) => {
        if (!connected) return;
        
        // Check for unsaved changes
        if (isDirty && selectedFile) {
            const confirmDiscard = confirm(`You have unsaved changes in ${selectedFile}. Discard changes?`);
            if (!confirmDiscard) return;
        }
        
        console.log(`📖 Opening file: ${filename}`);
        sendMessage('read_workspace_file', { filename }, 'hcl_editor');
    };

    const saveFile = () => {
        if (!connected || !selectedFile) return;
        
        console.log(`💾 Saving file: ${selectedFile} (${editedContent.length} chars)`);
        sendMessage('save_workspace_file', {
            filename: selectedFile,
            content: editedContent
        }, 'hcl_editor');
    };

    const createNewFile = () => {
        if (!connected || !newFileName.trim()) return;
        
        const fullPath = selectedFolder ? `${selectedFolder}/${newFileName}` : newFileName;
        
        sendMessage('create_workspace_file', {
            filename: fullPath,
            content: newFileContent
        }, 'hcl_editor');
    };

    const handleContentChange = (e) => {
        const newContent = e.target.value;
        setEditedContent(newContent);
        setIsDirty(newContent !== fileContent);
    };

    const handleKeyDown = (e) => {
        // Ctrl+S to save
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            saveFile();
        }
        
        // Tab support
        if (e.key === 'Tab') {
            e.preventDefault();
            const start = e.target.selectionStart;
            const end = e.target.selectionEnd;
            const newContent = editedContent.substring(0, start) + '  ' + editedContent.substring(end);
            setEditedContent(newContent);
            setIsDirty(newContent !== fileContent);
            
            // Reset cursor position
            setTimeout(() => {
                e.target.selectionStart = e.target.selectionEnd = start + 2;
            }, 0);
        }
    };

    const toggleFolder = (folderPath) => {
        const newExpanded = new Set(expandedFolders);
        if (newExpanded.has(folderPath)) {
            newExpanded.delete(folderPath);
        } else {
            newExpanded.add(folderPath);
        }
        setExpandedFolders(newExpanded);
    };

    const renderFileTreeHorizontal = (files, basePath = '') => {
        const allFiles = [];
        
        const collectFiles = (items, path = '') => {
            items.forEach(item => {
                const fullPath = path ? `${path}/${item.name}` : item.name;
                if (item.type === 'directory' && item.children && expandedFolders.has(fullPath)) {
                    collectFiles(item.children, fullPath);
                } else if (item.type === 'file') {
                    allFiles.push(fullPath);
                }
            });
        };
        
        collectFiles(files);
        
        return React.createElement('div', {
            style: {
                display: 'flex',
                flexWrap: 'wrap',
                gap: '6px',
                alignItems: 'center'
            }
        }, allFiles.map(filePath => 
            React.createElement('button', {
                key: filePath,
                onClick: () => openFile(filePath),
                style: {
                    background: selectedFile === filePath ? '#007acc' : '#3c3c3c',
                    color: selectedFile === filePath ? 'white' : '#d4d4d4',
                    border: '1px solid ' + (selectedFile === filePath ? '#007acc' : '#555'),
                    padding: '4px 8px',
                    borderRadius: '3px',
                    fontSize: '11px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    maxWidth: '150px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                }
            }, [
                React.createElement('span', {
                    key: 'icon',
                    style: { fontSize: '10px' }
                }, '📄'),
                React.createElement('span', { key: 'name' }, filePath.split('/').pop()),
                selectedFile === filePath && isDirty ? React.createElement('span', {
                    key: 'dirty',
                    style: { color: '#ffa500', fontSize: '8px', marginLeft: '2px' }
                }, '●') : null
            ])
        ));
    };

    const renderFolderChips = (files, basePath = '') => {
        const folders = files.filter(item => item.type === 'directory');
        
        return React.createElement('div', {
            style: {
                display: 'flex',
                flexWrap: 'wrap',
                gap: '4px',
                marginBottom: '8px'
            }
        }, folders.map(folder => {
            const fullPath = basePath ? `${basePath}/${folder.name}` : folder.name;
            const isExpanded = expandedFolders.has(fullPath);
            
            return React.createElement('button', {
                key: fullPath,
                onClick: () => toggleFolder(fullPath),
                style: {
                    background: isExpanded ? '#007acc' : '#444',
                    color: isExpanded ? 'white' : '#ccc',
                    border: 'none',
                    padding: '3px 6px',
                    borderRadius: '3px',
                    fontSize: '10px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '3px'
                }
            }, [
                React.createElement('span', {
                    key: 'icon',
                    style: { fontSize: '9px' }
                }, isExpanded ? '📂' : '📁'),
                React.createElement('span', { key: 'name' }, folder.name)
            ]);
        }));
    };

    return React.createElement('div', {
        style: {
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            background: theme.background,
            color: theme.text
        }
    }, [
        // File Explorer Tab Bar
        React.createElement('div', {
            key: 'tab-bar',
            style: {
                display: 'flex',
                alignItems: 'center',
                background: '#2d2d30',
                borderBottom: '1px solid #333',
                padding: '4px 12px',
                gap: '8px'
            }
        }, [
            // Explorer Tab Toggle
            React.createElement('button', {
                key: 'explorer-tab',
                onClick: () => setIsSidebarCollapsed(!isSidebarCollapsed),
                style: {
                    background: !isSidebarCollapsed ? '#007acc' : 'transparent',
                    color: !isSidebarCollapsed ? 'white' : '#cccccc',
                    border: '1px solid ' + (!isSidebarCollapsed ? '#007acc' : '#555'),
                    padding: '3px 8px',
                    borderRadius: '2px',
                    fontSize: '10px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                }
            }, ['📁', 'Explorer']),
            
            // New File button (always visible)
            React.createElement('button', {
                key: 'new-file-tab',
                onClick: () => setShowNewFileDialog(true),
                style: {
                    background: '#007acc',
                    color: 'white',
                    border: 'none',
                    padding: '3px 8px',
                    borderRadius: '2px',
                    fontSize: '10px',
                    cursor: 'pointer'
                }
            }, '+ New')
        ]),
        
        // File Explorer Panel (collapsible)
        !isSidebarCollapsed ? React.createElement('div', {
            key: 'explorer-panel',
            style: {
                background: '#1e1e1e',
                borderBottom: '1px solid #333',
                padding: '8px 16px',
                position: 'relative'
            }
        }, [
            React.createElement('div', {
                key: 'explorer-content',
                style: {
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px'
                }
            }, [
                // Folder chips row
                React.createElement('div', {
                    key: 'folders-section',
                    style: {
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: '11px'
                    }
                }, [
                    React.createElement('span', {
                        key: 'folders-label',
                        style: { color: '#888', minWidth: '50px' }
                    }, 'Folders:'),
                    isLoading ? 
                        React.createElement('span', { style: { color: '#888' } }, 'Loading...') :
                        renderFolderChips(workspaceFiles)
                ]),
                
                // Files row
                React.createElement('div', {
                    key: 'files-section',
                    style: {
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '8px',
                        fontSize: '11px'
                    }
                }, [
                    React.createElement('span', {
                        key: 'files-label',
                        style: { color: '#888', minWidth: '50px', paddingTop: '4px' }
                    }, 'Files:'),
                    React.createElement('div', {
                        key: 'files-container',
                        style: { flex: 1 }
                    }, isLoading ? 
                        React.createElement('span', { style: { color: '#888' } }, 'Loading...') :
                        renderFileTreeHorizontal(workspaceFiles)
                    )
                ])
            ]),
            
            // Quick collapse button
            React.createElement('button', {
                key: 'collapse-btn',
                onClick: () => setIsSidebarCollapsed(true),
                style: {
                    position: 'absolute',
                    right: '8px',
                    top: '8px',
                    background: 'transparent',
                    color: '#888',
                    border: 'none',
                    padding: '2px 4px',
                    fontSize: '12px',
                    cursor: 'pointer',
                    borderRadius: '2px'
                },
                title: 'Collapse Explorer'
            }, '×')
        ]) : null,
        
        // Editor Area
        React.createElement('div', {
            key: 'editor-area',
            style: {
                flex: 1,
                display: 'flex',
                flexDirection: 'column'
            }
        }, [
            // Editor Header
            React.createElement('div', {
                key: 'editor-header',
                style: {
                    padding: '4px 12px',
                    borderBottom: '1px solid #333',
                    background: '#2d2d30',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }
            }, [
                React.createElement('div', {
                    key: 'file-info',
                    style: { display: 'flex', alignItems: 'center' }
                }, [
                    React.createElement('span', {
                        key: 'filename',
                        style: { fontWeight: 'bold', color: '#cccccc', fontSize: '11px' }
                    }, selectedFile ? `📝 ${selectedFile}` : 'No file selected'),
                    
                    isDirty ? React.createElement('span', {
                        key: 'dirty-indicator',
                        style: { marginLeft: '6px', color: '#ffa500', fontSize: '10px' }
                    }, '●') : null
                ]),
                
                selectedFile ? React.createElement('div', {
                    key: 'actions',
                    style: { display: 'flex', gap: '6px' }
                }, [
                    React.createElement('button', {
                        key: 'save',
                        onClick: saveFile,
                        disabled: !isDirty,
                        style: {
                            background: isDirty ? '#007acc' : '#444',
                            color: isDirty ? 'white' : '#888',
                            border: 'none',
                            padding: '3px 8px',
                            borderRadius: '2px',
                            fontSize: '10px',
                            cursor: isDirty ? 'pointer' : 'default'
                        }
                    }, 'Save (Ctrl+S)'),
                    
                    React.createElement('span', {
                        key: 'stats',
                        style: { fontSize: '9px', color: '#888', alignSelf: 'center' }
                    }, `${editedContent.split('\n').length} lines`)
                ]) : null
            ]),
            
            // Status Bar
            saveStatus ? React.createElement('div', {
                key: 'status',
                style: {
                    padding: '2px 12px',
                    background: saveStatus.type === 'success' ? '#1f5f2d' : '#722d2d',
                    color: 'white',
                    fontSize: '10px',
                    borderBottom: '1px solid #333'
                }
            }, saveStatus.message) : null,
            
            // Editor
            React.createElement('div', {
                key: 'editor',
                style: { flex: 1, position: 'relative' }
            }, selectedFile ? 
                React.createElement('textarea', {
                    ref: editorRef,
                    value: editedContent,
                    onChange: handleContentChange,
                    onKeyDown: handleKeyDown,
                    placeholder: 'Start typing...',
                    spellCheck: false,
                    style: {
                        width: '100%',
                        height: '100%',
                        border: 'none',
                        outline: 'none',
                        resize: 'none',
                        padding: '16px',
                        fontSize: '12px',
                        fontFamily: "'Fira Code', 'JetBrains Mono', 'SF Mono', 'Cascadia Code', 'Consolas', 'Monaco', 'Courier New', monospace",
                        fontWeight: '400',
                        lineHeight: '1.4',
                        background: '#1e1e1e',
                        color: '#d4d4d4',
                        tabSize: 2
                    }
                }) :
                React.createElement('div', {
                    style: {
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        height: '100%',
                        color: '#888',
                        fontSize: '16px'
                    }
                }, 'Select a file to start editing')
            )
        ]),
        
        // New File Dialog
        showNewFileDialog ? React.createElement('div', {
            key: 'dialog-overlay',
            style: {
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(0,0,0,0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 1000
            },
            onClick: (e) => {
                if (e.target === e.currentTarget) {
                    setShowNewFileDialog(false);
                }
            }
        }, React.createElement('div', {
            style: {
                background: '#2d2d30',
                border: '1px solid #444',
                borderRadius: '6px',
                padding: '20px',
                width: '400px',
                maxWidth: '90vw'
            }
        }, [
            React.createElement('h3', {
                key: 'title',
                style: { margin: '0 0 16px 0', color: '#cccccc' }
            }, 'Create New File'),
            
            React.createElement('div', {
                key: 'folder-info',
                style: { marginBottom: '12px', fontSize: '12px', color: '#888' }
            }, `Creating in: ${selectedFolder || 'workspace root'}`),
            
            React.createElement('input', {
                key: 'filename',
                type: 'text',
                placeholder: 'Enter filename (e.g. main.tf)',
                value: newFileName,
                onChange: (e) => setNewFileName(e.target.value),
                style: {
                    width: '100%',
                    padding: '8px',
                    marginBottom: '12px',
                    background: '#1e1e1e',
                    border: '1px solid #444',
                    borderRadius: '3px',
                    color: '#d4d4d4',
                    fontSize: '14px'
                },
                autoFocus: true
            }),
            
            React.createElement('textarea', {
                key: 'content',
                placeholder: 'Initial file content (optional)',
                value: newFileContent,
                onChange: (e) => setNewFileContent(e.target.value),
                spellCheck: false,
                style: {
                    width: '100%',
                    height: '100px',
                    padding: '8px',
                    marginBottom: '16px',
                    background: '#1e1e1e',
                    border: '1px solid #444',
                    borderRadius: '3px',
                    color: '#d4d4d4',
                    fontSize: '12px',
                    fontFamily: "'Fira Code', 'JetBrains Mono', 'SF Mono', 'Cascadia Code', 'Consolas', 'Monaco', 'Courier New', monospace",
                    fontWeight: '400',
                    resize: 'vertical'
                }
            }),
            
            React.createElement('div', {
                key: 'actions',
                style: { display: 'flex', gap: '8px', justifyContent: 'flex-end' }
            }, [
                React.createElement('button', {
                    key: 'cancel',
                    onClick: () => setShowNewFileDialog(false),
                    style: {
                        background: '#444',
                        color: '#ccc',
                        border: 'none',
                        padding: '8px 16px',
                        borderRadius: '3px',
                        cursor: 'pointer'
                    }
                }, 'Cancel'),
                
                React.createElement('button', {
                    key: 'create',
                    onClick: createNewFile,
                    disabled: !newFileName.trim(),
                    style: {
                        background: newFileName.trim() ? '#007acc' : '#444',
                        color: newFileName.trim() ? 'white' : '#888',
                        border: 'none',
                        padding: '8px 16px',
                        borderRadius: '3px',
                        cursor: newFileName.trim() ? 'pointer' : 'default'
                    }
                }, 'Create File')
            ])
        ])) : null
    ]);
}
