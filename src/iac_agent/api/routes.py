"""API routes for the IaC Agent."""

from typing import Dict, Any, List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from iac_agent.core.config import settings
from iac_agent.database.connection import Database


# Request/Response Models for simple LLM config
class LLMConfigRequest(BaseModel):
    endpoint: str
    api_key: str
    model_name: str
    deployment_name: Optional[str] = None


class LLMConfigResponse(BaseModel):
    endpoint: str
    model_name: str
    deployment_name: Optional[str]
    is_configured: bool
    status: Optional[str] = None


class WorkspaceInfoResponse(BaseModel):
    workspace_path: str
    terraform_files: List[str]
    state_exists: bool
    resource_count: int


class SettingsResponse(BaseModel):
    llm_configured: bool
    llm_endpoint: str
    llm_model: str
    workspace_path: str
    max_resources: int


# Router
api_router = APIRouter()


@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "iac-agent"}


@api_router.get("/test-pty")
async def test_pty():
    """Test PTY functionality without WebSocket."""
    from iac_agent.infrastructure.terminal.pty_manager import pty_manager
    
    try:
        # Test creating a PTY session
        session_id = await pty_manager.create_session()
        
        # Test writing to it
        writing_success = await pty_manager.write_to_session(session_id, "echo 'PTY Test'\r\n")
        
        # Wait a moment for output
        import asyncio
        await asyncio.sleep(0.5)
        
        # Test reading from it 
        output = await pty_manager.read_from_session(session_id)
        
        # Clean up
        await pty_manager.terminate_session(session_id)
        
        return {
            "success": True,
            "session_id": session_id, 
            "writing_success": writing_success,
            "output": output or "No output received"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    return {"status": "healthy", "app": settings.app_name}


@api_router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Get current application settings."""
    return SettingsResponse(
        llm_configured=settings.is_llm_configured(),
        llm_endpoint=settings.llm.endpoint,
        llm_model=settings.llm.model_name,
        workspace_path=str(settings.infrastructure.workspace_directory),
        max_resources=settings.infrastructure.max_resources
    )


# Legacy provider endpoints removed - using simplified LLM config instead


@api_router.get("/workspace", response_model=WorkspaceInfoResponse)
async def get_workspace_info():
    """Get current workspace information."""
    workspace_path = settings.infrastructure.workspace_directory
    
    # Find Terraform files
    terraform_files = []
    if workspace_path.exists():
        terraform_files = [
            f.name for f in workspace_path.glob("*.tf")
        ]
    
    # Check for state file
    state_file = workspace_path / "terraform.tfstate"
    state_exists = state_file.exists()
    
    # Count resources (simplified)
    resource_count = 0
    if state_exists:
        try:
            import json
            with open(state_file) as f:
                state_data = json.load(f)
                resource_count = len(state_data.get("resources", []))
        except Exception:
            resource_count = 0
    
    return WorkspaceInfoResponse(
        workspace_path=str(workspace_path),
        terraform_files=terraform_files,
        state_exists=state_exists,
        resource_count=resource_count
    )


@api_router.post("/workspace/upload")
async def upload_terraform_files(files: List[UploadFile] = File(...)):
    """Upload Terraform files to workspace."""
    workspace_path = settings.infrastructure.workspace_directory
    workspace_path.mkdir(exist_ok=True)
    
    uploaded_files = []
    for file in files:
        if not file.filename.endswith(('.tf', '.tfvars', '.tfstate')):
            continue
            
        file_path = workspace_path / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        uploaded_files.append(file.filename)
    
    return {"uploaded_files": uploaded_files}


@api_router.get("/sessions")
async def get_active_sessions():
    """Get list of active agent sessions."""
    # This would integrate with the session manager
    return {"sessions": [], "count": 0}


# Simple LLM Configuration Endpoints
@api_router.get("/llm/config", response_model=LLMConfigResponse)
async def get_llm_config():
    """Get current LLM configuration."""
    return LLMConfigResponse(
        endpoint=settings.llm.endpoint,
        model_name=settings.llm.model_name,
        deployment_name=settings.llm.deployment_name,
        is_configured=settings.is_llm_configured(),
        status="configured" if settings.is_llm_configured() else "not_configured"
    )


@api_router.post("/llm/config")
async def update_llm_config(request: LLMConfigRequest):
    """Update LLM configuration."""
    from iac_agent.providers.llm_manager import llm_manager
    
    # Update settings
    settings.update_llm_config(
        endpoint=request.endpoint,
        api_key=request.api_key,
        model_name=request.model_name,
        deployment_name=request.deployment_name
    )
    
    # Save credentials to .env file for persistence
    try:
        settings.save_credentials_to_env()
    except Exception as e:
        print(f"Warning: Failed to save credentials to .env file: {e}")
    
    # Update manager
    llm_manager.update_config(
        endpoint=request.endpoint,
        api_key=request.api_key,
        model_name=request.model_name,
        deployment_name=request.deployment_name
    )
    
    return {"status": "updated", "message": "LLM configuration updated and saved successfully"}


@api_router.post("/llm/test")
async def test_llm_config():
    """Test current LLM configuration."""
    from iac_agent.providers.llm_manager import llm_manager
    
    return await llm_manager.test_connection()


@api_router.post("/terraform/plan")
async def run_terraform_plan():
    """Run terraform plan in current workspace."""
    # This would integrate with the terraform manager
    return {"status": "not_implemented"}


@api_router.post("/terraform/apply")
async def run_terraform_apply():
    """Run terraform apply in current workspace."""
    # This would integrate with the terraform manager
    return {"status": "not_implemented"}


@api_router.get("/graph/data")
async def get_graph_data():
    """Get infrastructure graph data."""
    # This would return React Flow compatible node/edge data
    return {
        "nodes": [],
        "edges": [],
        "ghost_nodes": []
    }


@api_router.post("/azure/import")
async def import_azure_resources(resource_group: str, subscription_id: str = None):
    """Import Azure resources using aztfexport."""
    # This would integrate with the Azure discovery module
    return {"status": "not_implemented"}


@api_router.get("/binaries/status")
async def get_binary_status():
    """Get status of required binaries."""
    from iac_agent.infrastructure.binary_manager import BinaryManager
    
    binary_manager = BinaryManager()
    status = await binary_manager.check_binaries()
    
    return {"binaries": status}


@api_router.post("/binaries/install")
async def install_binaries():
    """Install missing binaries."""
    from iac_agent.infrastructure.binary_manager import BinaryManager
    
    binary_manager = BinaryManager()
    result = await binary_manager.ensure_binaries()
    
    return {"status": "completed", "installed": result}