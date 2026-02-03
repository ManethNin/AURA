"""
GitHub Service
Handles GitHub API interactions
"""

# TODO: Implement GitHub service
# - Verify webhook signatures
# - Fetch repository content
# - Create pull requests
# - Get user repositories
# - Manage GitHub App installation


"""
GitHub Service - Handles GitHub API interactions
"""
import hmac
import hashlib
import base64
import re
from typing import Optional, Dict, Any, List, Tuple
import httpx
from app.core.config import settings
from app.repositories.change_repository import change_repo
from app.utils.logger import logger


class GitHubService:
    """Service for GitHub API operations"""
    
    def __init__(self):
        # Only initialize if not in local mode
        if not settings.LOCAL_MODE:
            self.webhook_secret = settings.GITHUB_WEBHOOK_SECRET
            self.app_id = settings.GITHUB_APP_ID
        else:
            self.webhook_secret = None
            self.app_id = None
    
    def verify_webhook_signature(self, payload_body: bytes, signature_header: str) -> bool:
        """
        Verify GitHub webhook signature for security
        CRITICAL: Always verify webhooks in production!
        """
        if settings.LOCAL_MODE:
            logger.warning("Webhook signature verification skipped in LOCAL_MODE")
            return True
            
        if not signature_header or not self.webhook_secret:
            return False
        
        # GitHub sends signature as 'sha256=...'
        hash_algorithm, github_signature = signature_header.split('=')
        
        # Calculate expected signature
        mac = hmac.new(
            self.webhook_secret.encode(),
            msg=payload_body,
            digestmod=hashlib.sha256
        )
        expected_signature = mac.hexdigest()
        
        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_signature, github_signature)
    
    async def get_file_content(
        self, 
        owner: str, 
        repo: str, 
        path: str, 
        ref: str = "main"
    ) -> Optional[str]:
        """
        Get file content from GitHub repository
        Used to fetch pom.xml content
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                params={"ref": ref},
                headers={
                    "Accept": "application/vnd.github.v3.raw",  # Get raw content
                    "Authorization": f"Bearer {settings.GITHUB_APP_ID}"  # Or use installation token
                }
            )
            
            if response.status_code == 200:
                return response.text
            return None
    
    async def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Get GitHub user information"""
        url = f"https://api.github.com/users/{username}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                return response.json()
            return None
    
    async def get_repo_info(self, owner: str, repo: str, access_token: str = None) -> Optional[Dict[str, Any]]:
        """Get GitHub repository information"""
        url = f"https://api.github.com/repos/{owner}/{repo}"
        
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            return None
    
    async def get_default_branch(self, owner: str, repo: str, access_token: str = None) -> str:
        """Get the default branch of a repository (e.g., 'main' or 'master')"""
        repo_info = await self.get_repo_info(owner, repo, access_token)
        
        if repo_info and "default_branch" in repo_info:
            return repo_info["default_branch"]
        
        # Fallback: Try 'main' first, then 'master'
        logger.warning(f"Could not determine default branch for {owner}/{repo}, trying 'main'")
        return "main"
    
    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
        access_token: str = None,
        installation_id: int = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a pull request on GitHub
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        elif installation_id:
            return None
        else:
            return None
        
        payload = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 201:
                return response.json()
            else:
                logger.error(f"Failed to create PR: {response.status_code} - {response.text}")
                return None
    
    async def create_branch(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        base_sha: str,
        access_token: str
    ) -> bool:
        """Create a new branch in the repository"""
        url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "ref": f"refs/heads/{branch_name}",
            "sha": base_sha
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            logger.info(f"Branch creation response: {response.status_code}")
            logger.info(f"Response body: {response.text}")
            
            if response.status_code == 201:
                return True
            elif response.status_code == 422:
                # Branch might already exist
                logger.warning(f"Branch {branch_name} might already exist: {response.text}")
                return True  # Consider it success if branch exists
            else:
                logger.error(f"Failed to create branch: {response.status_code} - {response.text}")
                return False
        
    async def get_branch_head_sha(
        self,
        owner: str,
        repo: str,
        branch: str,
        access_token: str
    ) -> Optional[str]:
        """Get the HEAD SHA of a branch"""
        url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {access_token}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["object"]["sha"]
            else:
                logger.error(f"Failed to get branch HEAD: {response.status_code} - {response.text}")
                return None
    
    async def get_file_sha(
        self,
        owner: str,
        repo: str,
        file_path: str,
        branch: str,
        access_token: str
    ) -> Optional[str]:
        """Get the SHA of a file in a repository"""
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {access_token}"
        }
        
        params = {"ref": branch}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                params=params,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("sha")
            return None
    
    async def get_file_content_with_sha(
        self,
        owner: str,
        repo: str,
        file_path: str,
        branch: str,
        access_token: str
    ) -> Optional[Tuple[str, str]]:
        """Get file content and SHA together"""
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {access_token}"
        }
        
        params = {"ref": branch}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                params=params,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                content = base64.b64decode(data["content"]).decode('utf-8')
                return (content, data["sha"])
            return None
    
    async def update_file(
        self,
        owner: str,
        repo: str,
        file_path: str,
        content: str,
        message: str,
        branch: str,
        access_token: str,
        sha: str
    ) -> Optional[Dict[str, Any]]:
        """Update a file in the repository"""
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        content_base64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        payload = {
            "message": message,
            "content": content_base64,
            "branch": branch,
            "sha": sha
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                url,
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"Failed to update file {file_path}: {response.status_code} - {response.text}")
                return None
    
    def parse_unified_diff(self, diff_text: str) -> List[Dict[str, Any]]:
        """
        Parse unified diff format and extract file changes
        Returns list of: [{"file_path": str, "changes": [(line_num, old_line, new_line), ...]}, ...]
        """
        # Remove markdown code blocks if present
        diff_text = re.sub(r'^```diff\s*\n', '', diff_text, flags=re.MULTILINE)
        diff_text = re.sub(r'\n```\s*$', '', diff_text, flags=re.MULTILINE)
        
        file_changes = []
        current_file = None
        current_changes = []
        
        lines = diff_text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Detect file header: --- a/path/to/file.java
            if line.startswith('--- '):
                # Save previous file if exists
                if current_file:
                    file_changes.append({
                        "file_path": current_file,
                        "full_content": current_changes
                    })
                
                # Extract file path (remove 'a/' or 'b/' prefix)
                file_path = line[4:].strip()
                if file_path.startswith('a/'):
                    file_path = file_path[2:]
                
                # Get the +++ line
                i += 1
                if i < len(lines) and lines[i].startswith('+++ '):
                    new_path = lines[i][4:].strip()
                    if new_path.startswith('b/'):
                        new_path = new_path[2:]
                    current_file = new_path
                    current_changes = []
            
            # Collect the actual diff content
            elif current_file and (line.startswith('-') or line.startswith('+') or line.startswith('@@')):
                current_changes.append(line)
            elif current_file:
                current_changes.append(line)
            
            i += 1
        
        # Save last file
        if current_file:
            file_changes.append({
                "file_path": current_file,
                "full_content": current_changes
            })
        
        return file_changes
    
    def apply_diff_to_content(self, original_content: str, diff_hunks: List[str]) -> str:
        """
        Apply unified diff hunks to original file content
        Simple line-based replacement
        """
        lines = original_content.split('\n')
        new_lines = lines.copy()
        
        # Extract changes from diff hunks
        removals = []
        additions = []
        
        for hunk in diff_hunks:
            if hunk.startswith('-') and not hunk.startswith('---'):
                removals.append(hunk[1:])  # Remove '-' prefix
            elif hunk.startswith('+') and not hunk.startswith('+++'):
                additions.append(hunk[1:])  # Remove '+' prefix
        
        # Simple approach: replace lines that match removals with additions
        # For complex diffs, you might need a proper diff/patch library
        result_lines = []
        i = 0
        removal_idx = 0
        
        while i < len(new_lines):
            line = new_lines[i]
            
            # Check if this line should be removed
            if removal_idx < len(removals) and line == removals[removal_idx]:
                # Skip removed line, add corresponding addition if exists
                if removal_idx < len(additions):
                    result_lines.append(additions[removal_idx])
                removal_idx += 1
            else:
                result_lines.append(line)
            
            i += 1
        
        # Add any remaining additions
        while removal_idx < len(additions):
            result_lines.append(additions[removal_idx])
            removal_idx += 1
        
        return '\n'.join(result_lines)

# Global instance
github_service = GitHubService()
