"""
Repository management endpoints
View repos, changes, and trigger repairs
"""
from fastapi import APIRouter, HTTPException
from app.repositories.change_repository import change_repo
from app.utils.logger import logger

router = APIRouter()

@router.get("/changes/{change_id}")
async def get_change_details(change_id: str):
    """Get detailed information about a specific change"""
    try:
        change = await change_repo.find_by_id(change_id)
        
        if not change:
            raise HTTPException(404, "Change not found")
        
        return {
            "id": str(change.id),
            "repository_id": change.repository_id,
            "commit_sha": change.commit_sha,
            "commit_message": change.commit_message,
            "status": change.status,
            "progress": change.progress,
            "status_message": change.status_message,
            "breaking_changes": change.breaking_changes,
            "suggested_fix": change.suggested_fix,
            "diff": change.diff,
            "error_message": change.error_message,
            "created_at": change.created_at.isoformat(),
            "updated_at": change.updated_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching change details: {str(e)}")
        raise HTTPException(500, "Failed to fetch change details")

@router.get("/changes/{change_id}/status")
async def get_change_status(change_id: str):
    """Get real-time status of a change (for polling)"""
    try:
        change = await change_repo.find_by_id(change_id)
        
        if not change:
            raise HTTPException(404, "Change not found")
        
        return {
            "id": str(change.id),
            "status": change.status,
            "progress": change.progress,
            "message": change.status_message,
            "error": change.error_message,
            "is_complete": change.status in ["fixed", "failed"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching status: {str(e)}")
        raise HTTPException(500, "Failed to fetch status")

