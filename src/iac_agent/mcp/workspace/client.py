"""Simplified FastMCP client for file operations."""

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile
import os

logger = logging.getLogger(__name__)


class FastMCPClient:
    """Client for FastMCP file server operations."""
    
    def __init__(self):
        self.server_process: Optional[subprocess.Popen] = None
        self.workspace_dir: Optional[Path] = None
        
    async def start_file_server(self, workspace_path: str) -> None:
        """Start the FastMCP file server."""
        try:
            self.workspace_dir = Path(workspace_path).resolve()
            
            # Path to our FastMCP server
            server_script = Path(__file__).parent / "server.py"
            
            # Start the server as a subprocess
            self.server_process = subprocess.Popen([
                sys.executable, 
                str(server_script),
                str(self.workspace_dir)
            ], 
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
            )
            
            logger.info(f"Started FastMCP file server for workspace: {workspace_path}")
            
        except Exception as e:
            logger.error(f"Failed to start FastMCP server: {str(e)}")
            raise
    
    async def list_files(self, pattern: str = "*.tf") -> list:
        """List files matching pattern."""
        if not self.workspace_dir:
            raise ValueError("Workspace directory not set")
        
        import fnmatch
        files = []
        
        try:
            for file_path in self.workspace_dir.rglob(pattern):
                if file_path.is_file():
                    try:
                        stat = file_path.stat()
                        files.append({
                            "name": file_path.name,
                            "path": str(file_path.relative_to(self.workspace_dir)),
                            "full_path": str(file_path),
                            "size": stat.st_size,
                            "modified": stat.st_mtime,
                            "type": "file"
                        })
                    except (OSError, PermissionError):
                        continue
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            raise
        
        return files
    
    async def read_file(self, path: str) -> str:
        """Read file content."""
        if not self.workspace_dir:
            raise ValueError("Workspace directory not set")
        
        file_path = Path(path)
        
        # Ensure relative path within workspace
        if file_path.is_absolute():
            try:
                file_path = file_path.relative_to(self.workspace_dir)
            except ValueError:
                raise ValueError("File path is outside workspace directory")
        
        full_path = self.workspace_dir / file_path
        
        # Security check
        try:
            full_path.resolve().relative_to(self.workspace_dir.resolve())
        except ValueError:
            raise ValueError("File path is outside workspace directory")
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(full_path, 'r', encoding='latin1') as f:
                return f.read()
    
    async def write_file(self, path: str, content: str) -> str:
        """Write content to file."""
        logger.info(f"💾 [MCP Client] write_file called with path: {path}")
        
        if not self.workspace_dir:
            raise ValueError("Workspace directory not set")
        
        file_path = Path(path)
        logger.info(f"💾 [MCP Client] Original file_path: {file_path}")
        
        if file_path.is_absolute():
            try:
                file_path = file_path.relative_to(self.workspace_dir)
                logger.info(f"💾 [MCP Client] Converted to relative: {file_path}")
            except ValueError:
                raise ValueError("File path is outside workspace directory")
        
        full_path = self.workspace_dir / file_path
        logger.info(f"💾 [MCP Client] Full path: {full_path}")
        
        # Security check
        try:
            resolved_path = full_path.resolve()
            resolved_workspace = self.workspace_dir.resolve()
            resolved_path.relative_to(resolved_workspace)
            logger.info(f"💾 [MCP Client] Security check passed")
        except ValueError:
            raise ValueError("File path is outside workspace directory")
        
        # Create directory if needed
        logger.info(f"💾 [MCP Client] Creating parent directories")
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"💾 [MCP Client] Writing {len(content)} characters to file")
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            result = f"Successfully wrote to {path}"
            logger.info(f"💾 [MCP Client] Write successful: {result}")
            return result
        except Exception as e:
            logger.error(f"💾 [MCP Client] Write failed: {str(e)}")
            raise Exception(f"Failed to write file: {str(e)}")
    
    async def execute_tool_call(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call - simplified interface for compatibility."""
        logger.info(f"💾 [MCP Client] execute_tool_call called: {function_name}")
        logger.info(f"💾 [MCP Client] Arguments: {arguments}")
        
        try:
            # Map function names to our methods
            if function_name == "file_server___list_files":
                pattern = arguments.get("pattern", "*.tf")
                result = await self.list_files(pattern)
                
                # Return in expected format
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result)
                    }]
                }
            
            elif function_name == "file_server___read_file":
                path = arguments.get("path")
                if not path:
                    raise ValueError("Path parameter required")
                
                content = await self.read_file(path)
                
                return {
                    "content": [{
                        "type": "text", 
                        "text": content
                    }]
                }
            
            elif function_name == "file_server___write_file":
                logger.info(f"💾 [MCP Client] Starting write operation")
                path = arguments.get("path")
                content = arguments.get("content", "")
                
                logger.info(f"💾 [MCP Client] Write path: {path}")
                logger.info(f"💾 [MCP Client] Write content length: {len(content)}")
                
                if not path:
                    raise ValueError("Path parameter required")
                
                result = await self.write_file(path, content)
                logger.info(f"💾 [MCP Client] Write result: {result}")
                
                response = {
                    "content": [{
                        "type": "text",
                        "text": result
                    }]
                }
                logger.info(f"💾 [MCP Client] Returning response: {response}")
                return response
            
            elif function_name == "file_server___delete_file":
                path = arguments.get("path")
                force = arguments.get("force", False)
                
                if not path:
                    raise ValueError("Path parameter required")
                
                # Direct file deletion with safety checks
                file_path = Path(path)
                if file_path.is_absolute():
                    try:
                        file_path = file_path.relative_to(self.workspace_dir)
                    except ValueError:
                        raise ValueError("File path is outside workspace directory")
                
                full_path = self.workspace_dir / file_path
                
                # Protected file checks
                filename = full_path.name.lower()
                if not force:
                    if (filename.startswith('.terraform') or 
                        filename.endswith('.tfstate') or 
                        filename.endswith('.tfstate.backup') or
                        filename == 'terraform.tfvars' or
                        filename == '.terraform.lock.hcl'):
                        raise ValueError(f"Cannot delete protected terraform file '{path}'. Use force=True to override.")
                
                if not full_path.exists():
                    raise FileNotFoundError(f"File not found: {path}")
                
                full_path.unlink()
                result = f"Successfully deleted {path}"
                
                return {
                    "content": [{
                        "type": "text",
                        "text": result
                    }]
                }
            
            elif function_name == "file_server___create_terraform_resource":
                # This tool uses read-modify-write approach, delegate to read_file and write_file
                result = "Use read_file and write_file tools for complex terraform resource creation"
                
                return {
                    "content": [{
                        "type": "text",
                        "text": result
                    }]
                }
            
            elif function_name == "file_server___terraform_validate":
                # Run terraform validate in workspace
                
                try:
                    result = subprocess.run(
                        ["terraform", "validate", "-json"],
                        cwd=self.workspace_dir,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    validation_result = {
                        "exit_code": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "valid": result.returncode == 0
                    }
                    
                    return {
                        "content": [{
                            "type": "text",
                            "text": json.dumps(validation_result, indent=2)
                        }]
                    }
                    
                except subprocess.TimeoutExpired:
                    raise Exception("Terraform validate timed out after 30 seconds")
                except FileNotFoundError:
                    raise Exception("Terraform command not found. Please ensure terraform is installed and in PATH.")
            
            elif function_name == "file_server___format_hcl":
                # Run terraform fmt in workspace
                
                format_path = arguments.get("path", ".")
                
                try:
                    result = subprocess.run(
                        ["terraform", "fmt", format_path],
                        cwd=self.workspace_dir,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        formatted_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
                        if formatted_files and formatted_files[0]:
                            format_result = f"Formatted {len(formatted_files)} files: {', '.join(formatted_files)}"
                        else:
                            format_result = f"No formatting changes needed for {format_path}"
                    else:
                        raise Exception(f"terraform fmt failed: {result.stderr}")
                    
                    return {
                        "content": [{
                            "type": "text",
                            "text": format_result
                        }]
                    }
                    
                except subprocess.TimeoutExpired:
                    raise Exception("Terraform fmt timed out after 30 seconds")
                except FileNotFoundError:
                    raise Exception("Terraform command not found. Please ensure terraform is installed and in PATH.")
            
            else:
                raise ValueError(f"Unknown function: {function_name}")
                
        except Exception as e:
            logger.error(f"Tool call failed: {str(e)}")
            raise
    
    def get_all_tools(self) -> list:
        """Get all available MCP tools - for compatibility with existing code."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "file_server___list_files",
                    "description": "List files in the workspace directory matching the given pattern",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "File pattern to search for",
                                "default": "*.tf"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "file_server___read_file",
                    "description": "Read the contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the file to read"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "file_server___write_file",
                    "description": "Write content to a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the file to write"
                            },
                            "content": {
                                "type": "string",
                                "description": "Content to write to the file"
                            }
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "file_server___delete_file",
                    "description": "Delete a file with safety checks for important terraform files",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the file to delete"
                            },
                            "force": {
                                "type": "boolean",
                                "description": "Force deletion of protected files",
                                "default": False
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "file_server___create_terraform_resource",
                    "description": "Create a new Terraform resource definition (deprecated - use read_file and write_file for better control)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "resource_type": {
                                "type": "string",
                                "description": "Type of Terraform resource (e.g., 'aws_s3_bucket')"
                            },
                            "resource_name": {
                                "type": "string",
                                "description": "Name of the resource"
                            },
                            "attributes": {
                                "type": "object",
                                "description": "Resource attributes as key-value pairs",
                                "default": {}
                            },
                            "filename": {
                                "type": "string",
                                "description": "Terraform file to write to",
                                "default": "main.tf"
                            }
                        },
                        "required": ["resource_type", "resource_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "file_server___terraform_validate",
                    "description": "Run terraform validate and return machine-readable validation results",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "file_server___format_hcl",
                    "description": "Run 'terraform fmt' on the specified file or directory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to file or directory to format",
                                "default": "."
                            }
                        }
                    }
                }
            }
        ]
    
    def get_server_status(self) -> dict:
        """Get server status - for compatibility."""
        return {
            "fastmcp_file_server": {
                "status": "running" if self.server_process else "stopped",
                "workspace": str(self.workspace_dir) if self.workspace_dir else None
            }
        }
    
    async def shutdown(self) -> None:
        """Shutdown the FastMCP client."""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            except Exception as e:
                logger.error(f"Error shutting down server: {str(e)}")
            finally:
                self.server_process = None


# Global client instance
fastmcp_client = FastMCPClient()