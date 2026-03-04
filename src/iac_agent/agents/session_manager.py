"""Agent session manager for handling user interactions with real MCP integration."""

import uuid
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime

from iac_agent.core.config import settings
from iac_agent.providers.llm_manager import llm_manager, LLMMessage
from iac_agent.mcp import mcp_client


class AgentSession:
    """Represents an active agent session."""
    
    def __init__(self, session_id: str, workspace_path: str):
        self.session_id = session_id
        self.workspace_path = workspace_path
        self.created_at = datetime.utcnow()
        self.last_active = datetime.utcnow()
        self.conversation_history: List[Dict[str, Any]] = []
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_active = datetime.utcnow()
    
    def add_message(self, role: str, content: str):
        """Add message to conversation history."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.conversation_history.append(message)
        self.update_activity()
    
    def get_context(self) -> Dict[str, Any]:
        """Get current session context."""
        return {
            "session_id": self.session_id,
            "workspace_path": self.workspace_path,
            "message_count": len(self.conversation_history),
            "last_active": self.last_active.isoformat()
        }


class SessionManager:
    """Manages agent sessions and interactions with real MCP integration."""
    
    def __init__(self, websocket_manager=None):
        self.active_sessions: Dict[str, AgentSession] = {}
        self.websocket_manager = websocket_manager
        self._mcp_initialized = False
        self.logger = logging.getLogger(__name__)
        # Reference to MCP client for direct access
        self.mcp_client = mcp_client
    
    async def _ensure_mcp_initialized(self):
        """Ensure FastMCP client is initialized."""
        if not self._mcp_initialized:
            try:
                # Start the FastMCP file server 
                workspace_path = str(settings.infrastructure.workspace_directory)
                self.logger.info(f"💾 [Session Manager] Initializing MCP with workspace: {workspace_path}")
                await mcp_client.start_file_server(workspace_path)
                self._mcp_initialized = True
                self.logger.info("💾 [Session Manager] FastMCP file server started successfully")
            except Exception as e:
                self.logger.error(f"💾 [Session Manager] Failed to initialize FastMCP: {str(e)}")
                import traceback
                self.logger.error(f"💾 [Session Manager] Full traceback: {traceback.format_exc()}")
                raise
        else:
            self.logger.info("💾 [Session Manager] MCP already initialized")
    
    async def create_session(self, workspace_path: str = None) -> str:
        """Create a new agent session."""
        session_id = str(uuid.uuid4())
        return await self.create_session_with_id(session_id, workspace_path)
    
    async def create_session_with_id(self, session_id: str, workspace_path: str = None) -> str:
        """Create a new agent session with specified ID."""
        if not workspace_path:
            workspace_path = str(settings.infrastructure.workspace_directory)
        
        session = AgentSession(session_id, workspace_path)
        self.active_sessions[session_id] = session
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Get an active session."""
        return self.active_sessions.get(session_id)
    
    async def process_user_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """Process a user message and generate agent response with MCP tools."""
        # Ensure MCP is initialized
        await self._ensure_mcp_initialized()
        
        session = await self.get_session(session_id)
        if not session:
            # Create new session with the provided session_id (don't generate new UUID)
            await self.create_session_with_id(session_id)
            session = await self.get_session(session_id)
        
        # Generate LLM response
        try:
            # Convert conversation history to LLM format
            llm_messages = []
            
            # Add system message for context with MCP tools
            llm_messages.append(LLMMessage(
                role="system", 
                content="""You are an Infrastructure as Code (IaC) agent assistant with file system access.
You can help users manage Terraform files in their workspace using the following tools:

- file_server___read_file: Read the contents of a file
- file_server___write_file: Write content to a file 
- file_server___list_files: List files in a directory (use pattern='*.tf' for Terraform files)
- file_server___create_terraform_resource: Create new Terraform resource blocks
- file_server___delete_file: Delete files

When users ask to:
- "Show my files" or "List my Terraform files" → Use file_server___list_files with pattern='*.tf'
- "Read main.tf" or "Show me the content of X" → Use file_server___read_file
- "Add a database" or "Create a storage account" → Use file_server___create_terraform_resource
- "Update a file" or "Change the configuration" → Use file_server___write_file
- "Delete old files" → Use file_server___delete_file

Always be helpful and explain what operations you're performing."""
            ))
            
            # Add conversation history (last 20 messages to prevent context overflow)
            recent_messages = session.conversation_history[-20:]
            for msg in recent_messages:
                llm_messages.append(LLMMessage(
                    role=msg["role"],
                    content=msg["content"]
                ))
            
            # Add current user message (don't add to history yet)
            llm_messages.append(LLMMessage(
                role="user",
                content=message
            ))
            
            # Check if LLM is configured
            if not llm_manager.is_configured():
                response_content = "⚠️ LLM is not configured. Please configure your AI model settings in the application."
                metadata = {
                    "action": "configuration_needed",
                    "error": True,
                    "error_type": "llm_not_configured"
                }
            else:
                # Get MCP tools 
                mcp_tools = mcp_client.get_all_tools()
                
                # Generate LLM response with MCP tools
                llm_response = await llm_manager.generate_response(
                    messages=llm_messages,
                    tools=mcp_tools,
                    temperature=0.1,
                    max_tokens=2048
                )
                
                response_content = llm_response.content or ""
                
                # Handle tool calls if present
                if llm_response.has_tool_calls():
                    self.logger.info(f"Processing {len(llm_response.tool_calls)} MCP tool calls")
                    tool_results = []
                    
                    for tool_call in llm_response.tool_calls:
                        function_name = tool_call['function']['name']
                        arguments = tool_call['function']['arguments']
                        
                        self.logger.info(f"Executing MCP tool: {function_name}")
                        
                        try:
                            # Execute MCP tool
                            result = await mcp_client.execute_tool_call(function_name, arguments)
                            tool_results.append({
                                'tool': function_name,
                                'success': True,
                                'result': result
                            })
                        except Exception as e:
                            self.logger.error(f"MCP tool call failed: {str(e)}")
                            tool_results.append({
                                'tool': function_name,
                                'success': False,
                                'error': str(e)
                            })
                    
                    # Generate final response based on tool results
                    tool_summary = []
                    for tr in tool_results:
                        if tr['success']:
                            if 'content' in tr['result']:
                                content_text = tr['result']['content'][0].get('text', '') if tr['result']['content'] else ''
                                tool_summary.append(f"✅ {tr['tool']}: {content_text}")
                            else:
                                tool_summary.append(f"✅ {tr['tool']}: Executed successfully")
                        else:
                            tool_summary.append(f"❌ {tr['tool']}: {tr['error']}")
                    
                    tool_context = LLMMessage(
                        role='user',
                        content=f"Tool execution results:\n{chr(10).join(tool_summary)}\n\nPlease provide a helpful summary of what was accomplished."
                    )
                    
                    final_response = await llm_manager.generate_response(
                        messages=llm_messages + [tool_context],
                        temperature=0.1
                    )
                    response_content = final_response.content
                
                metadata = {
                    "action": "chat_response",
                    "model": llm_response.model,
                    "tokens_used": llm_response.tokens_used,
                    "session_id": session_id,
                    "mcp_tools_used": len(llm_response.tool_calls) if llm_response.has_tool_calls() else 0
                }
            
        except Exception as e:
            response_content = f"Sorry, I encountered an error processing your message: {str(e)}"
            metadata = {
                "action": "error",
                "error": True,
                "error_type": "llm_error",
                "error_details": str(e)
            }
        
        # NOW add both messages to history after LLM processing
        session.add_message("user", message)
        session.add_message("assistant", response_content)
        
        return {
            "content": response_content,
            "metadata": metadata
        }
    
    def get_active_session_ids(self) -> List[str]:
        """Get list of active session IDs."""
        return list(self.active_sessions.keys())
    
    async def end_session(self, session_id: str) -> bool:
        """End an active session."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        return False
    
    async def shutdown(self):
        """Shutdown session manager and MCP servers."""
        try:
            await mcp_client.shutdown()
            self.logger.info("MCP client shutdown successfully")
        except Exception as e:
            self.logger.error(f"Error shutting down MCP client: {str(e)}")
    
    def get_mcp_status(self) -> Dict[str, Any]:
        """Get MCP server status."""
        if not self._mcp_initialized:
            return {"initialized": False}
        
        return {
            "initialized": True,
            "servers": mcp_client.get_server_status()
        }
    
