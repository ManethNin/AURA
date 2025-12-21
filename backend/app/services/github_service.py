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
from typing import Optional, Dict, Any
import httpx
from app.core.config import settings
from app.repositories.change_repository import change_repo


class GitHubService:
    """Service for GitHub API operations"""
    
    def __init__(self):
        self.webhook_secret = settings.GITHUB_WEBHOOK_SECRET
        self.app_id = settings.GITHUB_APP_ID
    
    def verify_webhook_signature(self, payload_body: bytes, signature_header: str) -> bool:
        """
        Verify GitHub webhook signature for security
        CRITICAL: Always verify webhooks in production!
        """
        if not signature_header:
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
    
    async def get_repo_info(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Get GitHub repository information"""
        url = f"https://api.github.com/repos/{owner}/{repo}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                return response.json()
            return None
        
    async def create_pull_request(change_id: str):
        fixed_change = await change_repo.find_by_id(change_id=change_id)

    

# Global instance
github_service = GitHubService()
