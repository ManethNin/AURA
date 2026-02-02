"""
Repository management endpoints
View repos, changes, and trigger repairs
"""
from fastapi import APIRouter, HTTPException, Depends
from app.repositories.change_repository import change_repo
from app.repositories.repo_repository import repository_repo
from app.utils.logger import logger
from app.services.github_service import github_service
from app.models.user import UserInDB
from app.auth.jwt import get_current_user

router = APIRouter()

@router.get("/{change_id}")
async def get_change_details(change_id: str, current_user : UserInDB = Depends(get_current_user)):
    """Get detailed information about a specific change"""
    try:
        change = await change_repo.find_by_id(change_id)

        repo = await repository_repo.find_by_id(change.repository_id)
        
        if not change:
            raise HTTPException(404, "Change not found")
        
        if repo.owner_id != current_user.github_id:
            raise HTTPException(403, "Access denied, Github Ids don't match")
        
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

@router.get("/{change_id}/status")
async def get_change_status(change_id: str, current_user : UserInDB = Depends(get_current_user)):
    """Get real-time status of a change (for polling)"""
    try:
        change = await change_repo.find_by_id(change_id)
        
        if not change:
            raise HTTPException(404, "Change not found")
        
        repo = await repository_repo.find_by_id(change.repository_id)
    
        if repo.owner_id != current_user.github_id:
            raise HTTPException(403, "Access denied, Github Ids don't match")
        
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

@router.post("/{change_id}/pull-request")
async def create_pull_request(change_id: str, current_user: UserInDB = Depends(get_current_user)):
    """
    Create a pull request for a fixed change
    Parses the unified diff and applies all file changes
    """
    try:
        # Get the change
        change = await change_repo.find_by_id(change_id)
        
        if not change:
            raise HTTPException(404, "Change not found")
        
        # Verify ownership
        repo = await repository_repo.find_by_id(change.repository_id)
        
        if not repo:
            raise HTTPException(404, "Repository not found")
        
        if repo.owner_id != current_user.github_id:
            raise HTTPException(403, "Access denied")
        
        # Check if change is fixed
        if change.status != "fixed":
            raise HTTPException(400, f"Cannot create PR. Change status is '{change.status}'. Must be 'fixed'.")
        
        # Check if user has access token
        if not current_user.access_token:
            raise HTTPException(401, "GitHub access token not found. Please re-authenticate.")
        
        # Parse repository owner and name
        owner, repo_name = repo.full_name.split("/")

        # Get the default branch (main or master)
        logger.info(f"Detecting default branch for {repo.full_name}")
        base_branch = await github_service.get_default_branch(
            owner=owner,
            repo=repo_name,
            access_token=current_user.access_token
        )
        logger.info(f"Using base branch: {base_branch}")
        
        # Generate unique branch name with timestamp to avoid conflicts
        import time
        timestamp = int(time.time())
        branch_name = f"aura-fix-{change.commit_sha[:7]}-{timestamp}"

        logger.info(f"Getting current HEAD of {base_branch}")
        base_sha = await github_service.get_branch_head_sha(
            owner=owner,
            repo=repo_name,
            branch=base_branch,
            access_token=current_user.access_token
        )
        
        if not base_sha:
            raise HTTPException(500, f"Failed to get HEAD SHA of {base_branch} branch")
        
        
        # Step 1: Create new branch from the commit
        logger.info(f"Creating branch {branch_name} from {change.commit_sha}")
        branch_created = await github_service.create_branch(
            owner=owner,
            repo=repo_name,
            branch_name=branch_name,
            base_sha=base_sha,
            access_token=current_user.access_token
        )
        
        if not branch_created:
            raise HTTPException(500, "Failed to create branch on GitHub")
        
        # Step 2: Determine how to apply changes
        # If we have modified_files (from recipe agent), use them directly
        # Otherwise, parse the diff and apply it
        
        updated_files = []
        
        if change.modified_files:
            # Recipe agent provided actual file contents - use them directly!
            logger.info(f"Using {len(change.modified_files)} modified files from recipe agent (no diff parsing needed)")
            
            for file_path, new_content in change.modified_files.items():
                logger.info(f"Updating file directly: {file_path}")
                
                # Get current file SHA (needed for update)
                file_data = await github_service.get_file_content_with_sha(
                    owner=owner,
                    repo=repo_name,
                    file_path=file_path,
                    branch=branch_name,
                    access_token=current_user.access_token
                )
                
                if not file_data:
                    logger.error(f"Failed to get SHA for {file_path}")
                    continue
                
                _, file_sha = file_data
                
                # Update file on GitHub with the correct content
                commit_result = await github_service.update_file(
                    owner=owner,
                    repo=repo_name,
                    file_path=file_path,
                    content=new_content,
                    message=f"🤖 AURA: Fix {file_path}",
                    branch=branch_name,
                    access_token=current_user.access_token,
                    sha=file_sha
                )
                
                if commit_result:
                    updated_files.append(file_path)
                    logger.info(f"✓ Updated {file_path}")
                else:
                    logger.error(f"✗ Failed to update {file_path}")
        else:
            # Fall back to parsing diff (for legacy agent or if no modified_files)
            logger.info(f"Parsing unified diff (no modified_files available)")
            file_changes = github_service.parse_unified_diff(change.diff or change.suggested_fix)
            
            if not file_changes:
                raise HTTPException(400, "No file changes found in diff")
            
            logger.info(f"Found {len(file_changes)} files to update from diff")
            
            for file_change in file_changes:
                file_path = file_change["file_path"]
                
                # Skip if it's /dev/null (new file creation - not supported yet)
                if file_path == "/dev/null":
                    logger.warning(f"Skipping new file creation: not implemented")
                    continue
                
                logger.info(f"Updating file: {file_path}")
                
                # Get current file content and SHA
                file_data = await github_service.get_file_content_with_sha(
                    owner=owner,
                    repo=repo_name,
                    file_path=file_path,
                    branch=branch_name,
                    access_token=current_user.access_token
                )
                
                if not file_data:
                    logger.error(f"Failed to get content for {file_path}")
                    continue
                
                original_content, file_sha = file_data
                
                # Apply diff to content
                new_content = github_service.apply_diff_to_content(
                    original_content,
                    file_change["full_content"]
                )
                
                # Update file on GitHub
                commit_result = await github_service.update_file(
                    owner=owner,
                    repo=repo_name,
                    file_path=file_path,
                    content=new_content,
                    message=f"🤖 AURA: Fix {file_path}",
                    branch=branch_name,
                    access_token=current_user.access_token,
                    sha=file_sha
                )
                
                if commit_result:
                    updated_files.append(file_path)
                    logger.info(f"✓ Updated {file_path}")
                else:
                    logger.error(f"✗ Failed to update {file_path}")
        
        if not updated_files:
            raise HTTPException(500, "Failed to update any files")
        
        # Step 4: Create pull request
        logger.info(f"Creating pull request")
        pr_title = f"🤖 AURA: Auto-fix dependency migration issues"
        pr_body = f"""## Automated Dependency Fix by AURA

This pull request was automatically generated to fix dependency migration issues.

### Original Commit
- **SHA**: `{change.commit_sha}`
- **Message**: {change.commit_message}

### Files Changed
{chr(10).join([f'- `{f}`' for f in updated_files])}

### Changes Applied
```diff
{change.diff or change.suggested_fix}
```

---
*Generated by [AURA](https://github.com/ManethNin/AURA) - Automated Dependency Repair Assistant*
"""
        
        pr_data = await github_service.create_pull_request(
            owner=owner,
            repo=repo_name,
            title=pr_title,
            body=pr_body,
            head_branch=branch_name,
            base_branch=base_branch,
            access_token=current_user.access_token
        )
        
        if not pr_data:
            raise HTTPException(500, "Failed to create pull request on GitHub")
        
        # Step 5: Update change record with PR URL
        await change_repo.update_pr_url(change_id, pr_data["html_url"])
        
        logger.info(f"✓ Created PR #{pr_data['number']}: {pr_data['html_url']}")
        
        return {
            "success": True,
            "pr_url": pr_data["html_url"],
            "pr_number": pr_data["number"],
            "branch": branch_name,
            "files_updated": updated_files,
            "message": "Pull request created successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating pull request: {str(e)}")
        raise HTTPException(500, f"Failed to create pull request: {str(e)}")