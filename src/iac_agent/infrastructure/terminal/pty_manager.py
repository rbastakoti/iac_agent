"""
PTY Manager for terminal sessions
Compatible with the existing WebSocket manager architecture
"""
import asyncio
import logging
import uuid
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from winpty import PtyProcess
    WINPTY_AVAILABLE = True
except ImportError:
    WINPTY_AVAILABLE = False
    logger.warning("winpty not available - terminal functionality will be limited")


class PTYSession:
    """Represents a single PTY session"""
    
    def __init__(self, session_id: str, shell: str = None, cwd: str = None):
        self.session_id = session_id
        self.shell = shell or "powershell.exe"
        self.cwd = cwd
        self.process: Optional[PtyProcess] = None
        self.running = False
        self._lock = asyncio.Lock()
        
    async def start(self, cols: int = 80, rows: int = 24) -> bool:
        """Start the PTY process"""
        if not WINPTY_AVAILABLE:
            raise Exception("winpty not available - cannot start terminal")
        
        try:
            # Spawn the process with specified dimensions
            self.process = PtyProcess.spawn(
                self.shell, 
                dimensions=(rows, cols),
                cwd=self.cwd
            )
            self.running = True
            logger.info(f"PTY session {self.session_id} started with shell: {self.shell}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start PTY session {self.session_id}: {e}")
            raise
    
    async def write(self, data: str):
        """Write data to the PTY"""
        if self.process and self.running:
            try:
                self.process.write(data)
            except Exception as e:
                logger.error(f"Error writing to PTY session {self.session_id}: {e}")
                raise
    
    async def read(self) -> str:
        """Read available output from the PTY"""
        if not self.process or not self.running:
            return ""
        
        try:
            # Use run_in_executor to make the blocking read non-blocking
            loop = asyncio.get_event_loop()
            output = await loop.run_in_executor(None, self._read_output)
            return output or ""
        except Exception as e:
            logger.error(f"Error reading from PTY session {self.session_id}: {e}")
            return ""
    
    def _read_output(self) -> str:
        """Blocking read from PTY - called in executor"""
        try:
            if self.process:
                return self.process.read()
        except (OSError, IOError) as e:
            logger.debug(f"PTY read error in session {self.session_id}: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error reading PTY session {self.session_id}: {e}")
            return ""
        return ""
    
    def resize(self, cols: int, rows: int):
        """Resize the PTY"""
        # Validate input parameters
        if not isinstance(cols, int) or not isinstance(rows, int):
            raise ValueError("Columns and rows must be integers")
        if cols < 1 or rows < 1 or cols > 200 or rows > 100:
            raise ValueError("Invalid terminal dimensions")
            
        if self.process and self.running:
            try:
                # Use setwinsize instead of set_size for winpty
                if hasattr(self.process, 'setwinsize'):
                    self.process.setwinsize(rows, cols)
                elif hasattr(self.process, 'set_size'):
                    self.process.set_size(rows, cols)
                else:
                    raise NotImplementedError(f"PTY resize not supported for session {self.session_id}")
            except Exception as e:
                logger.error(f"Error resizing PTY session {self.session_id}: {e}")
                raise
    
    async def terminate(self):
        """Terminate the PTY session"""
        self.running = False
        if self.process:
            try:
                self.process.terminate()
                logger.info(f"PTY session {self.session_id} terminated")
            except Exception as e:
                logger.error(f"Error terminating PTY session {self.session_id}: {e}")
            finally:
                self.process = None


class PTYManager:
    """Manages multiple PTY sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, PTYSession] = {}
        
    async def create_session(self, shell: str = None, cwd: str = None) -> str:
        """Create a new PTY session and return its ID"""
        session_id = str(uuid.uuid4())
        session = PTYSession(session_id, shell, cwd)
        
        try:
            await session.start()
            self.sessions[session_id] = session
            return session_id
        except Exception as e:
            logger.error(f"Failed to create PTY session: {e}")
            raise
    
    def get_session(self, session_id: str) -> Optional[PTYSession]:
        """Get a PTY session by ID"""
        return self.sessions.get(session_id)
    
    async def write_to_session(self, session_id: str, data: str) -> bool:
        """Write data to a specific PTY session"""
        session = self.sessions.get(session_id)
        if session and session.running:
            try:
                await session.write(data)
                return True
            except Exception as e:
                logger.error(f"Failed to write to session {session_id}: {e}")
                return False
        return False
    
    async def read_from_session(self, session_id: str) -> str:
        """Read available output from a specific PTY session"""
        session = self.sessions.get(session_id)
        if session and session.running:
            try:
                return await session.read()
            except Exception as e:
                logger.error(f"Failed to read from session {session_id}: {e}")
                return ""
        return ""
    
    def resize_session(self, session_id: str, cols: int, rows: int):
        """Resize a specific PTY session"""
        session = self.sessions.get(session_id)
        if session and session.running:
            session.resize(cols, rows)
    
    async def terminate_session(self, session_id: str):
        """Terminate a specific PTY session"""
        session = self.sessions.get(session_id)
        if session:
            await session.terminate()
            if session_id in self.sessions:
                del self.sessions[session_id]
    
    async def terminate_all_sessions(self):
        """Terminate all active PTY sessions"""
        for session_id in list(self.sessions.keys()):
            await self.terminate_session(session_id)
    
    def get_active_session_count(self) -> int:
        """Get the number of active sessions"""
        return len([s for s in self.sessions.values() if s.running])
    
    def list_sessions(self) -> Dict[str, Dict[str, Any]]:
        """List all sessions with their info"""
        return {
            sid: {
                "shell": session.shell,
                "cwd": session.cwd,
                "running": session.running
            }
            for sid, session in self.sessions.items()
        }


# Global PTY manager instance
pty_manager = PTYManager()