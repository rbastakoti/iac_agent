"""WebSocket manager for real-time communication."""

import json
import asyncio
import logging
import uuid
from typing import Dict, List, Any, Optional
from uuid import uuid4
from datetime import datetime

from fastapi import WebSocket
from pydantic import BaseModel

# Import terminal server functionality
from iac_agent.infrastructure.terminal.pty_manager import pty_manager

logger = logging.getLogger(__name__)


class WebSocketMessage(BaseModel):
    """WebSocket message structure."""
    type: str
    payload: Any
    session_id: Optional[str] = None
    timestamp: datetime = None
    
    def __init__(self, **data):
        if data.get('timestamp') is None:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


class ConnectionInfo(BaseModel):
    """Connection information."""
    model_config = {"arbitrary_types_allowed": True}
    
    websocket: WebSocket
    session_id: str
    connected_at: datetime
    last_activity: datetime
    pty_session_id: Optional[str] = None  # Track PTY session for this connection


class WebSocketManager:
    """Manages WebSocket connections and message routing."""
    
    def __init__(self):
        self.active_connections: Dict[str, ConnectionInfo] = {}
        self.session_to_connection: Dict[str, str] = {}
        # Create persistent session manager
        self.session_manager = None
    
    async def connect(self, websocket: WebSocket) -> str:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        
        connection_id = str(uuid4())
        connection_info = ConnectionInfo(
            websocket=websocket,
            session_id="",  # Will be set when user starts a session
            connected_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        
        self.active_connections[connection_id] = connection_info
        
        # Send welcome message
        await self.send_to_connection(connection_id, WebSocketMessage(
            type="connection_established",
            payload={"connection_id": connection_id}
        ))
        
        return connection_id
    
    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection and clean up PTY session."""
        connection_id = None
        for conn_id, info in self.active_connections.items():
            if info.websocket == websocket:
                connection_id = conn_id
                break
        
        if connection_id:
            connection_info = self.active_connections.pop(connection_id, None)
            if connection_info:
                # Clean up PTY session if exists
                if connection_info.pty_session_id:
                    asyncio.create_task(self._cleanup_pty_session(connection_info.pty_session_id))
                
                # Clean up session tracking
                if connection_info.session_id:
                    self.session_to_connection.pop(connection_info.session_id, None)
    
    async def handle_message(self, websocket: WebSocket, data: str) -> None:
        """Handle incoming WebSocket message."""
        try:
            message_data = json.loads(data)
            message = WebSocketMessage(**message_data)
            
            logger.info(f"📨 Received WebSocket message: type={message.type}, session_id={message.session_id}")
            
            # Find connection
            connection_id = None
            for conn_id, info in self.active_connections.items():
                if info.websocket == websocket:
                    connection_id = conn_id
                    info.last_activity = datetime.utcnow()
                    break
            
            if not connection_id:
                logger.warning("⚠️ Message received from unknown connection")
                return
            
            # Route message based on type
            await self.route_message(connection_id, message)
            
        except Exception as e:
            logger.error(f"❌ WebSocket message handling error: {str(e)}")
            await self.send_error(websocket, f"Invalid message format: {str(e)}")
    
    async def route_message(self, connection_id: str, message: WebSocketMessage) -> None:
        """Route message to appropriate handler."""
        handlers = {
            # Chat functionality
            "start_session": self.handle_start_session,
            "chat_message": self.handle_chat_message,
            # File operations via MCP 
            "list_workspace_files": self.handle_list_workspace_files,
            "read_workspace_file": self.handle_read_workspace_file,
            "save_workspace_file": self.handle_save_workspace_file,
            "create_workspace_file": self.handle_create_workspace_file,
            # Terminal functionality
            "pty_spawn": self.handle_pty_spawn,
            "pty_write": self.handle_pty_write,
            "pty_resize": self.handle_pty_resize,
            # Graph functionality
            "graph_interaction": self.handle_graph_interaction,
            # File/Settings functionality
            "terraform_command": self.handle_terraform_command,
            "settings_update": self.handle_settings_update,
            "heartbeat": self.handle_heartbeat,
        }
        
        handler = handlers.get(message.type)
        if handler:
            await handler(connection_id, message)
        else:
            await self.send_error_to_connection(
                connection_id, 
                f"Unknown message type: {message.type}"
            )
    
    # ----------------------------------------------------------------------------
    # CHAT FUNCTIONALITY
    # ----------------------------------------------------------------------------
    
    async def handle_start_session(self, connection_id: str, message: WebSocketMessage) -> None:
        """Handle session start."""
        session_id = message.payload.get("session_id") or str(uuid4())
        
        # Update connection with session ID
        if connection_id in self.active_connections:
            self.active_connections[connection_id].session_id = session_id
            self.session_to_connection[session_id] = connection_id
        
        await self.send_to_connection(connection_id, WebSocketMessage(
            type="session_started",
            payload={"session_id": session_id},
            session_id=session_id
        ))
    
    async def handle_chat_message(self, connection_id: str, message: WebSocketMessage) -> None:
        """Handle chat message from user."""
        # Use existing session manager (should be set from main.py)
        if self.session_manager is None:
            await self.send_error_to_connection(connection_id, "Session manager not initialized")
            return
        
        session_id = message.session_id or "default"
        
        response = await self.session_manager.process_user_message(
            session_id,
            message.payload.get("content", "")
        )
        
        await self.send_to_connection(connection_id, WebSocketMessage(
            type="chat_response",
            payload=response,
            session_id=session_id
        ))
    
    # ----------------------------------------------------------------------------
    # FILE OPERATIONS via MCP
    # ----------------------------------------------------------------------------
    
    async def handle_list_workspace_files(self, connection_id: str, message: WebSocketMessage) -> None:
        """Handle request to list workspace files via MCP."""
        if self.session_manager is None:
            await self.send_error_to_connection(connection_id, "Session manager not initialized")
            return
        
        try:
            logger.info("Processing list_workspace_files request via FastMCP")
            
            # Ensure MCP is initialized
            await self.session_manager._ensure_mcp_initialized()
            
            # Use the standard list_files tool and build tree from flat list
            result = await self.session_manager.mcp_client.execute_tool_call(
                "file_server___list_files", 
                {"pattern": "*"}
            )
            
            logger.info(f"FastMCP list_files result: {result}")
            
            if result.get('content') and len(result['content']) > 0:
                # Parse the JSON content
                import json
                files_data = json.loads(result['content'][0]['text'])
                
                # Convert flat file list to tree structure
                tree_structure = self._build_file_tree(files_data)
                
                logger.info(f"Built file tree with {len(tree_structure)} root items")
                
                await self.send_to_connection(connection_id, WebSocketMessage(
                    type="workspace_files",
                    payload={"files": tree_structure},
                    session_id=message.session_id
                ))
            else:
                logger.warning("No files found or empty result")
                await self.send_to_connection(connection_id, WebSocketMessage(
                    type="workspace_files",
                    payload={"files": []},
                    session_id=message.session_id
                ))
                
        except Exception as e:
            logger.error(f"Failed to list files via FastMCP: {str(e)}")
            await self.send_error_to_connection(connection_id, f"Failed to list files: {str(e)}")

    async def handle_read_workspace_file(self, connection_id: str, message: WebSocketMessage) -> None:
        """Handle request to read workspace file content via MCP."""
        if self.session_manager is None:
            await self.send_error_to_connection(connection_id, "Session manager not initialized")
            return
        
        filename = message.payload.get("filename")
        if not filename:
            await self.send_error_to_connection(connection_id, "Filename is required")
            return
        
        try:
            logger.info(f"Reading workspace file: {filename}")
            
            # Ensure MCP is initialized
            await self.session_manager._ensure_mcp_initialized()
            
            # Use the session manager's MCP client
            result = await self.session_manager.mcp_client.execute_tool_call(
                "file_server___read_file",
                {"path": filename}
            )
            
            logger.info(f"FastMCP read_file result: {result}")
            
            if result.get('content') and len(result['content']) > 0:
                content = result['content'][0]['text']
                
                await self.send_to_connection(connection_id, WebSocketMessage(
                    type="workspace_file_content",
                    payload={
                        "filename": filename,
                        "content": content
                    },
                    session_id=message.session_id
                ))
            else:
                await self.send_error_to_connection(connection_id, f"Could not read file: {filename}")
                
        except Exception as e:
            logger.error(f"Failed to read file {filename} via FastMCP: {str(e)}")
            await self.send_error_to_connection(connection_id, f"Failed to read file: {str(e)}")

    async def handle_save_workspace_file(self, connection_id: str, message: WebSocketMessage) -> None:
        """Handle request to save workspace file content via MCP."""
        logger.info(f"💾 Starting save operation for connection {connection_id}")
        
        if self.session_manager is None:
            logger.error("💾 Session manager is None - cannot save file")
            await self.send_error_to_connection(connection_id, "Session manager not initialized")
            return
        
        filename = message.payload.get("filename")
        content = message.payload.get("content", "")
        
        logger.info(f"💾 Save request - filename: {filename}, content length: {len(content)}")
        
        if not filename:
            logger.error("💾 No filename provided")
            await self.send_error_to_connection(connection_id, "Filename is required")
            return
        
        try:
            logger.info(f"💾 Saving workspace file: {filename}")
            
            # Ensure MCP is initialized
            logger.info("💾 Ensuring MCP is initialized...")
            await self.session_manager._ensure_mcp_initialized()
            logger.info("💾 MCP initialization successful")
            
            # Use the session manager's MCP client to save file
            logger.info(f"💾 Executing MCP tool call for file_server___write_file")
            result = await self.session_manager.mcp_client.execute_tool_call(
                "file_server___write_file",
                {
                    "path": filename,
                    "content": content
                }
            )
            
            logger.info(f"💾 FastMCP write_file result: {result}")
            logger.info(f"💾 Result type: {type(result)}")
            
            if result.get('content') and len(result['content']) > 0:
                # Check if save was successful
                success_message = result['content'][0]['text']
                logger.info(f"💾 Save successful, message: {success_message}")
                
                await self.send_to_connection(connection_id, WebSocketMessage(
                    type="file_saved",
                    payload={
                        "filename": filename,
                        "success": True,
                        "message": success_message
                    },
                    session_id=message.session_id
                ))
                logger.info(f"💾 Successfully saved file: {filename}")
            else:
                logger.error(f"💾 Save failed - empty or invalid result: {result}")
                await self.send_error_to_connection(connection_id, f"Failed to save file: {filename}")
                
        except Exception as e:
            logger.error(f"💾 Exception during save operation: {str(e)}")
            logger.error(f"💾 Exception type: {type(e)}")
            import traceback
            logger.error(f"💾 Full traceback: {traceback.format_exc()}")
            
            await self.send_to_connection(connection_id, WebSocketMessage(
                type="file_saved",
                payload={
                    "filename": filename,
                    "success": False,
                    "error": str(e)
                },
                session_id=message.session_id
            ))

    async def handle_create_workspace_file(self, connection_id: str, message: WebSocketMessage) -> None:
        """Handle request to create a new workspace file via MCP."""
        if self.session_manager is None:
            await self.send_error_to_connection(connection_id, "Session manager not initialized")
            return
        
        filename = message.payload.get("filename")
        content = message.payload.get("content", "")
        
        if not filename:
            await self.send_error_to_connection(connection_id, "Filename is required")
            return
        
        try:
            logger.info(f"Creating workspace file: {filename}")
            
            # Ensure MCP is initialized
            await self.session_manager._ensure_mcp_initialized()
            
            # Use the session manager's MCP client to create file
            result = await self.session_manager.mcp_client.execute_tool_call(
                "file_server___write_file",
                {
                    "path": filename,
                    "content": content
                }
            )
            
            logger.info(f"FastMCP create file result: {result}")
            
            if result.get('content') and len(result['content']) > 0:
                # Check if creation was successful
                success_message = result['content'][0]['text']
                
                await self.send_to_connection(connection_id, WebSocketMessage(
                    type="file_created",
                    payload={
                        "filename": filename,
                        "success": True,
                        "message": success_message
                    },
                    session_id=message.session_id
                ))
                logger.info(f"Successfully created file: {filename}")
            else:
                await self.send_error_to_connection(connection_id, f"Failed to create file: {filename}")
                
        except Exception as e:
            logger.error(f"Failed to create file {filename} via FastMCP: {str(e)}")
            await self.send_error_to_connection(connection_id, f"Failed to create file: {str(e)}")

    def _build_file_tree(self, files_data):
        """Convert flat file list to hierarchical tree structure for file explorer."""
        tree = {}
        
        for file_info in files_data:
            path_parts = file_info['path'].split('/')
            current = tree
            
            # Build directory structure
            for i, part in enumerate(path_parts):
                if i == len(path_parts) - 1:  # This is the file
                    current[part] = {
                        'name': part,
                        'type': 'file',
                        'path': file_info['path'],
                        'size': file_info.get('size', 0),
                        'modified': file_info.get('modified', 0)
                    }
                else:  # This is a directory
                    if part not in current:
                        current[part] = {
                            'name': part,
                            'type': 'directory',
                            'children': {}
                        }
                    current = current[part]['children']
        
        # Convert to list format expected by frontend
        return self._tree_dict_to_list(tree)
    
    def _tree_dict_to_list(self, tree_dict):
        """Convert tree dictionary to list format expected by frontend."""
        result = []
        for name, item in sorted(tree_dict.items()):
            if item['type'] == 'directory':
                result.append({
                    'name': name,
                    'type': 'directory',
                    'children': self._tree_dict_to_list(item['children'])
                })
            else:
                result.append({
                    'name': name,
                    'type': 'file',
                    'path': item['path'],
                    'size': item.get('size', 0),
                    'modified': item.get('modified', 0)
                })
        return result

    # ----------------------------------------------------------------------------
    # TERMINAL FUNCTIONALITY
    # ----------------------------------------------------------------------------
    
    async def handle_pty_spawn(self, connection_id: str, message: WebSocketMessage) -> None:
        """Handle PTY spawn request."""
        try:
            shell = message.payload.get("shell", "powershell.exe")
            cwd = message.payload.get("cwd")
            
            # Create PTY session
            pty_session_id = await pty_manager.create_session(shell=shell, cwd=cwd)
            
            # Update connection with PTY session ID
            if connection_id in self.active_connections:
                self.active_connections[connection_id].pty_session_id = pty_session_id
            
            # Send success response
            await self.send_to_connection(connection_id, WebSocketMessage(
                type="pty_spawn",
                payload={
                    "success": True,
                    "pty_session_id": pty_session_id,
                    "shell": shell
                },
                session_id=message.session_id
            ))
            
            # Start output monitoring
            asyncio.create_task(self._monitor_pty_session(connection_id, pty_session_id))
            
        except Exception as e:
            logger.error(f"Error spawning PTY: {e}")
            await self.send_to_connection(connection_id, WebSocketMessage(
                type="pty_spawn",
                payload={
                    "success": False,
                    "error": str(e)
                },
                session_id=message.session_id
            ))
    
    async def handle_pty_write(self, connection_id: str, message: WebSocketMessage) -> None:
        """Handle PTY write request."""
        try:
            data = message.payload.get("data", "")
            pty_session_id = self._get_pty_session_id(connection_id, message)
            
            if not pty_session_id:
                await self.send_error_to_connection(connection_id, "No active PTY session")
                return
            
            success = await pty_manager.write_to_session(pty_session_id, data)
            if not success:
                await self.send_error_to_connection(connection_id, "Failed to write to PTY session")
            
        except Exception as e:
            logger.error(f"Error writing to PTY: {e}")
            await self.send_error_to_connection(connection_id, f"PTY write error: {str(e)}")
    
    async def handle_pty_resize(self, connection_id: str, message: WebSocketMessage) -> None:
        """Handle PTY resize request."""
        try:
            cols = message.payload.get("cols", 80)
            rows = message.payload.get("rows", 24)
            pty_session_id = self._get_pty_session_id(connection_id, message)
            
            if not pty_session_id:
                await self.send_error_to_connection(connection_id, "No active PTY session")
                return
            
            pty_manager.resize_session(pty_session_id, cols, rows)
            
        except Exception as e:
            logger.error(f"Error resizing PTY: {e}")
            await self.send_error_to_connection(connection_id, f"PTY resize error: {str(e)}")
    
    def _get_pty_session_id(self, connection_id: str, message: WebSocketMessage) -> Optional[str]:
        """Get PTY session ID from message payload or connection info."""
        pty_session_id = message.payload.get("pty_session_id")
        
        if not pty_session_id:
            connection_info = self.active_connections.get(connection_id)
            if connection_info:
                pty_session_id = connection_info.pty_session_id
                
        return pty_session_id
    
    async def _monitor_pty_session(self, connection_id: str, pty_session_id: str):
        """Monitor PTY session and forward output to WebSocket."""
        try:
            while connection_id in self.active_connections:
                session = pty_manager.get_session(pty_session_id)
                if not session or not session.running:
                    break
                
                output = await pty_manager.read_from_session(pty_session_id)
                if output:
                    await self.send_to_connection(connection_id, WebSocketMessage(
                        type="pty_output",
                        payload={
                            "pty_session_id": pty_session_id,
                            "data": output
                        }
                    ))
                
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error monitoring PTY session {pty_session_id}: {e}")
            if connection_id in self.active_connections:
                await self.send_error_to_connection(connection_id, f"PTY monitoring error: {str(e)}")
    
    async def _cleanup_pty_session(self, pty_session_id: str):
        """Clean up PTY session."""
        try:
            await pty_manager.terminate_session(pty_session_id)
            logger.info(f"Cleaned up PTY session: {pty_session_id}")
        except Exception as e:
            logger.error(f"Error cleaning up PTY session {pty_session_id}: {e}")

    # ----------------------------------------------------------------------------
    # GRAPH FUNCTIONALITY
    # ----------------------------------------------------------------------------

    async def handle_graph_interaction(self, connection_id: str, message: WebSocketMessage) -> None:
        """Handle graph visualization interaction."""
        # Handle graph updates, node selection, etc.
        await self.send_to_connection(connection_id, WebSocketMessage(
            type="graph_update",
            payload={"status": "not_implemented"},
            session_id=message.session_id
        ))
    
    # ----------------------------------------------------------------------------
    # FILE/SETTINGS FUNCTIONALITY
    # ----------------------------------------------------------------------------
    
    async def handle_terraform_command(self, connection_id: str, message: WebSocketMessage) -> None:
        """Handle Terraform command execution."""
        # This will be handled by the infrastructure manager
        await self.send_to_connection(connection_id, WebSocketMessage(
            type="terraform_output",
            payload={"status": "not_implemented"},
            session_id=message.session_id
        ))
    
    async def handle_settings_update(self, connection_id: str, message: WebSocketMessage) -> None:
        """Handle settings update."""
        # Update application settings
        await self.send_to_connection(connection_id, WebSocketMessage(
            type="settings_updated",
            payload={"status": "not_implemented"},
            session_id=message.session_id
        ))
    
    async def handle_heartbeat(self, connection_id: str, message: WebSocketMessage) -> None:
        """Handle heartbeat message."""
        await self.send_to_connection(connection_id, WebSocketMessage(
            type="heartbeat_response",
            payload={"timestamp": datetime.utcnow().isoformat()}
        ))
    
    # ----------------------------------------------------------------------------
    # CORE WEBSOCKET UTILITIES
    # ----------------------------------------------------------------------------
    
    async def send_to_connection(self, connection_id: str, message: WebSocketMessage) -> None:
        """Send message to a specific connection."""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id].websocket
            await websocket.send_text(message.model_dump_json())
    
    async def send_to_session(self, session_id: str, message: WebSocketMessage) -> None:
        """Send message to all connections in a session."""
        connection_id = self.session_to_connection.get(session_id)
        if connection_id:
            await self.send_to_connection(connection_id, message)
    
    async def broadcast_to_all(self, message: WebSocketMessage) -> None:
        """Broadcast message to all connected clients."""
        for connection_id in self.active_connections.keys():
            try:
                await self.send_to_connection(connection_id, message)
            except Exception:
                # Connection might be dead, will be cleaned up later
                pass
    
    async def send_error_to_connection(self, connection_id: str, error_message: str) -> None:
        """Send error message to connection."""
        await self.send_to_connection(connection_id, WebSocketMessage(
            type="error",
            payload={"message": error_message}
        ))
    
    async def send_error(self, websocket: WebSocket, error_message: str) -> None:
        """Send error message directly to WebSocket."""
        error_msg = WebSocketMessage(
            type="error",
            payload={"message": error_message}
        )
        await websocket.send_text(error_msg.model_dump_json())
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs."""
        return list(self.session_to_connection.keys())
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)