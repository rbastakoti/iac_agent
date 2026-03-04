"""Binary dependency manager for cross-platform tool installation."""

import asyncio
import platform
import hashlib
import zipfile
import tarfile
from typing import Dict, Optional, Tuple
from pathlib import Path
import httpx

from iac_agent.core.config import settings


class BinaryInfo:
    """Information about a binary dependency."""
    
    def __init__(self, name: str, version: str, download_urls: dict, 
                 checksums: dict, executable_name: str):
        self.name = name
        self.version = version
        self.download_urls = download_urls  # {platform: url}
        self.checksums = checksums  # {platform: sha256}
        self.executable_name = executable_name


class BinaryManager:
    """Manages installation and verification of required binaries."""
    
    def __init__(self):
        self.bin_directory = settings.infrastructure.bin_directory
        self.bin_directory.mkdir(exist_ok=True)
        
        # Detect platform first
        self.platform = self._detect_platform()
        
        # Define binary specifications (needs platform info)
        self.binaries = self._get_binary_specs()
    
    def _detect_platform(self) -> str:
        """Detect the current platform."""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        if system == "windows":
            return "windows_amd64"
        elif system == "darwin":
            if "arm" in machine or "arm64" in machine:
                return "darwin_arm64" 
            return "darwin_amd64"
        elif system == "linux":
            if "arm" in machine or "aarch64" in machine:
                return "linux_arm64"
            return "linux_amd64"
        
        raise RuntimeError(f"Unsupported platform: {system} {machine}")
    
    def _get_binary_specs(self) -> Dict[str, BinaryInfo]:
        """Get specifications for all required binaries."""
        terraform_version = settings.infrastructure.terraform_version
        
        return {
            "terraform": BinaryInfo(
                name="terraform",
                version=terraform_version,
                download_urls={
                    "windows_amd64": f"https://releases.hashicorp.com/terraform/{terraform_version}/terraform_{terraform_version}_windows_amd64.zip",
                    "darwin_amd64": f"https://releases.hashicorp.com/terraform/{terraform_version}/terraform_{terraform_version}_darwin_amd64.zip",
                    "darwin_arm64": f"https://releases.hashicorp.com/terraform/{terraform_version}/terraform_{terraform_version}_darwin_arm64.zip",
                    "linux_amd64": f"https://releases.hashicorp.com/terraform/{terraform_version}/terraform_{terraform_version}_linux_amd64.zip",
                    "linux_arm64": f"https://releases.hashicorp.com/terraform/{terraform_version}/terraform_{terraform_version}_linux_arm64.zip",
                },
                checksums={
                    # These would be real checksums in production
                    "windows_amd64": "mock_checksum_windows",
                    "darwin_amd64": "mock_checksum_darwin",
                    "darwin_arm64": "mock_checksum_darwin_arm",
                    "linux_amd64": "mock_checksum_linux",
                    "linux_arm64": "mock_checksum_linux_arm",
                },
                executable_name="terraform.exe" if self.platform.startswith("windows") else "terraform"
            ),
            
            "az": BinaryInfo(
                name="az",
                version=settings.infrastructure.az_cli_version,
                download_urls={
                    # Azure CLI has different installation methods per platform
                    "windows_amd64": "https://aka.ms/installazurecliwindows",
                    "darwin_amd64": "https://aka.ms/installazureclimacos",
                    "darwin_arm64": "https://aka.ms/installazureclimacos", 
                    "linux_amd64": "https://aka.ms/InstallAzureCLIDeb",
                    "linux_arm64": "https://aka.ms/InstallAzureCLIDeb",
                },
                checksums={
                    # Azure CLI uses package managers, checksums handled differently
                    "windows_amd64": "package_manager",
                    "darwin_amd64": "package_manager",
                    "darwin_arm64": "package_manager",
                    "linux_amd64": "package_manager", 
                    "linux_arm64": "package_manager",
                },
                executable_name="az.cmd" if self.platform.startswith("windows") else "az"
            ),
            
            "aztfexport": BinaryInfo(
                name="aztfexport",
                version=settings.infrastructure.aztfexport_version,
                download_urls={
                    "windows_amd64": f"https://github.com/Azure/aztfexport/releases/download/v{settings.infrastructure.aztfexport_version}/aztfexport_v{settings.infrastructure.aztfexport_version}_windows_amd64.zip",
                    "darwin_amd64": f"https://github.com/Azure/aztfexport/releases/download/v{settings.infrastructure.aztfexport_version}/aztfexport_v{settings.infrastructure.aztfexport_version}_darwin_amd64.tar.gz",
                    "darwin_arm64": f"https://github.com/Azure/aztfexport/releases/download/v{settings.infrastructure.aztfexport_version}/aztfexport_v{settings.infrastructure.aztfexport_version}_darwin_arm64.tar.gz",
                    "linux_amd64": f"https://github.com/Azure/aztfexport/releases/download/v{settings.infrastructure.aztfexport_version}/aztfexport_v{settings.infrastructure.aztfexport_version}_linux_amd64.tar.gz",
                    "linux_arm64": f"https://github.com/Azure/aztfexport/releases/download/v{settings.infrastructure.aztfexport_version}/aztfexport_v{settings.infrastructure.aztfexport_version}_linux_arm64.tar.gz",
                },
                checksums={
                    # These would be real checksums in production
                    "windows_amd64": "mock_checksum_aztfexport_windows",
                    "darwin_amd64": "mock_checksum_aztfexport_darwin",
                    "darwin_arm64": "mock_checksum_aztfexport_darwin_arm",
                    "linux_amd64": "mock_checksum_aztfexport_linux",
                    "linux_arm64": "mock_checksum_aztfexport_linux_arm",
                },
                executable_name="aztfexport.exe" if self.platform.startswith("windows") else "aztfexport"
            )
        }
    
    async def check_binaries(self) -> Dict[str, dict]:
        """Check status of all required binaries."""
        status = {}
        
        for name, binary_info in self.binaries.items():
            binary_path = self.bin_directory / binary_info.executable_name
            
            installed = binary_path.exists()
            version = None
            
            if installed:
                version = await self._get_binary_version(binary_path, name)
            
            status[name] = {
                "installed": installed,
                "version": version,
                "expected_version": binary_info.version,
                "path": str(binary_path),
                "needs_update": version != binary_info.version if version else False
            }
        
        return status
    
    async def _get_binary_version(self, binary_path: Path, binary_name: str) -> Optional[str]:
        """Get version of an installed binary."""
        try:
            if binary_name == "terraform":
                proc = await asyncio.create_subprocess_exec(
                    str(binary_path), "version", "-json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await proc.communicate()
                if proc.returncode == 0:
                    import json
                    version_data = json.loads(stdout.decode())
                    return version_data.get("terraform_version", "unknown")
            
            elif binary_name == "az":
                proc = await asyncio.create_subprocess_exec(
                    str(binary_path), "version", "--output", "json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await proc.communicate()
                if proc.returncode == 0:
                    import json
                    version_data = json.loads(stdout.decode())
                    return version_data.get("azure-cli", "unknown")
            
            elif binary_name == "aztfexport":
                proc = await asyncio.create_subprocess_exec(
                    str(binary_path), "version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await proc.communicate()
                if proc.returncode == 0:
                    return stdout.decode().strip()
        
        except Exception:
            pass
        
        return None
    
    async def ensure_binaries(self) -> Dict[str, str]:
        """Ensure all required binaries are installed."""
        status = await self.check_binaries()
        results = {}
        
        for name, info in status.items():
            if not info["installed"] or info["needs_update"]:
                try:
                    await self.install_binary(name)
                    results[name] = "installed"
                except Exception as e:
                    results[name] = f"failed: {str(e)}"
            else:
                results[name] = "already_installed"
        
        return results
    
    async def install_binary(self, binary_name: str) -> bool:
        """Install a specific binary."""
        if binary_name not in self.binaries:
            raise ValueError(f"Unknown binary: {binary_name}")
        
        binary_info = self.binaries[binary_name]
        
        # Special handling for Azure CLI (uses package managers)
        if binary_name == "az":
            return await self._install_azure_cli()
        
        # Download and install other binaries
        return await self._download_and_install(binary_info)
    
    async def _install_azure_cli(self) -> bool:
        """Install Azure CLI using platform-specific methods."""
        # For MVP, we'll provide instructions rather than automatic installation
        # In production, this would use platform-specific package managers
        print("Azure CLI installation required. Please install manually:")
        if self.platform.startswith("windows"):
            print("Run: winget install -e --id Microsoft.AzureCLI")
        elif self.platform.startswith("darwin"):
            print("Run: brew install azure-cli")
        else:
            print("Run: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash")
        
        return False  # For MVP, require manual installation
    
    async def _download_and_install(self, binary_info: BinaryInfo) -> bool:
        """Download and install a binary."""
        if self.platform not in binary_info.download_urls:
            raise RuntimeError(f"No download URL for platform: {self.platform}")
        
        download_url = binary_info.download_urls[self.platform]
        expected_checksum = binary_info.checksums[self.platform]
        
        # Download the binary
        download_path = self.bin_directory / f"{binary_info.name}_download"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(download_url)
            response.raise_for_status()
            
            with open(download_path, "wb") as f:
                f.write(response.content)
        
        # Verify checksum (skip for MVP since we're using mock checksums)
        # In production, this would verify the actual SHA256 checksum
        
        # Extract if needed
        if download_url.endswith('.zip'):
            await self._extract_zip(download_path, binary_info)
        elif download_url.endswith('.tar.gz'):
            await self._extract_tar(download_path, binary_info)
        else:
            # Direct binary, just rename
            final_path = self.bin_directory / binary_info.executable_name
            download_path.rename(final_path)
            final_path.chmod(0o755)  # Make executable on Unix
        
        # Clean up download
        if download_path.exists():
            download_path.unlink()
        
        return True
    
    async def _extract_zip(self, archive_path: Path, binary_info: BinaryInfo) -> None:
        """Extract ZIP archive."""
        final_path = self.bin_directory / binary_info.executable_name
        
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            # Extract the binary
            for member in zip_ref.namelist():
                if member.endswith(binary_info.executable_name.replace('.exe', '')):
                    with zip_ref.open(member) as source, open(final_path, 'wb') as target:
                        target.write(source.read())
                    break
        
        if not self.platform.startswith("windows"):
            final_path.chmod(0o755)  # Make executable on Unix
    
    async def _extract_tar(self, archive_path: Path, binary_info: BinaryInfo) -> None:
        """Extract TAR archive."""
        final_path = self.bin_directory / binary_info.executable_name
        
        with tarfile.open(archive_path, 'r:gz') as tar_ref:
            # Extract the binary
            for member in tar_ref.getmembers():
                if member.name.endswith(binary_info.executable_name):
                    with tar_ref.extractfile(member) as source, open(final_path, 'wb') as target:
                        target.write(source.read())
                    break
        
        final_path.chmod(0o755)  # Make executable on Unix
    
    def get_binary_path(self, binary_name: str) -> Optional[Path]:
        """Get path to installed binary."""
        if binary_name not in self.binaries:
            return None

        binary_info = self.binaries[binary_name]
        binary_path = self.bin_directory / binary_info.executable_name
        
        return binary_path if binary_path.exists() else None
    
    async def execute_terraform_command(self, command: str, workspace_path: Path, 
                                      stream_callback=None) -> Dict[str, any]:
        """Execute a terraform command with streaming output."""
        terraform_path = self.get_binary_path("terraform")
        if not terraform_path:
            raise RuntimeError("Terraform binary not found. Please install terraform.")
        
        # Parse command into arguments
        cmd_args = command.split()
        if cmd_args[0] != "terraform":
            cmd_args.insert(0, "terraform")
        cmd_args[0] = str(terraform_path)
        
        # Change to workspace directory
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(workspace_path)
            
            # Execute command with streaming
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_path
            )
            
            stdout_lines = []
            stderr_lines = []
            
            # Stream output
            async def read_stream(stream, lines_list, stream_type):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    line_text = line.decode().rstrip()
                    lines_list.append(line_text)
                    
                    # Call stream callback if provided
                    if stream_callback:
                        await stream_callback(stream_type, line_text)
            
            # Read both streams concurrently
            await asyncio.gather(
                read_stream(process.stdout, stdout_lines, "stdout"),
                read_stream(process.stderr, stderr_lines, "stderr")
            )
            
            # Wait for process completion
            return_code = await process.wait()
            
            return {
                "return_code": return_code,
                "stdout": "\n".join(stdout_lines),
                "stderr": "\n".join(stderr_lines),
                "success": return_code == 0,
                "command": " ".join(cmd_args)
            }
            
        except Exception as e:
            return {
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False,
                "command": " ".join(cmd_args),
                "error": str(e)
            }
        finally:
            # Restore original directory
            os.chdir(original_cwd)
    
    async def terraform_init(self, workspace_path: Path, stream_callback=None) -> Dict[str, any]:
        """Initialize terraform workspace."""
        return await self.execute_terraform_command("terraform init", workspace_path, stream_callback)
    
    async def terraform_plan(self, workspace_path: Path, stream_callback=None, 
                           out_file: str = None) -> Dict[str, any]:
        """Generate terraform plan."""
        command = "terraform plan -no-color -detailed-exitcode"
        if out_file:
            command += f" -out={out_file}"
        return await self.execute_terraform_command(command, workspace_path, stream_callback)
    
    async def terraform_apply(self, workspace_path: Path, plan_file: str = None, 
                            stream_callback=None) -> Dict[str, any]:
        """Apply terraform changes."""
        command = "terraform apply -no-color -auto-approve"
        if plan_file:
            command += f" {plan_file}"
        return await self.execute_terraform_command(command, workspace_path, stream_callback)