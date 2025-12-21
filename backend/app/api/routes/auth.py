"""
Authentication endpoints
GitHub OAuth login and token management
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from app.core.config import settings
import requests
from app.auth.jwt import create_access_token, get_current_user
from app.auth.github_oauth import GitHubOAuth
from app.models.user import User, UserInDB
from app.repositories.user_repository import user_repo


router = APIRouter()

# TODO: Implement authentication routes
# - GitHub OAuth login
# - Callback handler
# - Token generation (JWT)
# - Token refresh
# - Logout

github_oauth = GitHubOAuth(
    client_id=settings.GITHUB_CLIENT_ID,
    client_secret=settings.GITHUB_CLIENT_SECRET
)


@router.get("/github/login")
async def login():
    github_auth_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={(settings.GITHUB_CLIENT_ID)}"
        "&scope=read:user user:email"
    )
    return RedirectResponse(github_auth_url)

# This call by GitHub
@router.get("/github/callback")
async def github_callback(code: str):
    try:
        # 1. Exchange code → access token
        access_token = await github_oauth.exchange_code_for_token(code=code)

        if not access_token:
            raise HTTPException(400, "GitHub auth failed")
        
        # 2. Get user info
        user_info = await github_oauth.get_user_info(access_token)

        user = User(
                github_id=str(user_info["id"]),
                username=user_info["login"],
                email=user_info.get("email"),
                avatar_url=user_info.get("avatar_url"),
                access_token=access_token  # Store for GitHub API calls
            )
        
        await user_repo.create_or_update(user)
        

        # 3. Create YOUR JWT
        jwt_token = create_access_token({"github_id": user.github_id,"username": user.username, "email": user.email})

        # 4. Redirect back to React
        frontend_url = settings.FRONTEND_URL
        return RedirectResponse(f"{frontend_url}/auth/callback?token={jwt_token}")
    
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"GitHub authentication failed: {str(e)}"
        )
    



