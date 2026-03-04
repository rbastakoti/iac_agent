#!/usr/bin/env python3
"""Setup script for IaC Agent MVP."""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def print_banner():
    """Print setup banner."""
    banner = """
🤖 IaC Agent Setup
==================
Local-first Infrastructure as Code Workspace
    """
    print(banner)


def check_python_version():
    """Check Python version requirements."""
    print("📋 Checking Python version...")
    
    if sys.version_info < (3, 11):
        print("❌ Python 3.11+ is required")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def check_git():
    """Check if git is available."""
    print("📋 Checking git availability...")
    
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Git is available")
            return True
    except FileNotFoundError:
        print("❌ Git not found")
        return False


def install_dependencies():
    """Install Python dependencies."""
    print("📦 Installing Python dependencies...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-e", "."
        ], check=True)
        print("✅ Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def setup_environment():
    """Set up environment configuration."""
    print("⚙️  Setting up environment...")
    
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print("ℹ️  .env file already exists")
    elif env_example.exists():
        try:
            shutil.copy(env_example, env_file)
            print("✅ Created .env from example")
            print("⚠️  Please edit .env file to add your API keys")
        except Exception as e:
            print(f"❌ Failed to copy .env.example: {e}")
            return False
    else:
        print("⚠️  No .env.example file found")
    
    return True


def create_workspace():
    """Create initial workspace."""
    print("📁 Setting up workspace...")
    
    try:
        # Run iac-agent init command
        subprocess.run([sys.executable, "-m", "iac_agent.cli", "init"], check=True)
        print("✅ Workspace initialized")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to initialize workspace: {e}")
        return False


def run_tests():
    """Run basic tests to verify installation."""
    print("🧪 Running basic tests...")
    
    try:
        # Import main modules to check for basic errors
        import iac_agent
        from iac_agent.core.config import settings
        from iac_agent.main import create_app
        
        print("✅ Basic imports successful")
        
        # Try to create the app
        app = create_app()
        print("✅ FastAPI app creation successful")
        
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def print_next_steps():
    """Print next steps for the user."""
    next_steps = """
🎉 Setup Complete!

Next Steps:
-----------
1. Configure your LLM provider:
   iac-agent configure --provider openai --api-key YOUR_API_KEY

2. Check binary dependencies:
   iac-agent binaries --install

3. Start the server:
   iac-agent serve

4. Open your browser:
   http://localhost:8080

Documentation:
--------------
• README.md - Complete documentation
• .env file - Configure APIs and settings  
• workspace/ - Your Terraform workspace

Troubleshooting:
----------------
• Run 'iac-agent status' to check configuration
• Check logs if the server fails to start
• Ensure your API keys are correctly set in .env

Happy Infrastructure Coding! 🚀
    """
    print(next_steps)


def main():
    """Main setup function."""
    print_banner()
    
    success_steps = []
    
    # Step 1: Check Python version
    try:
        check_python_version()
        success_steps.append("python_version")
    except SystemExit:
        return 1
    
    # Step 2: Check git (optional)
    if check_git():
        success_steps.append("git")
    
    # Step 3: Install dependencies
    if install_dependencies():
        success_steps.append("dependencies")
    else:
        print("❌ Setup failed at dependency installation")
        return 1
    
    # Step 4: Setup environment
    if setup_environment():
        success_steps.append("environment")
    else:
        print("❌ Setup failed at environment configuration")
        return 1
    
    # Step 5: Create workspace
    if create_workspace():
        success_steps.append("workspace")
    else:
        print("⚠️  Workspace creation failed, but you can run 'iac-agent init' later")
    
    # Step 6: Run basic tests
    if run_tests():
        success_steps.append("tests")
    else:
        print("⚠️  Basic tests failed, but installation might still work")
    
    # Show results
    print(f"\n📊 Setup Results: {len(success_steps)} steps completed")
    for step in success_steps:
        print(f"  ✅ {step}")
    
    print_next_steps()
    return 0


if __name__ == "__main__":
    sys.exit(main())