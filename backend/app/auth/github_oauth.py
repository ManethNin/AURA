"""
GitHub OAuth handler
"""

# TODO: Implement GitHub OAuth
# - OAuth login flow
# - Exchange code for token
# - Get user info from GitHub
# - Store tokens securely

import requests
from app.core.config import settings
from fastapi import HTTPException


class GitHubOAuth:
    """
    Handle GitHub OAuth authentication
    """
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = "https://github.com/login/oauth/access_token"
        self.user_api_url = "https://api.github.com/user"
    
    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Generate GitHub OAuth URL"""
        pass
    
    async def exchange_code_for_token(self, code: str) -> dict:
        """Exchange authorization code for access token"""

        try:
            response = requests.post(
                self.token_url,
                headers={"Accept": "application/json"},
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                },
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            access_token = data.get("access_token")
            
            if not access_token:
                error = data.get("error_description", "Unknown error")
                raise HTTPException(
                    status_code=400, 
                    detail=f"GitHub OAuth failed: {error}"
                )
            
            return access_token
            
        except requests.RequestException as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to communicate with GitHub: {str(e)}"
            )
    
    async def get_user_info(self, access_token: str) -> dict:
        """Get user info from GitHub"""
        try:
            response = requests.get(
                self.user_api_url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch user info from GitHub: {str(e)}"
            )
        
