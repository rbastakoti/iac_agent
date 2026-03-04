// Enhanced LLM Connection Management Component
function LLMConnectionsTab({ onClose }) {
    const [connections, setConnections] = useState([]);
    const [activeConnection, setActiveConnection] = useState('');
    const [showAddModal, setShowAddModal] = useState(false);
    const [editingConnection, setEditingConnection] = useState(null);
    const [testResults, setTestResults] = useState({});
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        loadConnections();
    }, []);

    const loadConnections = async () => {
        try {
            const response = await fetch('/api/connections');
            const data = await response.json();
            setConnections(data.connections);
            setActiveConnection(data.active_connection);
        } catch (error) {
            console.error('Failed to load connections:', error);
        }
    };

    const testConnection = async (connectionName) => {
        setLoading(true);
        try {
            const response = await fetch(`/api/connections/${connectionName}/test`, {
                method: 'POST'
            });
            const result = await response.json();
            
            setTestResults(prev => ({
                ...prev,
                [connectionName]: result
            }));
            
            // Reload connections to get updated status
            await loadConnections();
        } catch (error) {
            setTestResults(prev => ({
                ...prev,
                [connectionName]: { status: 'error', error: error.message }
            }));
        }
        setLoading(false);
    };

    const activateConnection = async (connectionName) => {
        try {
            const response = await fetch(`/api/connections/${connectionName}/activate`, {
                method: 'POST'
            });
            
            if (response.ok) {
                await loadConnections();
                addSystemMessage(`✅ Activated connection: ${connectionName}`);
            }
        } catch (error) {
            console.error('Failed to activate connection:', error);
        }
    };

    const deleteConnection = async (connectionName) => {
        if (!confirm(`Are you sure you want to delete the connection "${connectionName}"?`)) {
            return;
        }

        try {
            const response = await fetch(`/api/connections/${connectionName}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                await loadConnections();
                addSystemMessage(`🗑️ Deleted connection: ${connectionName}`);
            }
        } catch (error) {
            console.error('Failed to delete connection:', error);
        }
    };

    return (
        <div>
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h3 className="text-lg font-medium text-white">LLM Connections</h3>
                    <p className="text-sm text-gray-400 mt-1">
                        Manage your AI model connections with unified configuration
                    </p>
                </div>
                <button
                    onClick={() => setShowAddModal(true)}
                    className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                    </svg>
                    <span>Add Connection</span>
                </button>
            </div>

            {/* Current Active Connection */}
            {activeConnection && (
                <div className="bg-gradient-to-r from-blue-900 to-purple-900 rounded-lg p-4 mb-6 border border-blue-700">
                    <div className="flex items-center space-x-3">
                        <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
                        <div>
                            <div className="text-white font-medium">Currently Active</div>
                            <div className="text-blue-200 text-sm">{activeConnection}</div>
                        </div>
                    </div>
                </div>
            )}

            {/* Connections List */}
            <div className="space-y-4">
                {connections.map((connection) => (
                    <div 
                        key={connection.name} 
                        className={`bg-gray-700 rounded-lg p-4 border-l-4 ${
                            connection.is_active 
                                ? 'border-green-400 bg-gray-700/80' 
                                : connection.status === 'connected' 
                                    ? 'border-blue-400' 
                                    : 'border-red-400'
                        }`}
                    >
                        {/* Connection Header */}
                        <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center space-x-3">
                                <div className={`w-3 h-3 rounded-full ${
                                    connection.status === 'connected' ? 'bg-green-400' : 'bg-red-400'
                                }`}></div>
                                <h4 className="font-medium text-white">{connection.name}</h4>
                                {connection.is_active && (
                                    <span className="text-xs bg-green-600 px-2 py-1 rounded-full">ACTIVE</span>
                                )}
                            </div>
                            
                            {/* Action Buttons */}
                            <div className="flex space-x-2">
                                <button
                                    onClick={() => testConnection(connection.name)}
                                    disabled={loading}
                                    className="px-3 py-1 bg-gray-600 hover:bg-gray-500 text-white text-sm rounded transition-colors disabled:opacity-50"
                                >
                                    {loading ? '...' : 'Test'}
                                </button>
                                
                                {!connection.is_active && (
                                    <button
                                        onClick={() => activateConnection(connection.name)}
                                        className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors"
                                    >
                                        Activate
                                    </button>
                                )}
                                
                                <button
                                    onClick={() => setEditingConnection(connection)}
                                    className="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 text-white text-sm rounded transition-colors"
                                >
                                    Edit
                                </button>
                                
                                <button
                                    onClick={() => deleteConnection(connection.name)}
                                    className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition-colors"
                                >
                                    Delete
                                </button>
                            </div>
                        </div>

                        {/* Connection Details */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                            <div>
                                <span className="text-gray-400">Endpoint:</span>
                                <div className="text-white font-mono text-xs break-all">{connection.endpoint}</div>
                            </div>
                            <div>
                                <span className="text-gray-400">Model:</span>
                                <div className="text-white">{connection.model_name}</div>
                            </div>
                            <div>
                                <span className="text-gray-400">Status:</span>
                                <div className={`${connection.status === 'connected' ? 'text-green-400' : 'text-red-400'}`}>
                                    {connection.status === 'connected' ? '✅ Connected' : '❌ Error'}
                                </div>
                            </div>
                        </div>

                        {/* Description */}
                        {connection.description && (
                            <div className="mt-2 text-sm text-gray-300">
                                {connection.description}
                            </div>
                        )}

                        {/* Test Results */}
                        {testResults[connection.name] && (
                            <div className="mt-3 p-3 bg-gray-800 rounded text-sm">
                                <div className="flex items-center space-x-2 mb-2">
                                    <span className="text-gray-400">Test Result:</span>
                                    <span className={testResults[connection.name].status === 'success' ? 'text-green-400' : 'text-red-400'}>
                                        {testResults[connection.name].status}
                                    </span>
                                </div>
                                {testResults[connection.name].response_preview && (
                                    <div className="text-gray-300 font-mono text-xs">
                                        {testResults[connection.name].response_preview}
                                    </div>
                                )}
                                {testResults[connection.name].error && (
                                    <div className="text-red-400 text-xs">
                                        {testResults[connection.name].error}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Error Message */}
                        {connection.error_message && (
                            <div className="mt-3 p-3 bg-red-900/30 border border-red-700 rounded text-sm">
                                <span className="text-red-400">⚠️ {connection.error_message}</span>
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {/* Add Connection Modal */}
            {showAddModal && (
                <AddConnectionModal
                    onClose={() => setShowAddModal(false)}
                    onSave={loadConnections}
                />
            )}

            {/* Edit Connection Modal */}
            {editingConnection && (
                <AddConnectionModal
                    connection={editingConnection}
                    onClose={() => setEditingConnection(null)}
                    onSave={loadConnections}
                />
            )}
        </div>
    );
}

// Add/Edit Connection Modal
function AddConnectionModal({ connection = null, onClose, onSave }) {
    const [formData, setFormData] = useState({
        name: connection?.name || '',
        endpoint: connection?.endpoint || '',
        api_key: '',  // Always start empty for security
        model_name: connection?.model_name || '',
        description: connection?.description || '',
        enabled: connection?.enabled ?? true
    });
    const [presets] = useState([
        {
            name: 'OpenAI',
            endpoint: 'https://api.openai.com/v1',
            model_name: 'gpt-4-turbo-preview',
            description: 'Official OpenAI API'
        },
        {
            name: 'Azure OpenAI',
            endpoint: 'https://your-resource.openai.azure.com/',
            model_name: 'gpt-4',
            description: 'Azure OpenAI Service'
        },
        {
            name: 'Anthropic Claude',
            endpoint: 'https://api.anthropic.com/',
            model_name: 'claude-3-sonnet-20240229',
            description: 'Anthropic Claude API'
        },
        {
            name: 'Ollama Local',
            endpoint: 'http://localhost:11434/v1',
            model_name: 'llama3.1:8b',
            description: 'Local Ollama server'
        }
    ]);

    const applyPreset = (preset) => {
        setFormData(prev => ({
            ...prev,
            ...preset
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!formData.api_key && !connection) {
            alert('API key is required for new connections');
            return;
        }

        try {
            const url = connection 
                ? `/api/connections/${connection.name}`
                : '/api/connections';
            
            const method = connection ? 'PUT' : 'POST';
            
            const response = await fetch(url, {
                method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData),
            });

            if (response.ok) {
                onSave();
                onClose();
                addSystemMessage(`✅ Connection ${connection ? 'updated' : 'added'}: ${formData.name}`);
            } else {
                const error = await response.text();
                alert(`Failed to save connection: ${error}`);
            }
        } catch (error) {
            console.error('Failed to save connection:', error);
            alert(`Error: ${error.message}`);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-gray-800 rounded-lg w-full max-w-2xl max-h-[80vh] overflow-hidden">
                <div className="p-4 border-b border-gray-700">
                    <h3 className="text-lg font-medium text-white">
                        {connection ? 'Edit Connection' : 'Add New Connection'}
                    </h3>
                </div>

                <form onSubmit={handleSubmit} className="p-4 space-y-4 overflow-y-auto max-h-96">
                    {/* Presets */}
                    {!connection && (
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                                Quick Setup (Optional)
                            </label>
                            <div className="grid grid-cols-2 gap-2">
                                {presets.map((preset) => (
                                    <button
                                        key={preset.name}
                                        type="button"
                                        onClick={() => applyPreset(preset)}
                                        className="p-2 text-left bg-gray-700 hover:bg-gray-600 rounded text-sm"
                                    >
                                        <div className="font-medium text-white">{preset.name}</div>
                                        <div className="text-xs text-gray-400">{preset.description}</div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Form Fields */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="md:col-span-2">
                            <label className="block text-sm font-medium text-gray-300 mb-1">
                                Connection Name *
                            </label>
                            <input
                                type="text"
                                required
                                value={formData.name}
                                onChange={(e) => setFormData({...formData, name: e.target.value})}
                                className="w-full px-3 py-2 bg-gray-700 text-white rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="e.g., OpenAI GPT-4"
                            />
                        </div>

                        <div className="md:col-span-2">
                            <label className="block text-sm font-medium text-gray-300 mb-1">
                                API Endpoint *
                            </label>
                            <input
                                type="url"
                                required
                                value={formData.endpoint}
                                onChange={(e) => setFormData({...formData, endpoint: e.target.value})}
                                className="w-full px-3 py-2 bg-gray-700 text-white rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="https://api.openai.com/v1"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-1">
                                API Key * {connection && <span className="text-xs">(leave empty to keep current)</span>}
                            </label>
                            <input
                                type="password"
                                required={!connection}
                                value={formData.api_key}
                                onChange={(e) => setFormData({...formData, api_key: e.target.value})}
                                className="w-full px-3 py-2 bg-gray-700 text-white rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="sk-..."
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-1">
                                Model Name *
                            </label>
                            <input
                                type="text"
                                required
                                value={formData.model_name}
                                onChange={(e) => setFormData({...formData, model_name: e.target.value})}
                                className="w-full px-3 py-2 bg-gray-700 text-white rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="gpt-4-turbo-preview"
                            />
                        </div>

                        <div className="md:col-span-2">
                            <label className="block text-sm font-medium text-gray-300 mb-1">
                                Description
                            </label>
                            <input
                                type="text"
                                value={formData.description}
                                onChange={(e) => setFormData({...formData, description: e.target.value})}
                                className="w-full px-3 py-2 bg-gray-700 text-white rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="Human-friendly description"
                            />
                        </div>
                    </div>

                    <div className="flex justify-end space-x-3 pt-4 border-t border-gray-700">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                        >
                            {connection ? 'Update' : 'Add'} Connection
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

// Helper function to add system messages (should be available globally)
function addSystemMessage(message, type = 'info') {
    // This would typically be passed down from the main App component
    console.log(`[${type}] ${message}`);
}