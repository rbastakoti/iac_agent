"""Core utilities and helpers for IaC Agent."""

import hashlib
import secrets
import re
from typing import List, Dict, Any
from pathlib import Path


class CredentialScrubber:
    """Utility for scrubbing credentials from text."""
    
    def __init__(self):
        self.patterns = [
            # Common password patterns
            r'password\s*[=:]\s*["\']([^"\']+)["\']',
            r'secret\s*[=:]\s*["\']([^"\']+)["\']',
            r'api_key\s*[=:]\s*["\']([^"\']+)["\']',
            r'token\s*[=:]\s*["\']([^"\']+)["\']',
            r'access_key\s*[=:]\s*["\']([^"\']+)["\']',
            r'private_key\s*[=:]\s*["\']([^"\']+)["\']',
            
            # Azure specific
            r'client_secret\s*[=:]\s*["\']([^"\']+)["\']',
            r'subscription_id\s*[=:]\s*["\']([^"\']+)["\']',
            
            # AWS specific
            r'aws_access_key_id\s*[=:]\s*["\']([^"\']+)["\']',
            r'aws_secret_access_key\s*[=:]\s*["\']([^"\']+)["\']',
            
            # Generic patterns
            r'[A-Za-z0-9_-]{40,}',  # Long strings that might be keys
        ]
    
    def scrub_text(self, text: str) -> str:
        """Scrub credentials from text."""
        scrubbed = text
        
        for pattern in self.patterns:
            scrubbed = re.sub(pattern, lambda m: self._replace_with_mask(m.group(0)), scrubbed, flags=re.IGNORECASE)
        
        return scrubbed
    
    def _replace_with_mask(self, match: str) -> str:
        """Replace matched credential with masked version."""
        if len(match) <= 8:
            return "*" * len(match)
        return match[:4] + "*" * (len(match) - 8) + match[-4:]
    
    def scrub_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively scrub credentials from a dictionary."""
        scrubbed = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                scrubbed[key] = self.scrub_text(value)
            elif isinstance(value, dict):
                scrubbed[key] = self.scrub_dict(value)
            elif isinstance(value, list):
                scrubbed[key] = [
                    self.scrub_text(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                scrubbed[key] = value
        
        return scrubbed


def generate_session_id() -> str:
    """Generate a secure session ID."""
    return secrets.token_urlsafe(32)


def generate_secret_key() -> str:
    """Generate a secure secret key."""
    return secrets.token_urlsafe(32)


def hash_file_content(file_path: Path) -> str:
    """Generate SHA256 hash of file content."""
    if not file_path.exists():
        return ""
    
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    
    return sha256_hash.hexdigest()


def validate_terraform_file(file_path: Path) -> bool:
    """Basic validation of Terraform file."""
    if not file_path.exists() or not file_path.suffix in ['.tf', '.tfvars']:
        return False
    
    try:
        content = file_path.read_text()
        # Basic syntax check - look for common Terraform constructs
        has_terraform_syntax = any(keyword in content for keyword in [
            'resource ', 'variable ', 'data ', 'output ', 'terraform ', 'provider '
        ])
        return has_terraform_syntax
    except Exception:
        return False


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def extract_terraform_resources(state_content: str) -> List[Dict[str, Any]]:
    """Extract resource information from Terraform state."""
    try:
        import json
        state_data = json.loads(state_content)
        
        resources = []
        for resource in state_data.get("resources", []):
            resources.append({
                "type": resource.get("type"),
                "name": resource.get("name"),
                "provider": resource.get("provider"),
                "instances": len(resource.get("instances", [])),
                "mode": resource.get("mode", "managed")
            })
        
        return resources
    except Exception:
        return []


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations."""
    # Remove harmful characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')
    # Limit length
    return sanitized[:255]