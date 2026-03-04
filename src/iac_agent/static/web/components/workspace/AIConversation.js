import { theme } from '../../theme.js';

const { useState, useEffect, useRef } = React;

export function AIConversation({ messages, onSendMessage, connected, currentModel = 'gpt-4o-mini' }) {
    const [input, setInput] = useState('');
    const [isStreaming, setIsStreaming] = useState(false);
    const messagesEndRef = useRef(null);
    
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);
    
    const handleSend = () => {
        if (input.trim() && connected) {
            onSendMessage('chat_message', { content: input.trim() });
            setInput('');
        }
    };
    
    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };
    
    return React.createElement('div', {
        style: {
            background: theme.panel,
            display: 'flex',
            flexDirection: 'column',
            height: '100%'
        }
    }, [
        // Header
        React.createElement('div', {
            key: 'header',
            style: {
                padding: '8px 12px',
                borderBottom: `1px solid ${theme.border}`,
                background: theme.background,
                color: theme.text,
                fontSize: '13px',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
            }
        }, [
            React.createElement('span', { key: 'icon' }, '💬'),
            'AI Conversation',
            React.createElement('span', {
                key: 'model',
                style: {
                    marginLeft: '8px',
                    padding: '2px 6px',
                    background: connected ? theme.accent + '20' : theme.error + '20',
                    color: connected ? theme.accent : theme.error,
                    fontSize: '10px',
                    borderRadius: '3px',
                    fontWeight: '500'
                }
            }, connected ? currentModel : 'not connected'),
            React.createElement('div', {
                key: 'status',
                style: {
                    marginLeft: 'auto',
                    padding: '2px 6px',
                    borderRadius: '10px',
                    background: connected ? theme.success : theme.error,
                    color: 'white',
                    fontSize: '10px'
                }
            }, connected ? '●' : '○')
        ]),
        
        // Messages area
        React.createElement('div', {
            key: 'messages',
            style: {
                flex: 1,
                padding: '12px',
                overflowY: 'auto',
                background: theme.background,
                fontSize: '13px'
            }
        }, [
            ...messages.map((msg, index) => 
                React.createElement('div', {
                    key: index,
                    style: {
                        marginBottom: '12px',
                        padding: '8px 10px',
                        borderRadius: '6px',
                        background: msg.role === 'user' ? theme.accent + '20' : theme.panel,
                        border: `1px solid ${msg.role === 'user' ? theme.accent : theme.border}`,
                        color: theme.text
                    }
                }, [
                    React.createElement('div', {
                        key: 'role',
                        style: {
                            fontSize: '11px',
                            color: theme.textMuted,
                            marginBottom: '2px',
                            fontWeight: '500'
                        }
                    }, msg.role === 'user' ? '👤 You' : '🤖 Assistant'),
                    React.createElement('div', {
                        key: 'content',
                        style: { whiteSpace: 'pre-wrap', lineHeight: '1.4' }
                    }, msg.content),
                    msg.timestamp && React.createElement('div', {
                        key: 'timestamp',
                        style: {
                            fontSize: '10px',
                            color: theme.textMuted,
                            marginTop: '6px'
                        }
                    }, msg.timestamp)
                ])
            ),
            
            // Inline input area
            React.createElement('div', {
                key: 'inline-input',
                style: {
                    marginTop: '8px',
                    padding: '8px 10px',
                    borderRadius: '6px',
                    background: theme.panel,
                    border: `1px solid ${theme.border}`,
                    color: theme.text
                }
            }, [
                React.createElement('div', {
                    key: 'input-header',
                    style: {
                        fontSize: '11px',
                        color: theme.textMuted,
                        marginBottom: '6px',
                        fontWeight: '500'
                    }
                }, '👤 You'),
                React.createElement('textarea', {
                    key: 'textarea',
                    value: input,
                    onChange: (e) => setInput(e.target.value),
                    onKeyPress: handleKeyPress,
                    placeholder: 'Ask about your infrastructure...',
                    disabled: !connected,
                    style: {
                        width: '100%',
                        minHeight: '40px',
                        padding: '6px 8px',
                        border: `1px solid ${theme.border}`,
                        borderRadius: '4px',
                        background: connected ? theme.background : theme.background + '80',
                        color: connected ? theme.text : theme.textMuted,
                        resize: 'vertical',
                        fontFamily: 'inherit',
                        fontSize: '13px',
                        outline: 'none'
                    }
                }),
                input.trim() && React.createElement('div', {
                    key: 'send-hint',
                    style: {
                        marginTop: '4px',
                        fontSize: '10px',
                        color: theme.textMuted,
                        textAlign: 'right'
                    }
                }, 'Press Enter to send, Shift+Enter for new line')
            ]),
            
            React.createElement('div', { key: 'end', ref: messagesEndRef })
        ])
    ]);
}