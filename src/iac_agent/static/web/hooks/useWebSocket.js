const { useState, useEffect, useCallback } = React;

export function useWebSocket() {
    const [socket, setSocket] = useState(null);
    const [connected, setConnected] = useState(false);
    const [messages, setMessages] = useState([]);
    const [reconnectAttempts, setReconnectAttempts] = useState(0);
    
    const connectWebSocket = useCallback(() => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        try {
            const ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                console.log('WebSocket connected');
                setConnected(true);
                setSocket(ws);
                setReconnectAttempts(0); // Reset on successful connection
                
                // Store WebSocket globally for terminal access
                window.wsManager = {
                    send: (message) => {
                        if (ws.readyState === WebSocket.OPEN) {
                            ws.send(JSON.stringify(message));
                        } else {
                            console.warn('WebSocket not ready, message not sent:', message);
                        }
                    },
                    connected: true
                };
            };
            
            ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                
                // Handle terminal output messages specially
                if (message.type === 'terminal_output') {
                    // Use current value, not captured value
                    if (window.handleTerminalOutput) {
                        window.handleTerminalOutput(message.payload);
                    }
                    return; // Don't add to general messages
                }
                
                // Handle PTY messages
                if (message.type === 'pty_spawn') {
                    // Use current value, not captured value
                    if (window.handlePTYSpawn) {
                        window.handlePTYSpawn(message.payload);
                    }
                    return; // Don't add to general messages
                }
                
                if (message.type === 'pty_output') {
                    // Use current value, not captured value
                    if (window.handlePTYOutput) {
                        window.handlePTYOutput(message.payload);
                    }
                    return; // Don't add to general messages
                }
                
                // Only add non-terminal messages to prevent memory bloat
                setMessages(prev => {
                    const newMessages = [...prev, message];
                    // Keep only last 100 messages to prevent memory leak
                    return newMessages.slice(-100);
                });
            };
        
        ws.onclose = () => {
            console.log('WebSocket disconnected');
            setConnected(false);
            setSocket(null);
            
            // Clean up global WebSocket manager
            if (window.wsManager) {
                window.wsManager.connected = false;
            }
            
            // Attempt reconnection with exponential backoff
            if (reconnectAttempts < 5) {
                const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 10000);
                console.log(`Attempting to reconnect in ${delay}ms... (attempt ${reconnectAttempts + 1}/5)`);
                setTimeout(() => {
                    setReconnectAttempts(prev => prev + 1);
                    connectWebSocket();
                }, delay);
            } else {
                console.error('Max reconnection attempts reached');
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            setConnected(false);
        };
        
        return ws;
        
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            setConnected(false);
            return null;
        }
    }, [reconnectAttempts]);
    
    useEffect(() => {
        const ws = connectWebSocket();
        
        return () => {
            if (ws) {
                ws.close();
            }
        };
    }, [connectWebSocket]);
    
    const sendMessage = useCallback((type, payload, session_id = null) => {
        if (socket && connected) {
            const message = { 
                type, 
                payload,
                ...(session_id && { session_id })
            };
            socket.send(JSON.stringify(message));
        } else {
            console.warn('Cannot send message: WebSocket not connected', { type, payload });
        }
    }, [socket, connected]);
    
    // Get the last message for components that need it
    const lastMessage = messages.length > 0 ? { data: JSON.stringify(messages[messages.length - 1]) } : null;
    
    return { socket, connected, messages, lastMessage, sendMessage };
}