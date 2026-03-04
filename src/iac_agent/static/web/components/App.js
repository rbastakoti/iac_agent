import { theme } from '../theme.js';
import { useWebSocket } from '../hooks/useWebSocket.js';
import { ActivityBar } from './ActivityBar.js';
import { SidePanel } from './SidePanel.js';
import { ResizableQuadPane } from './ResizableQuadPane.js';
import { AIConversation } from './workspace/AIConversation.js';
import { DirectTerminal } from './workspace/DirectTerminal.js';
import { HCLEditor } from './workspace/HCLEditor.js';
import { ResourceGraph } from './workspace/ResourceGraph.js';

const { useState, useEffect, useCallback } = React;

export function App() {
    const { socket, connected, messages, sendMessage } = useWebSocket();
    const [activePanel, setActivePanel] = useState('workspace');
    const [sidebarCollapsed, setSidebarCollapsed] = useState(true);
    const [sidebarWidth] = useState(300);
    const [currentModel, setCurrentModel] = useState('gpt-4o-mini');
    const [lastProcessedIndex, setLastProcessedIndex] = useState(-1);
    const [chatMessages, setChatMessages] = useState([
        { 
            role: 'system', 
            content: 'Welcome to IaC Agent! I can help you design, deploy, and manage infrastructure.\n\nTry asking:\n• "Show me my Azure resources"\n• "Create a new virtual network"\n• "Import my production environment"',
            timestamp: new Date().toLocaleTimeString()
        }
    ]);
    
    // Load current model configuration on startup
    useEffect(() => {
        const loadCurrentModel = async () => {
            try {
                const response = await fetch('/api/llm/config');
                if (response.ok) {
                    const config = await response.json();
                    if (config.is_configured && config.model_name) {
                        setCurrentModel(config.model_name);
                    }
                }
            } catch (error) {
                console.log('Failed to load model config:', error);
            }
        };
        loadCurrentModel();
    }, []);
    
    useEffect(() => {
        // Process only new messages since last processed index
        for (let i = lastProcessedIndex + 1; i < messages.length; i++) {
            const message = messages[i];
            
            if (message.type === 'chat_response') {
                setChatMessages(prev => [...prev, {
                    role: 'assistant',
                    content: message.payload.content,
                    timestamp: new Date().toLocaleTimeString()
                }]);
            }
        }
        
        // Update last processed index
        if (messages.length > 0) {
            setLastProcessedIndex(messages.length - 1);
        }
    }, [messages]);
    
    const handleSendMessage = useCallback((type, payload) => {
        if (type === 'chat_message') {
            setChatMessages(prev => [...prev, {
                role: 'user',
                content: payload.content,
                timestamp: new Date().toLocaleTimeString()
            }]);
        }
        sendMessage(type, payload);
    }, [sendMessage]);

    const handleToggleSidebar = () => {
        setSidebarCollapsed(!sidebarCollapsed);
    };
    
    const handleModelUpdate = (newModel) => {
        setCurrentModel(newModel);
    };

    const currentSidebarWidth = sidebarCollapsed ? 0 : sidebarWidth;
    
    return React.createElement('div', {
        style: {
            display: 'flex',
            height: '100vh',
            background: theme.background,
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Ubuntu", "Cantarell", sans-serif'
        }
    }, [
        // Activity Bar (always visible)
        React.createElement(ActivityBar, {
            key: 'activity-bar',
            activePanel: activePanel,
            onPanelChange: setActivePanel,
            sidebarCollapsed: sidebarCollapsed,
            onToggleSidebar: handleToggleSidebar
        }),
        
        // Side Panel (collapsible)
        React.createElement(SidePanel, {
            key: 'side-panel',
            activePanel: activePanel,
            collapsed: sidebarCollapsed,
            width: sidebarWidth,
            onModelUpdate: handleModelUpdate
        }),
        
        // Main Workspace (quad-pane)
        React.createElement(ResizableQuadPane, {
            key: 'main-workspace',
            sidebarWidth: currentSidebarWidth
        }, [
            // Top-Left: AI Conversation
            React.createElement(AIConversation, {
                key: 'ai-chat',
                messages: chatMessages,
                onSendMessage: handleSendMessage,
                connected: connected,
                currentModel: currentModel
            }),
            
            // Top-Right: HCL Editor
            React.createElement(HCLEditor, {
                key: 'hcl-editor'
            }),
            
            // Bottom-Left: Terminal
            React.createElement(DirectTerminal, {
                key: 'terminal'
            }),
            
            // Bottom-Right: Resource Graph
            React.createElement(ResourceGraph, {
                key: 'resource-graph'
            })
        ])
    ]);
}