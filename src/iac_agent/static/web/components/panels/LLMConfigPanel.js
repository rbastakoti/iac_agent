import { theme } from '../../theme.js';

const { useState, useEffect } = React;

export function LLMConfigPanel({ onModelUpdate }) {
    // New connection form
    const [newProvider, setNewProvider] = useState('openai');
    const [newApiKey, setNewApiKey] = useState('');
    const [newModel, setNewModel] = useState('gpt-4o-mini');
    const [newEndpoint, setNewEndpoint] = useState('https://api.openai.com/v1');
    
    // Saved connection
    const [savedConnection, setSavedConnection] = useState(null);
    
    // Active connection
    const [activeConnection, setActiveConnection] = useState(null);
    
    const [connectionStatus, setConnectionStatus] = useState('disconnected');
    const [showNewConnectionForm, setShowNewConnectionForm] = useState(false);

    const providers = [
        { id: 'openai', name: 'OpenAI', models: ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo'] },
        { id: 'anthropic', name: 'Anthropic (Claude)', models: ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307'] },
        { id: 'google', name: 'Google (Gemini)', models: ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-1.0-pro'] },
        { id: 'azure', name: 'Azure OpenAI', models: ['gpt-4', 'gpt-35-turbo'] },
        { id: 'ollama', name: 'Ollama (Local)', models: ['llama2', 'codellama', 'mistral'] }
    ];

    // Load saved and active connections on mount
    useEffect(() => {
        const loadConnections = async () => {
            try {
                const response = await fetch('/api/llm/config');
                if (response.ok) {
                    const config = await response.json();
                    if (config.is_configured) {
                        const connectionInfo = {
                            endpoint: config.endpoint,
                            model_name: config.model_name,
                            provider: detectProvider(config.endpoint)
                        };
                        setSavedConnection(connectionInfo);
                        setActiveConnection(connectionInfo);
                        setConnectionStatus('connected');
                    }
                }
            } catch (error) {
                console.log('No existing connections found');
            }
        };
        loadConnections();
    }, []);

    const detectProvider = (url) => {
        if (url.includes('openai.com')) return 'OpenAI';
        if (url.includes('ai.azure.com')) return 'Azure OpenAI';
        if (url.includes('anthropic.com')) return 'Anthropic';
        if (url.includes('googleapis.com')) return 'Google';
        return 'Custom';
    };

    const handleSaveNewConnection = async () => {
        try {
            const response = await fetch('/api/llm/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    endpoint: newEndpoint,
                    api_key: newApiKey,
                    model_name: newModel
                })
            });
            if (response.ok) {
                const newConnection = {
                    endpoint: newEndpoint,
                    model_name: newModel,
                    provider: detectProvider(newEndpoint)
                };
                setSavedConnection(newConnection);
                setActiveConnection(newConnection);
                setConnectionStatus('connected');
                if (onModelUpdate) {
                    onModelUpdate(newModel);
                }
                // Clear form
                setNewApiKey('');
            }
        } catch (error) {
            console.error('Failed to save connection:', error);
            setConnectionStatus('error');
        }
    };

    const handleTestConnection = async () => {
        setConnectionStatus('testing');
        try {
            const response = await fetch('/api/llm/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    endpoint: newEndpoint,
                    api_key: newApiKey,
                    model_name: newModel
                })
            });
            if (response.ok) {
                setConnectionStatus('connected');
            } else {
                setConnectionStatus('error');
            }
        } catch (error) {
            setConnectionStatus('error');
        }
    };

    const handleActivateSaved = async () => {
        if (savedConnection) {
            setActiveConnection(savedConnection);
            setConnectionStatus('connected');
            if (onModelUpdate) {
                onModelUpdate(savedConnection.model_name);
            }
        }
    };

    return React.createElement('div', {
        style: {
            padding: '16px',
            height: '100%',
            overflow: 'auto'
        }
    }, [
        // Active Connection Section
        React.createElement('div', {
            key: 'active-section',
            style: { marginBottom: '24px' }
        }, [
            React.createElement('div', {
                key: 'active-header',
                style: {
                    fontSize: '11px',
                    fontWeight: 'bold',
                    color: theme.textMuted,
                    marginBottom: '12px',
                    textTransform: 'uppercase',
                    letterSpacing: '1px'
                }
            }, 'Active Connection'),
            
            activeConnection ? React.createElement('div', {
                key: 'active-info',
                style: {
                    padding: '12px',
                    background: theme.success + '20',
                    border: `1px solid ${theme.success}`,
                    borderRadius: '4px',
                    fontSize: '12px'
                }
            }, [
                React.createElement('div', { key: 'provider', style: { marginBottom: '4px' } }, `Provider: ${activeConnection.provider}`),
                React.createElement('div', { key: 'model', style: { marginBottom: '4px' } }, `Model: ${activeConnection.model_name}`),
                React.createElement('div', { key: 'endpoint', style: { color: theme.textMuted, fontSize: '10px' } }, `Endpoint: ${activeConnection.endpoint}`),
                React.createElement('div', {
                    key: 'status',
                    style: {
                        marginTop: '8px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                    }
                }, [
                    React.createElement('span', { key: 'icon' }, connectionStatus === 'connected' ? '\ud83d\ufe20' : '\u26aa'),
                    React.createElement('span', { key: 'text' }, connectionStatus === 'connected' ? 'Connected' : 'Not Connected')
                ])
            ]) : React.createElement('div', {
                key: 'no-active',
                style: {
                    padding: '12px',
                    background: theme.textMuted + '20',
                    border: `1px solid ${theme.border}`,
                    borderRadius: '4px',
                    fontSize: '12px',
                    color: theme.textMuted,
                    textAlign: 'center'
                }
            }, 'No active connection')
        ]),
        
        // Saved Connection Section
        React.createElement('div', {
            key: 'saved-section',
            style: { marginBottom: '24px' }
        }, [
            React.createElement('div', {
                key: 'saved-header',
                style: {
                    fontSize: '11px',
                    fontWeight: 'bold',
                    color: theme.textMuted,
                    marginBottom: '12px',
                    textTransform: 'uppercase',
                    letterSpacing: '1px'
                }
            }, 'Saved Connection'),
            
            savedConnection ? React.createElement('div', {
                key: 'saved-info',
                style: {
                    padding: '12px',
                    background: theme.accent + '20',
                    border: `1px solid ${theme.accent}`,
                    borderRadius: '4px',
                    fontSize: '12px'
                }
            }, [
                React.createElement('div', { key: 'provider', style: { marginBottom: '4px' } }, `Provider: ${savedConnection.provider}`),
                React.createElement('div', { key: 'model', style: { marginBottom: '4px' } }, `Model: ${savedConnection.model_name}`),
                React.createElement('div', { key: 'endpoint', style: { color: theme.textMuted, fontSize: '10px' } }, `Endpoint: ${savedConnection.endpoint}`),
                React.createElement('button', {
                    key: 'activate-btn',
                    onClick: handleActivateSaved,
                    style: {
                        marginTop: '8px',
                        padding: '4px 8px',
                        background: theme.accent,
                        color: 'white',
                        border: 'none',
                        borderRadius: '3px',
                        fontSize: '10px',
                        cursor: 'pointer'
                    }
                }, 'Activate')
            ]) : React.createElement('div', {
                key: 'no-saved',
                style: {
                    padding: '12px',
                    background: theme.textMuted + '20',
                    border: `1px solid ${theme.border}`,
                    borderRadius: '4px',
                    fontSize: '12px',
                    color: theme.textMuted,
                    textAlign: 'center'
                }
            }, 'No saved connection')
        ]),
        
        // New Connection Section
        React.createElement('div', {
            key: 'new-section'
        }, [
            React.createElement('button', {
                key: 'new-header',
                onClick: () => setShowNewConnectionForm(!showNewConnectionForm),
                style: {
                    width: '100%',
                    padding: '12px',
                    background: theme.panel,
                    border: `1px solid ${theme.border}`,
                    borderRadius: '4px',
                    color: theme.text,
                    fontSize: '11px',
                    fontWeight: 'bold',
                    textTransform: 'uppercase',
                    letterSpacing: '1px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: showNewConnectionForm ? '16px' : '0px'
                },
                onMouseEnter: (e) => e.target.style.background = theme.hover,
                onMouseLeave: (e) => e.target.style.background = theme.panel
            }, [
                React.createElement('span', { key: 'text' }, 'New Connection +'),
                React.createElement('span', { key: 'arrow', style: { fontSize: '14px' } }, showNewConnectionForm ? '▼' : '▶')
            ]),
            
            // Conditionally show the form
            showNewConnectionForm ? [
                // Provider selection
                React.createElement('div', {
                    key: 'provider-section',
                    style: { marginBottom: '16px' }
                }, [
                React.createElement('label', {
                    key: 'label',
                    style: {
                        display: 'block',
                        fontSize: '12px',
                        fontWeight: '500',
                        color: theme.text,
                        marginBottom: '6px'
                    }
                }, 'Provider'),
                React.createElement('select', {
                    key: 'select',
                    value: newProvider,
                    onChange: (e) => {
                        setNewProvider(e.target.value);
                        const provider = providers.find(p => p.id === e.target.value);
                        if (provider) {
                            setNewModel(provider.models[0]);
                            // Update endpoint based on provider
                            if (provider.id === 'openai') setNewEndpoint('https://api.openai.com/v1');
                            else if (provider.id === 'anthropic') setNewEndpoint('https://api.anthropic.com/v1');
                            else if (provider.id === 'google') setNewEndpoint('https://generativelanguage.googleapis.com/v1');
                            else if (provider.id === 'azure') setNewEndpoint('https://your-resource.openai.azure.com/openai');
                            else if (provider.id === 'ollama') setNewEndpoint('http://localhost:11434/v1');
                        }
                    },
                    style: {
                        width: '100%',
                        padding: '6px 8px',
                        background: theme.background,
                        border: `1px solid ${theme.border}`,
                        borderRadius: '3px',
                        color: theme.text,
                        fontSize: '12px'
                    }
                }, providers.map(p =>
                    React.createElement('option', { key: p.id, value: p.id }, p.name)
                ))
            ]),
        
            // API Key input
            React.createElement('div', {
                key: 'api-key-section',
                style: { marginBottom: '16px' }
            }, [
                React.createElement('label', {
                    key: 'label',
                    style: {
                        display: 'block',
                        fontSize: '12px',
                        fontWeight: '500',
                        color: theme.text,
                        marginBottom: '6px'
                    }
                }, 'API Key'),
                React.createElement('input', {
                    key: 'input',
                    type: 'password',
                    value: newApiKey,
                    onChange: (e) => setNewApiKey(e.target.value),
                    placeholder: 'sk-...',
                    style: {
                        width: '100%',
                        padding: '6px 8px',
                        background: theme.background,
                        border: `1px solid ${theme.border}`,
                        borderRadius: '3px',
                        color: theme.text,
                        fontSize: '12px'
                    }
                })
            ]),
            
            // Model selection
            React.createElement('div', {
                key: 'model-section',
                style: { marginBottom: '16px' }
            }, [
                React.createElement('label', {
                    key: 'label',
                    style: {
                        display: 'block',
                        fontSize: '12px',
                        fontWeight: '500',
                        color: theme.text,
                        marginBottom: '6px'
                    }
                }, 'Model'),
                React.createElement('select', {
                    key: 'select',
                    value: newModel,
                    onChange: (e) => setNewModel(e.target.value),
                    style: {
                        width: '100%',
                        padding: '6px 8px',
                        background: theme.background,
                        border: `1px solid ${theme.border}`,
                        borderRadius: '3px',
                        color: theme.text,
                        fontSize: '12px'
                    }
                }, providers.find(p => p.id === newProvider)?.models.map(m =>
                    React.createElement('option', { key: m, value: m }, m)
                ))
            ]),
            
            // Custom endpoint
            React.createElement('div', {
                key: 'endpoint-section',
                style: { marginBottom: '16px' }
            }, [
                React.createElement('label', {
                    key: 'label',
                    style: {
                        display: 'block',
                        fontSize: '12px',
                        fontWeight: '500',
                        color: theme.text,
                        marginBottom: '6px'
                    }
                }, 'Endpoint URL'),
                React.createElement('input', {
                    key: 'input',
                    type: 'text',
                    value: newEndpoint,
                    onChange: (e) => setNewEndpoint(e.target.value),
                    style: {
                        width: '100%',
                        padding: '6px 8px',
                        background: theme.background,
                        border: `1px solid ${theme.border}`,
                        borderRadius: '3px',
                        color: theme.text,
                        fontSize: '12px'
                    }
                })
            ]),
        
            // Connection status and buttons
            React.createElement('div', {
                key: 'status-section'
            }, [
                React.createElement('div', {
                    key: 'status',
                    style: {
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '8px 12px',
                        background: theme.background,
                        border: `1px solid ${theme.border}`,
                        borderRadius: '3px',
                        marginBottom: '8px',
                        fontSize: '12px'
                    }
                }, [
                    React.createElement('span', { key: 'icon' }, connectionStatus === 'connected' ? '\ud83d\ufe20' : connectionStatus === 'testing' ? '\ud83d\ufe21' : connectionStatus === 'error' ? '\ud83d\udd34' : '\u26aa'),
                    React.createElement('span', { key: 'text' }, 
                        connectionStatus === 'connected' ? 'Test Successful' :
                        connectionStatus === 'testing' ? 'Testing...' :
                        connectionStatus === 'error' ? 'Test Failed' :
                        'Ready to test'
                    )
                ]),
                React.createElement('div', {
                    key: 'buttons',
                    style: {
                        display: 'flex',
                        gap: '8px'
                    }
                }, [
                    React.createElement('button', {
                        key: 'test-btn',
                        onClick: handleTestConnection,
                        disabled: connectionStatus === 'testing' || !newApiKey,
                        style: {
                            flex: 1,
                            padding: '6px 12px',
                            background: connectionStatus === 'testing' || !newApiKey ? theme.textMuted : theme.accent,
                            color: 'white',
                            border: 'none',
                            borderRadius: '3px',
                            fontSize: '12px',
                            cursor: connectionStatus === 'testing' || !newApiKey ? 'not-allowed' : 'pointer'
                        }
                    }, connectionStatus === 'testing' ? 'Testing...' : 'Test'),
                    React.createElement('button', {
                        key: 'save-btn',
                        onClick: handleSaveNewConnection,
                        disabled: !newApiKey || !newEndpoint || !newModel,
                        style: {
                            flex: 1,
                            padding: '6px 12px',
                            background: (!newApiKey || !newEndpoint || !newModel) ? theme.textMuted : theme.success,
                            color: 'white',
                            border: 'none',
                            borderRadius: '3px',
                            fontSize: '12px',
                            cursor: (!newApiKey || !newEndpoint || !newModel) ? 'not-allowed' : 'pointer'
                        }
                    }, 'Save')
                ])
            ])
            ] : null
        ])
    ]);
}