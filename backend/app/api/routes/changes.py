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
        
        # Generate branch name
        branch_name = f"aura-fix-{change.commit_sha[:7]}"

        
        logger.info(f"Getting current HEAD of {base_branch}")
        base_sha = await github_service.get_branch_head_sha(
            owner=owner,
            repo=repo_name,
            branch=base_branch,
            access_token=current_user.access_token
        )
        
        if not base_sha:
            raise HTTPException(500, f"Failed to get HEAD SHA of {base_branch} branch")
        
        # Apply the unified diff using UnifiedDiffCoder
        logger.info(f"Applying unified diff using UnifiedDiffCoder")
        
        # Import the proper diff coder
        from app.masterthesis.agent.aider.AdvancedDiffAgent import UnifiedDiffCoder
        from pathlib import Path
        import tempfile
        import subprocess
        
        # Create a temporary directory to clone and work with the repo
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_repo_path = Path(temp_dir) / "repo"
            
            # Clone the repository
            clone_url = f"https://{current_user.access_token}@github.com/{owner}/{repo_name}.git"
            logger.info(f"Cloning repository to temporary directory")
            subprocess.run(
                ["git", "clone", "--depth=1", f"--branch={base_branch}", clone_url, str(temp_repo_path)],
                check=True,
                capture_output=True
            )
            
            # Apply the diff using UnifiedDiffCoder
            coder = UnifiedDiffCoder(temp_repo_path)
            diff_content = change.diff or change.suggested_fix
            success, result = coder.apply_edits(diff_content)
            
            if not success:
                raise HTTPException(400, f"Failed to apply diff: {result}")
            
            logger.info(f"Diff applied successfully: {result}")
            
            # Get list of modified files
            git_status = subprocess.run(
                ["git", "-C", str(temp_repo_path), "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True
            )
            
            modified_files = []
            for line in git_status.stdout.strip().split('\n'):
                if line:
                    # Format: " M file.java" or "M  file.java"
                    parts = line.split()
                    if len(parts) >= 2:
                        modified_files.append(parts[1])
            
            logger.info(f"Modified files: {modified_files}")
            
            if not modified_files:
                raise HTTPException(400, "No files were modified by the diff")
            
            # Create branch and push changes
            logger.info(f"Creating and pushing branch {branch_name}")
            subprocess.run(
                ["git", "-C", str(temp_repo_path), "checkout", "-b", branch_name],
                check=True,
                capture_output=True
            )
            
            subprocess.run(
                ["git", "-C", str(temp_repo_path), "add", "-A"],
                check=True,
                capture_output=True
            )
            
            subprocess.run(
                ["git", "-C", str(temp_repo_path), "commit", "-m", "🤖 AURA: Auto-fix dependency migration issues"],
                check=True,
                capture_output=True
            )
            
            subprocess.run(
                ["git", "-C", str(temp_repo_path), "push", "origin", branch_name],
                check=True,
                capture_output=True
            )
        
        
        # Step 3: Create pull request
        logger.info(f"Creating pull request")
        pr_title = f"🤖 AURA: Auto-fix dependency migration issues"
        pr_body = f"""## Automated Dependency Fix by AURA

This pull request was automatically generated to fix dependency migration issues.

### Original Commit
- **SHA**: `{change.commit_sha}`
- **Message**: {change.commit_message}

### Files Changed
{chr(10).join([f'- `{f}`' for f in modified_files])}

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
        
        # Step 4: Update change record with PR URL
        await change_repo.update_pr_url(change_id, pr_data["html_url"])
        
        logger.info(f"✓ Created PR #{pr_data['number']}: {pr_data['html_url']}")
        
        return {
            "success": True,
            "pr_url": pr_data["html_url"],
            "pr_number": pr_data["number"],
            "branch": branch_name,
            "files_updated": modified_files,
            "message": "Pull request created successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating pull request: {str(e)}")
        raise HTTPException(500, f"Failed to create pull request: {str(e)}")