"""Simple LLM Manager using OpenAI SDK with tool support."""

from typing import List, Dict, Any, AsyncGenerator, Optional
from dataclasses import dataclass
import json
from openai import AsyncOpenAI

from iac_agent.core.config import settings


@dataclass
class LLMMessage:
    """Simple message format."""
    role: str  # system, user, assistant
    content: str


@dataclass
class LLMResponse:
    """Simple response format."""
    content: str
    model: str = ""
    tokens_used: int = 0
    tool_calls: Optional[List[Dict[str, Any]]] = None
    
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return bool(self.tool_calls)


class SimpleLLMManager:
    """Simple LLM manager using OpenAI SDK."""
    
    def __init__(self):
        self.client = None
        self._update_client()
    
    def _update_client(self):
        """Update the OpenAI client with current settings."""
        if settings.llm.api_key:
            self.client = AsyncOpenAI(
                base_url=settings.llm.endpoint,
                api_key=settings.llm.api_key
            )
        else:
            self.client = None
    
    def is_configured(self) -> bool:
        """Check if LLM is properly configured."""
        return bool(settings.llm.api_key and settings.llm.endpoint and settings.llm.model_name)
    
    async def generate_response(self, messages: List[LLMMessage], tools: List[Dict[str, Any]] = None, **kwargs) -> LLMResponse:
        """Generate response from LLM with optional tool support."""
        if not self.client:
            raise RuntimeError("LLM not configured. Please set API key and endpoint.")
        
        # Convert to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        try:
            # Prepare request parameters
            request_params = {
                "model": settings.llm.deployment_name or settings.llm.model_name,
                "messages": openai_messages,
                "max_tokens": kwargs.get('max_tokens', 4096),
                "temperature": kwargs.get('temperature', 0.1),
            }
            
            # Add tools if provided
            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = "auto"
            
            response = await self.client.chat.completions.create(**request_params)
            
            # Extract tool calls if present
            tool_calls = None
            message = response.choices[0].message
            if hasattr(message, 'tool_calls') and message.tool_calls:
                tool_calls = []
                for tool_call in message.tool_calls:
                    tool_calls.append({
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": json.loads(tool_call.function.arguments)
                        }
                    })
            
            return LLMResponse(
                content=message.content or "",
                model=response.model,
                tokens_used=response.usage.total_tokens if response.usage else 0,
                tool_calls=tool_calls
            )
            
        except Exception as e:
            raise RuntimeError(f"LLM API error: {str(e)}")
    
    async def stream_response(self, messages: List[LLMMessage], **kwargs) -> AsyncGenerator[str, None]:
        """Stream response from LLM."""
        if not self.client:
            yield "Error: LLM not configured. Please set API key and endpoint."
            return
        
        # Convert to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        try:
            stream = await self.client.chat.completions.create(
                model=settings.llm.deployment_name or settings.llm.model_name,
                messages=openai_messages,
                max_tokens=kwargs.get('max_tokens', 4096),
                temperature=kwargs.get('temperature', 0.1),
                stream=True,
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"Error: {str(e)}"
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test the LLM connection."""
        if not self.client:
            return {
                "status": "error",
                "error": "Not configured. Please set API key and endpoint."
            }
        
        try:
            # Simple test message
            test_message = LLMMessage(role="user", content="Say 'Connection test successful'")
            response = await self.generate_response([test_message])
            
            return {
                "status": "success",
                "model": response.model,
                "response": response.content[:100] + "..." if len(response.content) > 100 else response.content
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def update_config(self, endpoint: str, api_key: str, model_name: str, deployment_name: str = None):
        """Update LLM configuration."""
        settings.llm.endpoint = endpoint
        settings.llm.api_key = api_key
        settings.llm.model_name = model_name
        settings.llm.deployment_name = deployment_name
        
        # Update client
        self._update_client()


# Global LLM manager instance
llm_manager = SimpleLLMManager()