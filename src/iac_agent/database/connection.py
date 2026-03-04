"""Database connection and models."""

from typing import Optional, Dict, Any
import asyncio
import json
import uuid
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, create_engine, text, select, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.sqlite import JSON

from iac_agent.core.config import settings

Base = declarative_base()


class AgentSession(Base):
    """Agent session state tracking."""
    __tablename__ = "agent_sessions"

    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    workspace_path = Column(String)
    current_state = Column(String)  # LangGraph state node
    state_data = Column(JSON)  # Serialized state data
    is_active = Column(Boolean, default=True)


class WorkflowCheckpoint(Base):
    """LangGraph workflow checkpoints."""
    __tablename__ = "workflow_checkpoints"

    id = Column(String, primary_key=True)
    session_id = Column(String)
    node_id = Column(String)
    checkpoint_data = Column(Text)  # Serialized checkpoint
    created_at = Column(DateTime, default=datetime.utcnow)


class TerraformState(Base):
    """Terraform state metadata tracking."""
    __tablename__ = "terraform_states"

    id = Column(String, primary_key=True)
    session_id = Column(String)
    workspace_path = Column(String)
    state_hash = Column(String)  # Hash of terraform.tfstate
    resource_count = Column(Integer, default=0)
    last_plan = Column(Text)  # Last terraform plan output
    last_apply = Column(Text)  # Last terraform apply output
    updated_at = Column(DateTime, default=datetime.utcnow)


class LLMInteraction(Base):
    """LLM interaction logging."""
    __tablename__ = "llm_interactions"

    id = Column(String, primary_key=True)
    session_id = Column(String)
    provider = Column(String)
    model = Column(String)
    prompt = Column(Text)
    response = Column(Text)
    tokens_used = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class Database:
    """Database connection manager."""
    
    engine: Optional[AsyncEngine] = None
    session_factory: Optional[async_sessionmaker] = None
    
    @classmethod
    async def initialize(cls) -> None:
        """Initialize the database connection."""
        database_url = settings.database.url.replace("sqlite://", "sqlite+aiosqlite://")
        
        cls.engine = create_async_engine(
            database_url,
            echo=settings.database.echo,
            future=True
        )
        
        cls.session_factory = async_sessionmaker(
            cls.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create tables
        async with cls.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    @classmethod
    async def close(cls) -> None:
        """Close the database connection."""
        if cls.engine:
            await cls.engine.dispose()
    
    @classmethod
    def get_session(cls) -> AsyncSession:
        """Get an async database session."""
        if not cls.session_factory:
            raise RuntimeError("Database not initialized")
        return cls.session_factory()
    
    @classmethod
    async def save_agent_session(cls, session_id: str, workspace_path: str, 
                                current_state: str, state_data: dict) -> None:
        """Save or update agent session state."""
        async with cls.get_session() as session:
            existing = await session.get(AgentSession, session_id)
            
            if existing:
                existing.last_active = datetime.utcnow()
                existing.current_state = current_state
                existing.state_data = state_data
            else:
                new_session = AgentSession(
                    id=session_id,
                    workspace_path=workspace_path,
                    current_state=current_state,
                    state_data=state_data
                )
                session.add(new_session)
            
            await session.commit()
    
    @classmethod
    async def load_agent_session(cls, session_id: str) -> Optional[dict]:
        """Load agent session state."""
        async with cls.get_session() as session:
            agent_session = await session.get(AgentSession, session_id)
            if agent_session:
                return {
                    "id": agent_session.id,
                    "workspace_path": agent_session.workspace_path,
                    "current_state": agent_session.current_state,
                    "state_data": agent_session.state_data,
                    "created_at": agent_session.created_at,
                    "last_active": agent_session.last_active
                }
        return None
    
    @classmethod
    async def save_checkpoint(cls, checkpoint_id: str, session_id: str, 
                            node_id: str, checkpoint_data: str) -> None:
        """Save workflow checkpoint."""
        async with cls.get_session() as session:
            checkpoint = WorkflowCheckpoint(
                id=checkpoint_id,
                session_id=session_id,
                node_id=node_id,
                checkpoint_data=checkpoint_data
            )
            session.add(checkpoint)
            await session.commit()
    
    @classmethod
    async def save_terraform_state(cls, session_id: str, workspace_path: str,
                                 state_hash: str, resource_count: int) -> None:
        """Save terraform state metadata."""
        async with cls.get_session() as session:
            # Check if exists
            existing = None
            result = await session.execute(
                f"SELECT * FROM terraform_states WHERE session_id = '{session_id}'"
            )
            existing_row = result.fetchone()
            
            if existing_row:
                await session.execute(
                    f"""UPDATE terraform_states 
                    SET state_hash = '{state_hash}', 
                        resource_count = {resource_count},
                        updated_at = '{datetime.utcnow()}'
                    WHERE session_id = '{session_id}'"""
                )
            else:
                tf_state = TerraformState(
                    id=f"{session_id}_tf",
                    session_id=session_id,
                    workspace_path=workspace_path,
                    state_hash=state_hash,
                    resource_count=resource_count
                )
                session.add(tf_state)
            
            await session.commit()


class WorkflowStateManager:
    """Manage LangGraph workflow state persistence."""
    
    @classmethod
    async def save_workflow_state(cls, session_id: str, state_data: Dict[str, Any]) -> str:
        """Save current workflow state and return checkpoint ID."""
        checkpoint_id = str(uuid.uuid4())
        
        # Serialize state for storage
        serialized_state = {
            "state_type": "iac_workflow",
            "state_data": state_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await Database.save_checkpoint(
            checkpoint_id=checkpoint_id,
            session_id=session_id,
            node_id=state_data.get("current_operation", "unknown"),
            checkpoint_data=json.dumps(serialized_state)
        )
        
        return checkpoint_id
    
    @classmethod
    async def load_workflow_state(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """Load the latest workflow state for a session."""
        async with Database.get_session() as session:
            # Get the most recent checkpoint for this session using proper SQLAlchemy query
            stmt = select(WorkflowCheckpoint).where(
                WorkflowCheckpoint.session_id == session_id
            ).order_by(WorkflowCheckpoint.created_at.desc()).limit(1)
            
            result = await session.execute(stmt)
            checkpoint = result.scalar_one_or_none()
            
            if checkpoint:
                try:
                    checkpoint_data = json.loads(checkpoint.checkpoint_data)
                    return checkpoint_data.get("state_data")
                except (json.JSONDecodeError, KeyError):
                    return None
        
        return None
    
    @classmethod
    async def update_terraform_context(cls, session_id: str, state_hash: str, 
                                     resources: list) -> None:
        """Update terraform context in the latest workflow state."""
        current_state = await cls.load_workflow_state(session_id)
        if current_state:
            current_state["terraform_state_hash"] = state_hash
            current_state["terraform_resources"] = resources
            await cls.save_workflow_state(session_id, current_state)
    
    @classmethod
    async def clear_workflow_state(cls, session_id: str) -> None:
        """Clear workflow state for a session (useful for testing)."""
        async with Database.get_session() as session:
            stmt = delete(WorkflowCheckpoint).where(WorkflowCheckpoint.session_id == session_id)
            await session.execute(stmt)
            await session.commit()
    
    @classmethod
    async def get_workflow_history(cls, session_id: str, limit: int = 10) -> list:
        """Get workflow checkpoint history for debugging."""
        async with Database.get_session() as session:
            stmt = select(
                WorkflowCheckpoint.node_id, 
                WorkflowCheckpoint.created_at, 
                WorkflowCheckpoint.checkpoint_data
            ).where(
                WorkflowCheckpoint.session_id == session_id
            ).order_by(WorkflowCheckpoint.created_at.desc()).limit(limit)
            
            result = await session.execute(stmt)
            
            history = []
            for row in result.fetchall():
                try:
                    checkpoint_data = json.loads(row[2])
                    history.append({
                        "node_id": row[0],
                        "created_at": row[1],
                        "operation": checkpoint_data.get("state_data", {}).get("current_operation"),
                        "timestamp": checkpoint_data.get("timestamp")
                    })
                except (json.JSONDecodeError, KeyError):
                    continue
            
            return history