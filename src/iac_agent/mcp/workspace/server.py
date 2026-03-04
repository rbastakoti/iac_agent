"""FastMCP-based file server - much simpler than our custom implementation."""

import json
import os
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Any
import asyncio
import sys

from fastmcp import FastMCP
from pydantic import Field

# Create FastMCP server instance
mcp = FastMCP("IaC File Server")

# Set workspace directory
WORKSPACE_DIR = None

def set_workspace_directory(workspace_path: str) -> None:
    """Set the workspace directory for file operations."""
    global WORKSPACE_DIR
    WORKSPACE_DIR = Path(workspace_path).resolve()


@mcp.tool()
def list_files(pattern: str = Field(default="*", description="File pattern to search for")) -> List[Dict[str, Any]]:
    """List files in the workspace directory matching the given pattern."""
    if WORKSPACE_DIR is None:
        raise ValueError("Workspace directory not set")
    
    import fnmatch
    files = []
    
    for file_path in WORKSPACE_DIR.rglob(pattern):
        if file_path.is_file():
            try:
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "path": str(file_path.relative_to(WORKSPACE_DIR)),
                    "full_path": str(file_path),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "type": "file"
                })
            except (OSError, PermissionError):
                # Skip files we can't access
                continue
    
    return files


@mcp.tool()
def list_directory_tree() -> List[Dict[str, Any]]:
    """List all files and directories in the workspace as a tree structure."""
    if WORKSPACE_DIR is None:
        raise ValueError("Workspace directory not set")
    
    def build_tree(path: Path, base_path: Path) -> Dict[str, Any]:
        items = []
        try:
            for item in sorted(path.iterdir()):
                if item.name.startswith('.'):
                    continue  # Skip hidden files
                    
                relative_path = str(item.relative_to(base_path))
                
                if item.is_dir():
                    items.append({
                        "name": item.name,
                        "type": "directory",
                        "path": relative_path,
                        "children": build_tree(item, base_path)
                    })
                else:
                    try:
                        stat = item.stat()
                        items.append({
                            "name": item.name,
                            "type": "file", 
                            "path": relative_path,
                            "size": stat.st_size,
                            "modified": stat.st_mtime
                        })
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            pass
        
        return items
    
    return build_tree(WORKSPACE_DIR, WORKSPACE_DIR)


@mcp.tool()
def read_file(path: str = Field(description="Path to the file to read")) -> str:
    """Read the contents of a file."""
    if WORKSPACE_DIR is None:
        raise ValueError("Workspace directory not set")
    
    file_path = Path(path)
    
    # Ensure the path is relative and within workspace
    if file_path.is_absolute():
        # Convert absolute path to relative if it's within workspace
        try:
            file_path = file_path.relative_to(WORKSPACE_DIR)
        except ValueError:
            raise ValueError("File path is outside workspace directory")
    
    full_path = WORKSPACE_DIR / file_path
    
    # Security check: ensure resolved path is still within workspace
    try:
        full_path.resolve().relative_to(WORKSPACE_DIR.resolve())
    except ValueError:
        raise ValueError("File path is outside workspace directory")
    
    if not full_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    if not full_path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Try with different encoding if UTF-8 fails
        with open(full_path, 'r', encoding='latin1') as f:
            return f.read()


@mcp.tool()
def write_file(path: str = Field(description="Path to the file to write"),
              content: str = Field(description="Content to write to the file")) -> str:
    """Write content to a file."""
    if WORKSPACE_DIR is None:
        raise ValueError("Workspace directory not set")
    
    file_path = Path(path)
    
    # Ensure the path is relative and within workspace
    if file_path.is_absolute():
        try:
            file_path = file_path.relative_to(WORKSPACE_DIR)
        except ValueError:
            raise ValueError("File path is outside workspace directory")
    
    full_path = WORKSPACE_DIR / file_path
    
    # Security check: ensure resolved path is still within workspace
    try:
        full_path.resolve().relative_to(WORKSPACE_DIR.resolve())
    except ValueError:
        raise ValueError("File path is outside workspace directory")
    
    # Create directory if it doesn't exist
    full_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        raise Exception(f"Failed to write file: {str(e)}")


@mcp.tool()
def delete_file(path: str = Field(description="Path to the file to delete"),
               force: bool = Field(default=False, description="Force deletion of protected files")) -> str:
    """Delete a file with safety checks for important terraform files."""
    if WORKSPACE_DIR is None:
        raise ValueError("Workspace directory not set")
    
    file_path = Path(path)
    
    # Ensure the path is relative and within workspace
    if file_path.is_absolute():
        try:
            file_path = file_path.relative_to(WORKSPACE_DIR)
        except ValueError:
            raise ValueError("File path is outside workspace directory")
    
    full_path = WORKSPACE_DIR / file_path
    
    # Security check
    try:
        full_path.resolve().relative_to(WORKSPACE_DIR.resolve())
    except ValueError:
        raise ValueError("File path is outside workspace directory")
    
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
    
    if not full_path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    
    try:
        full_path.unlink()
        return f"Successfully deleted {path}"
    except Exception as e:
        raise Exception(f"Failed to delete file: {str(e)}")


@mcp.tool()
def create_terraform_resource(
    resource_type: str = Field(description="Type of Terraform resource (e.g., 'aws_s3_bucket')"),
    resource_name: str = Field(description="Name of the resource"),
    attributes: Dict[str, Any] = Field(default={}, description="Resource attributes as key-value pairs"),
    filename: str = Field(default="main.tf", description="Terraform file to write to")
) -> str:
    """Create a new Terraform resource definition using read-modify-write approach."""
    if WORKSPACE_DIR is None:
        raise ValueError("Workspace directory not set")
    
    file_path = Path(filename)
    if file_path.is_absolute():
        try:
            file_path = file_path.relative_to(WORKSPACE_DIR)
        except ValueError:
            raise ValueError("File path is outside workspace directory")
    
    full_path = WORKSPACE_DIR / file_path
    
    # Generate new Terraform resource block
    terraform_content = f'\nresource "{resource_type}" "{resource_name}" {{\n'
    
    for key, value in attributes.items():
        if isinstance(value, str):
            terraform_content += f'  {key} = "{value}"\n'
        elif isinstance(value, bool):
            terraform_content += f'  {key} = {str(value).lower()}\n'
        elif isinstance(value, (int, float)):
            terraform_content += f'  {key} = {value}\n'
        elif isinstance(value, list):
            terraform_content += f'  {key} = {json.dumps(value)}\n'
        elif isinstance(value, dict):
            terraform_content += f'  {key} = {json.dumps(value)}\n'
    
    terraform_content += '}\n'
    
    # Read existing content if file exists
    existing_content = ""
    if full_path.exists():
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
        except Exception as e:
            raise Exception(f"Failed to read existing file: {str(e)}")
    
    # Check if resource already exists
    resource_pattern = rf'resource\s+"{re.escape(resource_type)}"\s+"{re.escape(resource_name)}"\s*{{'
    if re.search(resource_pattern, existing_content):
        raise ValueError(f"Resource {resource_type}.{resource_name} already exists in {filename}. Use read_file and write_file to modify existing resources.")
    
    # Write combined content
    final_content = existing_content.rstrip() + terraform_content
    
    try:
        # Create directory if it doesn't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        return f"Successfully added {resource_type}.{resource_name} to {filename}"
    except Exception as e:
        raise Exception(f"Failed to create Terraform resource: {str(e)}")


@mcp.tool()
def terraform_validate() -> str:
    """Run terraform validate and return machine-readable validation results."""
    if WORKSPACE_DIR is None:
        raise ValueError("Workspace directory not set")
    
    try:
        # Run terraform validate with JSON output
        result = subprocess.run(
            ["terraform", "validate", "-json"],
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Return both stdout and stderr with exit code
        validation_result = {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "valid": result.returncode == 0
        }
        
        return json.dumps(validation_result, indent=2)
        
    except subprocess.TimeoutExpired:
        raise Exception("Terraform validate timed out after 30 seconds")
    except FileNotFoundError:
        raise Exception("Terraform command not found. Please ensure terraform is installed and in PATH.")
    except Exception as e:
        raise Exception(f"Failed to run terraform validate: {str(e)}")


@mcp.tool()
def format_hcl(path: str = Field(default=".", description="Path to file or directory to format")) -> str:
    """Run 'terraform fmt' on the specified file or directory."""
    if WORKSPACE_DIR is None:
        raise ValueError("Workspace directory not set")
    
    file_path = Path(path)
    
    # Handle relative paths
    if not file_path.is_absolute():
        full_path = WORKSPACE_DIR / file_path
    else:
        try:
            file_path.relative_to(WORKSPACE_DIR)
            full_path = file_path
        except ValueError:
            raise ValueError("File path is outside workspace directory")
    
    # Security check
    try:
        full_path.resolve().relative_to(WORKSPACE_DIR.resolve())
    except ValueError:
        raise ValueError("File path is outside workspace directory")
    
    try:
        # Run terraform fmt
        result = subprocess.run(
            ["terraform", "fmt", str(full_path)],
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            formatted_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            if formatted_files and formatted_files[0]:
                return f"Formatted {len(formatted_files)} files: {', '.join(formatted_files)}"
            else:
                return f"No formatting changes needed for {path}"
        else:
            raise Exception(f"terraform fmt failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        raise Exception("Terraform fmt timed out after 30 seconds")
    except FileNotFoundError:
        raise Exception("Terraform command not found. Please ensure terraform is installed and in PATH.")
    except Exception as e:
        raise Exception(f"Failed to format HCL: {str(e)}")


def main():
    """Run the FastMCP server."""
    if len(sys.argv) > 1:
        workspace_path = sys.argv[1]
        set_workspace_directory(workspace_path)
        print(f"Workspace set to: {WORKSPACE_DIR}", file=sys.stderr)
    
    # Run the FastMCP server
    mcp.run()


if __name__ == "__main__":
    main()