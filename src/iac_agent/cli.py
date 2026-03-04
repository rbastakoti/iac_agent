"""Command line interface for the IaC Agent."""

import asyncio
import sys
import webbrowser
from pathlib import Path
from typing import Optional

import click
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from iac_agent.core.config import settings
from iac_agent.main import create_app
from iac_agent.infrastructure.binary_manager import BinaryManager


console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """IaC Agent - Local-first Jupyter-style workspace for Infrastructure as Code."""
    pass


@main.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8080, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
@click.option("--check-binaries", is_flag=True, help="Check binary dependencies on startup")
@click.option("--open-browser/--no-open-browser", default=True, help="Open browser tab automatically")
def serve(host: str, port: int, reload: bool, check_binaries: bool, open_browser: bool):
    """Start the IaC Agent server."""
    
    # Update settings
    settings.host = host
    settings.port = port
    
    # Show startup banner
    console.print(Panel.fit(
        f"[bold blue]🤖 IaC Agent v0.1.0[/bold blue]\\n"
        f"Local-first Infrastructure as Code Workspace\\n\\n"
        f"Server: http://{host}:{port}\\n"
        f"Workspace: {settings.infrastructure.workspace_directory}",
        title="Starting IaC Agent",
        border_style="blue"
    ))
    
    # Check binaries if requested
    if check_binaries:
        console.print("\\n[yellow]Checking binary dependencies...[/yellow]")
        asyncio.run(_check_binaries_async())
    
    # Open browser if requested
    if open_browser:
        server_url = f"http://{host}:{port}"
        console.print(f"\\n[green]Opening browser at {server_url}...[/green]")
        try:
            webbrowser.open(server_url)
        except Exception as e:
            console.print(f"[yellow]Could not open browser: {e}[/yellow]")
    
    # Start the server
    try:
        uvicorn.run(
            "iac_agent.main:app",
            host=host,
            port=port,
            reload=reload,
            reload_dirs=["src"] if reload else None,
            log_level="info"
        )
    except KeyboardInterrupt:
        console.print("\\n[yellow]Shutting down...[/yellow]")
        sys.exit(0)


@main.command()
def status():
    """Show IaC Agent status and configuration."""
    
    # Configuration table
    config_table = Table(title="Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")
    
    config_table.add_row("Active LLM Provider", settings.active_llm_provider)
    config_table.add_row("Workspace Directory", str(settings.infrastructure.workspace_directory))
    config_table.add_row("Max Resources", str(settings.infrastructure.max_resources))
    config_table.add_row("Binary Directory", str(settings.infrastructure.bin_directory))
    
    console.print(config_table)
    
    # Check binaries
    console.print("\\n[yellow]Checking binary dependencies...[/yellow]")
    asyncio.run(_show_binary_status())


@main.command()
def init():
    """Initialize a new IaC workspace."""
    workspace_path = settings.infrastructure.workspace_directory
    
    if workspace_path.exists() and list(workspace_path.glob("*")):
        console.print(f"[red]Workspace already exists at {workspace_path}[/red]")
        if not click.confirm("Do you want to continue?"):
            return
    
    # Create workspace directory
    workspace_path.mkdir(exist_ok=True)
    
    # Create basic terraform files
    main_tf = workspace_path / "main.tf"
    if not main_tf.exists():
        main_tf.write_text('''# IaC Agent Workspace
# This file was auto-generated

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

# Configure the Azure Provider
provider "azurerm" {
  features {}
}

# Example resource group
# resource "azurerm_resource_group" "main" {
#   name     = "rg-iac-agent"
#   location = "East US"
# }
''')
    
    # Create variables file
    variables_tf = workspace_path / "variables.tf"
    if not variables_tf.exists():
        variables_tf.write_text('''# Variables for IaC Agent workspace

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "rg-iac-agent"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "East US"
}
''')
    
    console.print(f"[green]✅ Workspace initialized at {workspace_path}[/green]")
    console.print(f"[blue]📁 Created files:[/blue]")
    console.print(f"  • main.tf")
    console.print(f"  • variables.tf")


@main.command()
@click.option("--install", is_flag=True, help="Install missing binaries")
def binaries(install: bool):
    """Check and optionally install binary dependencies."""
    
    if install:
        console.print("[yellow]Installing binary dependencies...[/yellow]")
        asyncio.run(_install_binaries_async())
    else:
        console.print("[yellow]Checking binary dependencies...[/yellow]")
        asyncio.run(_show_binary_status())


@main.command()
@click.option("--endpoint", required=True, help="API endpoint URL")
@click.option("--api-key", required=True, help="API key")
@click.option("--model", required=True, help="Model name")
@click.option("--deployment", help="Deployment name (for Azure)")
def configure(endpoint: str, api_key: str, model: str, deployment: Optional[str]):
    """Configure LLM settings."""
    
    # Update LLM configuration
    settings.update_llm_config(
        endpoint=endpoint,
        api_key=api_key,
        model_name=model,
        deployment_name=deployment
    )
    
    console.print(f"[green]✅ LLM configured successfully![/green]")
    console.print(f"Provider: {settings.active_llm_provider}")
    console.print(f"Endpoint: {endpoint}")
    console.print(f"Model: {model}")
    if deployment:
        console.print(f"Deployment: {deployment}")
    console.print("[yellow]Use 'iac-agent serve' to start the agent[/yellow]")


async def _check_binaries_async():
    """Async wrapper for binary checking."""
    binary_manager = BinaryManager()
    status = await binary_manager.check_binaries()
    
    table = Table(title="Binary Dependencies")
    table.add_column("Binary", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Version", style="yellow")
    table.add_column("Expected", style="blue")
    
    for name, info in status.items():
        status_emoji = "✅" if info["installed"] else "❌"
        status_text = "Installed" if info["installed"] else "Missing"
        version = info["version"] or "N/A"
        expected = info["expected_version"]
        
        table.add_row(name, f"{status_emoji} {status_text}", version, expected)
    
    console.print(table)


async def _show_binary_status():
    """Show binary status table."""
    await _check_binaries_async()


async def _install_binaries_async():
    """Install missing binaries."""
    binary_manager = BinaryManager()
    
    console.print("Installing dependencies...")
    results = await binary_manager.ensure_binaries()
    
    for binary, result in results.items():
        if result == "installed":
            console.print(f"[green]✅ Installed {binary}[/green]")
        elif result == "already_installed":
            console.print(f"[blue]ℹ️  {binary} already installed[/blue]")
        else:
            console.print(f"[red]❌ Failed to install {binary}: {result}[/red]")


if __name__ == "__main__":
    main()