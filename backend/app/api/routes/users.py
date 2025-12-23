"""
User management endpoints
"""
# TODO: Implement user routes
# - Get current user profile
# - Update user settings
# - Get user activity


from fastapi import APIRouter, HTTPException, Depends
from app.utils.logger import logger
from app.services.github_service import github_service
from app.models.user import UserInDB
from app.auth.jwt import get_current_user

router = APIRouter()

@router.get("/me")
async def get_current_user_info(current_user: UserInDB = Depends(get_current_user)):
    """Get current authenticated user's profile"""
    return {
        "id": current_user.id,
        "github_id": current_user.github_id,
        "username": current_user.username,
        "email": current_user.email,
        "avatar_url": current_user.avatar_url,
        "repositories": current_user.repositories,
        "created_at": current_user.created_at.isoformat(),
        "updated_at": current_user.updated_at.isoformat()
    }

# @router.get("/me/repositories")
# async def get_my_repositories(current_user : UserInDB = Depends(get_current_user)):
#     return {
#             "repositories": current_user.repositories,
#             "count": len(current_user.repositories)
        # }
