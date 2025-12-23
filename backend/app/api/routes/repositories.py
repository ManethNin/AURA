"""
Repository management endpoints
View repos, changes, and trigger repairs
"""
from fastapi import APIRouter, HTTPException, Depends
from app.repositories.repo_repository import repository_repo, change_repo
from app.utils.logger import logger
from app.services.github_service import github_service
from app.models.user import UserInDB
from app.auth.jwt import get_current_user

router = APIRouter()

@router.get("")
async def get_all_repos(current_user: UserInDB = Depends(get_current_user)):
    try:
        repos = await repository_repo.find_all_by_owner_id(current_user.github_id)
        
        return repos if repos else []
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching repos: {str(e)}")
        raise HTTPException(500, "Failed to fetch repos")


@router.get("/{id}")
async def get_repo_details(id: str, current_user : UserInDB = Depends(get_current_user)):
    """Get detailed information about a specific repo"""
    try:
        repo = await repository_repo.find_by_id(id)
        
        if not repo:
            raise HTTPException(404, "Repo not found")
        
        if repo.owner_id != current_user.github_id:
            raise HTTPException(403, "Access denied, Github Ids don't match")
        
        return {
            "id": str(repo.id),
            "repository_id": repo.github_repo_id,
            "name": repo.name,
            "owner_id": repo.owner_id,
            "installation_id": repo.installation_id,
            "is_active": repo.is_active,
            "last_commit_sha": repo.last_commit_sha,
            "last_pom_change": repo.last_pom_change,
            "created_at": repo.created_at,
            "updated_at": repo.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching repo details: {str(e)}")
        raise HTTPException(500, "Failed to fetch repo details")
    

@router.delete("/{id}")
async def delete_repository(id: str, current_user : UserInDB = Depends(get_current_user)):
    """Delete a specific repository"""
    try:
        # First verify ownership before deleting
        repo = await repository_repo.find_by_id(id)
        
        if not repo:
            raise HTTPException(404, "Repo not found")
        
        if repo.owner_id != current_user.github_id:
            raise HTTPException(403, "Access denied, Github Ids don't match")
        
        # Now delete the repo
        repo_id = await repository_repo.delete_by_githubid(id)
        
        return {"id": repo_id, "message": "Repository deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting repo: {str(e)}")
        raise HTTPException(500, "Failed to delete repo")
    
@router.get("/{id}/changes")
async def get_repository_changes(id: str, current_user : UserInDB = Depends(get_current_user)):
    """Get all changes for a specific repository"""
    try:
        # First verify ownership
        repo = await repository_repo.find_by_id(id)
        if not repo:
            raise HTTPException(404, "Repository not found")
        
        if repo.owner_id != current_user.github_id:
            raise HTTPException(403, "Access denied, Github Ids don't match")
        
        # Get changes for this repo
        changes = await change_repo.find_by_repository(id)

        return changes if changes else []
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching changes details: {str(e)}")
        raise HTTPException(500, "Failed to fetch changes details")
