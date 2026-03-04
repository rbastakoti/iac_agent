"""Core configuration for the IaC Agent."""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class LLMConfig(BaseModel):
    """Simple LLM configuration."""
    endpoint: str = "https://api.openai.com/v1"
    api_key: str = ""
    model_name: str = ""
    deployment_name: Optional[str] = None  # For Azure deployments
    max_tokens: int = 4096
    temperature: float = 0.1


class DatabaseConfig(BaseModel):
    """Database configuration."""
    url: str = "sqlite:///./workspace.db"
    echo: bool = False


class SecurityConfig(BaseModel):
    """Security configuration."""
    secret_key: str = Field(default_factory=lambda: "dev-secret-key-change-in-production")
    encryption_key: Optional[str] = None
    credential_patterns: list[str] = Field(default_factory=lambda: [
        r'password\s*=\s*["\']([^"\']+)["\']',
        r'secret\s*=\s*["\']([^"\']+)["\']',
        r'api_key\s*=\s*["\']([^"\']+)["\']',
        r'token\s*=\s*["\']([^"\']+)["\']',
    ])


class InfrastructureConfig(BaseModel):
    """Infrastructure and binary configuration."""
    bin_directory: Path = Path("./bin")
    terraform_version: str = "1.6.0"
    az_cli_version: str = "2.55.0"
    aztfexport_version: str = "0.13.0"
    max_resources: int = 100
    workspace_directory: Path = Path("./workspace")


class Settings(BaseSettings):
    """Main application settings."""
    
    # Application
    app_name: str = "IaC Agent"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8080
    
    # LLM Provider tracking
    active_llm_provider: str = "Not Configured"
    
    # Database
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    
    # Security
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    # Infrastructure
    infrastructure: InfrastructureConfig = Field(default_factory=InfrastructureConfig)
    
    
    # LLM Configuration - Simple and straightforward
    llm: LLMConfig = Field(default_factory=LLMConfig)
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
        
        
    def is_llm_configured(self) -> bool:
        """Check if LLM is properly configured."""
        return bool(self.llm.api_key and self.llm.endpoint and self.llm.model_name)
    
    def update_llm_config(self, endpoint: str, api_key: str, model_name: str, deployment_name: str = None):
        """Update LLM configuration."""
        self.llm.endpoint = endpoint
        self.llm.api_key = api_key
        self.llm.model_name = model_name
        self.llm.deployment_name = deployment_name
        
        # Auto-determine and set active provider
        if "openai.com" in endpoint.lower():
            self.active_llm_provider = "OpenAI"
        elif "ai.azure.com" in endpoint.lower():
            self.active_llm_provider = "Azure OpenAI"
        elif "anthropic.com" in endpoint.lower():
            self.active_llm_provider = "Anthropic"
        elif "googleapis.com" in endpoint.lower():
            self.active_llm_provider = "Google"
        else:
            self.active_llm_provider = "Custom"

    def save_credentials_to_env(self):
        """Save current LLM credentials to .env file for persistence."""
        env_file = Path(".env")
        
        # Read existing .env content
        env_content = {}
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_content[key.strip()] = value.strip()
        
        # Update with current LLM config
        env_content['LLM__ENDPOINT'] = self.llm.endpoint
        env_content['LLM__API_KEY'] = self.llm.api_key
        env_content['LLM__MODEL_NAME'] = self.llm.model_name
        if self.llm.deployment_name:
            env_content['LLM__DEPLOYMENT_NAME'] = self.llm.deployment_name
        
        # Write back to .env file
        with open(env_file, 'w') as f:
            f.write("# IaC Agent Environment Configuration\n")
            f.write("# Auto-generated credentials - DO NOT COMMIT TO VERSION CONTROL\n\n")
            
            # Write LLM config section
            f.write("# =================================\n")
            f.write("# LLM Configuration (Auto-saved)\n")
            f.write("# =================================\n")
            for key, value in env_content.items():
                if key.startswith('LLM__'):
                    f.write(f"{key}={value}\n")
            
            f.write("\n# =================================\n")
            f.write("# Application Settings\n")
            f.write("# =================================\n")
            
            # Write other settings
            for key, value in env_content.items():
                if not key.startswith('LLM__'):
                    f.write(f"{key}={value}\n")
        
        print(f"✅ LLM credentials saved to {env_file.absolute()}")
        
    def load_credentials_from_env(self):
        """Load LLM credentials from .env file if available."""
        env_file = Path(".env")
        if not env_file.exists():
            return False
            
        # Read environment variables with the nested delimiter
        import os
        from dotenv import load_dotenv
        load_dotenv(env_file)
        
        # Check if LLM credentials are available
        endpoint = os.getenv('LLM__ENDPOINT')
        api_key = os.getenv('LLM__API_KEY') 
        model_name = os.getenv('LLM__MODEL_NAME')
        deployment_name = os.getenv('LLM__DEPLOYMENT_NAME')
        
        if endpoint and api_key and model_name:
            self.llm.endpoint = endpoint
            self.llm.api_key = api_key
            self.llm.model_name = model_name
            if deployment_name:
                self.llm.deployment_name = deployment_name
            print(f"✅ Auto-loaded LLM credentials from {env_file.absolute()}")
            return True
        
        return False


# Global settings instance
settings = Settings()