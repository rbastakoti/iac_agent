"""Main FastAPI application."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from iac_agent.core.config import settings
from iac_agent.database.connection import Database
from iac_agent.api.websocket_manager import WebSocketManager
from iac_agent.api.routes import api_router
from iac_agent.agents.session_manager import SessionManager
from iac_agent.infrastructure.binary_manager import BinaryManager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    print(f"🚀 Starting {settings.app_name}...")
    
    # Auto-load saved LLM credentials if available
    try:
        if settings.load_credentials_from_env():
            # Update LLM manager with loaded credentials
            from iac_agent.providers.llm_manager import llm_manager
            llm_manager._update_client()
    except Exception as e:
        print(f"⚠️  Warning: Failed to auto-load credentials: {e}")
    
    # Initialize database
    await Database.initialize()
    
    # Initialize binary manager
    binary_manager = BinaryManager()
    await binary_manager.ensure_binaries()
    
    # Create workspace directory
    settings.infrastructure.workspace_directory.mkdir(exist_ok=True)
    
    print(f"✅ Server running at http://{settings.host}:{settings.port}")
    print(f"📁 Workspace: {settings.infrastructure.workspace_directory.absolute()}")
    if settings.is_llm_configured():
        print(f"🤖 LLM configured: {settings.llm.model_name} @ {settings.llm.endpoint}")
    else:
        print("⚠️  LLM not configured - add your API credentials in the web interface")
    
    yield
    
    # Shutdown
    print("🔄 Shutting down...")
    await Database.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title=settings.app_name,
        description="Local-first Jupyter-style workspace for Infrastructure as Code",
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/api")
    
    # Session manager
    session_manager = SessionManager()
    app.state.session_manager = session_manager
    
    # WebSocket manager with shared session manager
    websocket_manager = WebSocketManager()
    websocket_manager.session_manager = session_manager  # Use the same instance
    app.state.websocket_manager = websocket_manager
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """Main WebSocket endpoint for real-time communication."""
        await websocket_manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                await websocket_manager.handle_message(websocket, data)
        except WebSocketDisconnect:
            websocket_manager.disconnect(websocket)
            websocket_manager.disconnect(websocket)
    
    # Static files for the React frontend
    static_dir = Path(__file__).parent / "static" / "web"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Serve the main application page."""
        # Serve the static HTML file instead of generating it
        static_html = static_dir / "index.html"
        if static_html.exists():
            try:
                # Explicitly specify UTF-8 encoding to handle Unicode characters
                return static_html.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # Fallback to the default HTML if there's an encoding issue
                return await get_index_html()
        else:
            return await get_index_html()
    
    return app


async def get_index_html() -> str:
    """Get the main HTML page (fallback version)."""
    return f"""
    <!DOCTYPE html>
    <html lang="en" class="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{settings.app_name}</title>
        
        <!-- React and ReactDOM -->
        <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
        <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
        
        <!-- Tailwind CSS -->
        <script src="https://cdn.tailwindcss.com"></script>
        <script>
            tailwind.config = {{
                theme: {{
                    extend: {{}},
                }},
                darkMode: 'class'
            }}
        </script>
        
        <!-- XTerm.js for terminal -->
        <link rel="stylesheet" href="https://unpkg.com/xterm@5.3.0/css/xterm.css" />
        <script src="https://unpkg.com/xterm@5.3.0/lib/xterm.js"></script>
        <script src="https://unpkg.com/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js"></script>
        
        <!-- React Flow for graph visualization -->
        <script src="https://unpkg.com/@xyflow/react@12.0.0/dist/umd/index.js"></script>
    </head>
    <body>
        <div id="root">
            <div class="flex items-center justify-center h-screen bg-slate-900 text-white">
                <div class="text-center">
                    <div class="text-4xl mb-4">🤖</div>
                    <div class="text-lg">Initializing IaC Agent Workspace...</div>
                    <div class="text-sm text-slate-400 mt-2">Loading Application...</div>
                </div>
            </div>
        </div>
        <script src="/static/web/app.js"></script>
    </body>
    </html>
    """


# Create the app instance
app = create_app()