"""
JWT token utilities
"""

# TODO: Implement JWT utilities
# - Create access tokens
# - Create refresh tokens
# - Verify tokens
# - Decode tokens
# - Token expiration handling

import jwt
from datetime import datetime, timedelta
from app.core.config import settings
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.repositories.user_repository import user_repo

security = HTTPBearer()


def create_access_token(payload: dict) -> str:
    """Create JWT access token"""
    data = {
        **payload,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=7),
    }

    return jwt.encode(
        data,
        settings.JWT_SECRET_KEY,
        algorithm="HS256"
    )


def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from token (dependency for FastAPI routes)"""
    token = credentials.credentials

    payload = verify_token(token)

    github_id = payload.get("github_id")
    if not github_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    user = await user_repo.find_by_github_id(github_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

async def get_current_user_payload(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get decoded JWT payload without database lookup"""
    return verify_token(credentials.credentials)

    
