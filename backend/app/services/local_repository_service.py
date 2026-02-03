"""
Local Repository Service
Handles local file system operations for repositories
Used when running in LOCAL_MODE
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.utils.logger import logger


class LocalRepositoryService:
    """Service for local file system repository operations"""
    
    def __init__(self):
        self.workspace_path = Path(settings.LOCAL_WORKSPACE_PATH) if settings.LOCAL_WORKSPACE_PATH else None
        
    def get_workspace_path(self) -> Path:
        """Get the base workspace path for local repositories"""
        if not self.workspace_path:
            raise ValueError("LOCAL_WORKSPACE_PATH not configured in settings")
        
        if not self.workspace_path.exists():
            self.workspace_path.mkdir(parents=True, exist_ok=True)
            
        return self.workspace_path
    
    def list_local_repositories(self) -> List[Dict[str, Any]]:
        """
        List all directories in the workspace that contain pom.xml (Java Maven projects)
        Returns list of repository information
        """
        workspace = self.get_workspace_path()
        repositories = []
        
        for item in workspace.iterdir():
            if item.is_dir():
                pom_file = item / "pom.xml"
                if pom_file.exists():
                    # Get git info if it's a git repository
                    git_info = self._get_git_info(item)
                    
                    repositories.append({
                        "name": item.name,
                        "path": str(item),
                        "has_pom": True,
                        "is_git": git_info is not None,
                        "git_info": git_info
                    })
        
        return repositories
    
    def _get_git_info(self, repo_path: Path) -> Optional[Dict[str, str]]:
        """Get git information from a local repository"""
        git_dir = repo_path / ".git"
        if not git_dir.exists():
            return None
        
        try:
            # Get current branch
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_path,
                text=True
            ).strip()
            
            # Get latest commit hash
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                text=True
            ).strip()
            
            # Get remote URL if exists
            try:
                remote_url = subprocess.check_output(
                    ["git", "config", "--get", "remote.origin.url"],
                    cwd=repo_path,
                    text=True
                ).strip()
            except subprocess.CalledProcessError:
                remote_url = None
            
            return {
                "branch": branch,
                "commit": commit,
                "remote_url": remote_url
            }
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to get git info for {repo_path}: {e}")
            return None
    
    def clone_repository(self, git_url: str, target_name: Optional[str] = None) -> Path:
        """
        Clone a repository from GitHub to the local workspace
        
        Args:
            git_url: GitHub repository URL (e.g., https://github.com/owner/repo.git)
            target_name: Optional custom directory name (defaults to repo name from URL)
        
        Returns:
            Path to the cloned repository
        """
        workspace = self.get_workspace_path()
        
        # Extract repo name from URL if target_name not provided
        if not target_name:
            target_name = git_url.rstrip('/').split('/')[-1].replace('.git', '')
        
        target_path = workspace / target_name
        
        # Check if already exists
        if target_path.exists():
            logger.info(f"Repository already exists at {target_path}, pulling latest changes")
            try:
                subprocess.run(
                    ["git", "pull"],
                    cwd=target_path,
                    check=True,
                    capture_output=True,
                    text=True
                )
                return target_path
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to pull updates: {e.stderr}")
                return target_path
        
        # Clone the repository
        logger.info(f"Cloning {git_url} to {target_path}")
        try:
            subprocess.run(
                ["git", "clone", git_url, str(target_path)],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Successfully cloned to {target_path}")
            return target_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone repository: {e.stderr}")
            raise RuntimeError(f"Failed to clone repository: {e.stderr}")
    
    def read_file(self, repo_name: str, file_path: str) -> Optional[str]:
        """
        Read file content from a local repository
        
        Args:
            repo_name: Name of the repository directory
            file_path: Relative path to the file within the repository
        
        Returns:
            File content as string or None if not found
        """
        workspace = self.get_workspace_path()
        full_path = workspace / repo_name / file_path
        
        if not full_path.exists():
            logger.warning(f"File not found: {full_path}")
            return None
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {full_path}: {e}")
            return None
    
    def write_file(self, repo_name: str, file_path: str, content: str) -> bool:
        """
        Write content to a file in a local repository
        
        Args:
            repo_name: Name of the repository directory
            file_path: Relative path to the file within the repository
            content: Content to write
        
        Returns:
            True if successful, False otherwise
        """
        workspace = self.get_workspace_path()
        full_path = workspace / repo_name / file_path
        
        try:
            # Create parent directories if they don't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Successfully wrote to {full_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing file {full_path}: {e}")
            return False
    
    def get_repository_path(self, repo_name: str) -> Optional[Path]:
        """Get the full path to a repository"""
        workspace = self.get_workspace_path()
        repo_path = workspace / repo_name
        
        if repo_path.exists() and repo_path.is_dir():
            return repo_path
        
        return None
    
    def check_pom_exists(self, repo_name: str) -> bool:
        """Check if pom.xml exists in a repository"""
        repo_path = self.get_repository_path(repo_name)
        if not repo_path:
            return False
        
        return (repo_path / "pom.xml").exists()


# Global instance
local_repo_service = LocalRepositoryService()
