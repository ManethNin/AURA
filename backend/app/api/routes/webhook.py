"""
GitHub webhook endpoint
Receives GitHub App webhook events for pom.xml changes
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Header, Request, HTTPException
from datetime import datetime
from app.services.github_service import github_service
from app.database.mongodb import get_database
from app.models.user import User, UserInDB
from app.models.repository import Repository, RepositoryInDB
from app.services.webhook_service import webhook_service


router = APIRouter()

@router.post("")
async def github_webhook(

    request: Request,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None)
):
    """
    Handle GitHub webhook events
    PRODUCTION-READY: Verifies signature, saves to DB
    """
    
    # Read raw body for signature verification
    body = await request.body()
    
    # SECURITY: Verify webhook signature
    if not github_service.verify_webhook_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    # Parse JSON payload
    payload = await request.json()
    
    # Only process push events
    if x_github_event != "push":
        return {"message": f"Ignored: {x_github_event} event"}
    
    # Extract repository info
    repo_data = payload.get("repository", {})
    owner_data = repo_data.get("owner", {})
    commits = payload.get("commits", [])
    installation_id = payload.get("installation", {}).get("id")  # ✅ From root level

    
    # Check if any commit contains pom.xml changes
    pom_changed = False
    commit_with_pom = None
    
    for commit in commits:
        all_files = (
            commit.get("added", []) + 
            commit.get("modified", []) + 
            commit.get("removed", [])
        )
        
        if any("pom.xml" in f for f in all_files):
            pom_changed = True
            commit_with_pom = commit
            break
    
    if not pom_changed:
        return {"message": "No pom.xml changes detected"}
    
    result = await webhook_service.process_webhook(repo_data=repo_data, owner_data= owner_data, commit_with_pom= commit_with_pom, installation_id= installation_id)
    
    return {
        "status": "success",
        "message": "pom.xml change processed",
        "data": result
    }
    
