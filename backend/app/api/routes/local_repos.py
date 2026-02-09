"""
Local repositories API routes
Endpoints for managing and processing local Java repositories
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from app.services.local_repository_service import local_repo_service
from app.core.config import settings
from app.utils.logger import logger
from app.utils.pipeline_logger import PipelineLogger

# Import the agent service
from app.agents.service import JavaMigrationAgentService


router = APIRouter()


class CloneRepositoryRequest(BaseModel):
    git_url: str
    target_name: Optional[str] = None


class ProcessRepositoryRequest(BaseModel):
    repo_name: str
    pom_diff: Optional[str] = ""  # Optional: provide specific pom.xml changes to analyze
    initial_errors: Optional[str] = ""  # Optional: provide initial Maven errors


class RepositoryResponse(BaseModel):
    name: str
    path: str
    has_pom: bool
    is_git: bool
    git_info: Optional[Dict[str, Any]] = None


@router.get("/list", response_model=List[RepositoryResponse])
async def list_local_repositories():
    """
    List all local Java (Maven) repositories in the workspace
    Only includes directories with pom.xml files
    """
    if not settings.LOCAL_MODE:
        raise HTTPException(
            status_code=400,
            detail="This endpoint is only available in LOCAL_MODE"
        )
    
    try:
        repositories = local_repo_service.list_local_repositories()
        return repositories
    except Exception as e:
        logger.error(f"Error listing repositories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clone")
async def clone_repository(request: CloneRepositoryRequest):
    """
    Clone a repository from GitHub to the local workspace
    
    Request body:
    - git_url: GitHub repository URL (e.g., https://github.com/owner/repo.git)
    - target_name: Optional custom directory name
    """
    if not settings.LOCAL_MODE:
        raise HTTPException(
            status_code=400,
            detail="This endpoint is only available in LOCAL_MODE"
        )
    
    try:
        repo_path = local_repo_service.clone_repository(
            git_url=request.git_url,
            target_name=request.target_name
        )
        
        # Check if it's a Maven project
        has_pom = (repo_path / "pom.xml").exists()
        
        return {
            "success": True,
            "message": "Repository cloned successfully",
            "path": str(repo_path),
            "name": repo_path.name,
            "has_pom": has_pom
        }
    except Exception as e:
        logger.error(f"Error cloning repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process/{repo_name}")
async def process_repository(
    repo_name: str,
    request: ProcessRepositoryRequest,
    background_tasks: BackgroundTasks
):
    """
    Process a local repository with the Java migration agent
    
    Path parameter:
    - repo_name: Name of the repository directory
    
    Request body:
    - pom_diff: Optional pom.xml changes to analyze
    - initial_errors: Optional Maven compilation errors
    """
    if not settings.LOCAL_MODE:
        raise HTTPException(
            status_code=400,
            detail="This endpoint is only available in LOCAL_MODE"
        )
    
    # Validate repository exists
    repo_path = local_repo_service.get_repository_path(repo_name)
    if not repo_path:
        raise HTTPException(
            status_code=404,
            detail=f"Repository '{repo_name}' not found in workspace"
        )
    
    # Check if it has pom.xml
    if not local_repo_service.check_pom_exists(repo_name):
        raise HTTPException(
            status_code=400,
            detail=f"Repository '{repo_name}' does not contain pom.xml"
        )
    
    # Get git info
    git_info = local_repo_service._get_git_info(repo_path)
    commit_hash = git_info.get("commit", "local") if git_info else "local"
    
    # If no pom_diff provided, try to detect recent changes
    pom_diff = request.pom_diff
    if not pom_diff:
        # Try to get recent git diff for pom.xml
        try:
            import subprocess
            result = subprocess.run(
                ["git", "diff", "HEAD~1", "HEAD", "--", "**/pom.xml"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout:
                pom_diff = result.stdout
                logger.info(f"Detected pom.xml changes from git diff")
        except Exception as e:
            logger.warning(f"Could not detect pom.xml changes: {e}")
            pom_diff = "No diff provided"
    
    # Step 1: Compile in Docker to get initial errors
    initial_errors = request.initial_errors
    if not initial_errors:
        logger.info(f"Compiling {repo_name} in Docker to get initial errors...")
        try:
            from app.masterthesis.agent.MavenReproducerAgent import MavenReproducerAgent
            from pathlib import Path
            
            maven_agent = MavenReproducerAgent(Path(repo_path))
            with maven_agent.start_container():
                (compile_ok, test_ok), error_text, _ = maven_agent.compile_maven(
                    diffs=[],
                    run_tests=False,
                    timeout=300
                )
            
            if not compile_ok:
                initial_errors = error_text
                logger.info(f"Compilation failed - detected errors ({len(error_text)} chars)")
            else:
                logger.info("Project compiles successfully - no errors to fix")
                return {
                    "success": True,
                    "repository": repo_name,
                    "message": "Project compiles successfully, no fixes needed"
                }
        except Exception as e:
            logger.error(f"Error during initial compilation: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to compile project: {str(e)}")

    # Initialize pipeline logger early so it can be used by API change analysis
    pipeline_logger = PipelineLogger(repo_name)
    
    # Log initial input data
    pipeline_logger.log_input(
        pom_diff=pom_diff,
        initial_errors=initial_errors,
        repo_path=str(repo_path),
        commit_hash=commit_hash
    )

    # Step 1.5: Generate API changes from dependency diff (REVAPI/JApiCmp)
    api_changes_text = ""
    if pom_diff:
        try:
            from app.masterthesis.agent.JapiCmpAgent import JapiCmpAgent

            api_change_agent = JapiCmpAgent(pipeline_logger=pipeline_logger)
            api_changes_text = api_change_agent.generate_api_changes(
                repo_path=str(repo_path),
                pom_diff=pom_diff,
                compilation_errors=initial_errors  # Filter API changes to only relevant ones
            )
            if api_changes_text:
                logger.info(f"Generated API changes ({len(api_changes_text)} chars)")
            else:
                logger.info("No API changes generated (tool not configured or no changes found)")
        except Exception as e:
            logger.warning(f"API change analysis failed: {e}")
    
    try:
        # ========================================
        # RECIPE-BASED AGENT (tries first)
        # ========================================
        recipe_result = None
        if initial_errors:  # Check the local variable, not request.initial_errors!
            logger.info(f"[RecipeAgent] Attempting recipe-based fix for {repo_name}")
            try:
                from app.recipe_agent.recipe_orchestrator import RecipeOrchestrator
                
                orchestrator = RecipeOrchestrator(settings.GROQ_API_KEY, pipeline_logger=pipeline_logger)
                recipe_result = orchestrator.process_breaking_change(
                    repo_path=str(repo_path),
                    pom_diff=pom_diff,
                    compilation_errors=initial_errors,  # Use the local variable
                    commit_sha=commit_hash,
                    repo_slug=repo_name,
                    api_changes=api_changes_text  # Pass filtered API changes
                )
                
                if recipe_result and recipe_result.get("success"):
                    logger.info(f"[RecipeAgent] Successfully fixed using recipes for {repo_name}")
                    pipeline_logger.log_final_result(True, recipe_result)
                    pipeline_logger.finalize()
                    return {
                        "success": True,
                        "repository": repo_name,
                        "commit": commit_hash,
                        "method": "recipe_agent",
                        "recipes_applied": recipe_result.get("recipes_applied", []),
                        "result": recipe_result
                    }
                else:
                    logger.info(f"[RecipeAgent] Recipe fix not applicable, falling back to LLM agent")
            except Exception as e:
                logger.warning(f"[RecipeAgent] Recipe agent failed: {e}, falling back to LLM agent")
        
        # ========================================
        # LLM AGENT (fallback or primary if no errors)
        # ========================================
        # Initialize the agent service with configured provider
        agent_service = JavaMigrationAgentService()
       
        # Process the repository
        logger.info(f"Starting agent processing for {repo_name}")
        result = agent_service.process_repository(
            repo_path=str(repo_path),
            commit_hash=commit_hash,
            repo_slug=repo_name,  # Use repo_name as slug for local repos
            pom_diff=pom_diff,
            initial_errors=initial_errors,  # Use the local variable
            api_changes_text=api_changes_text,
            pipeline_logger=pipeline_logger  # Pass the same logger instance
        )
        
        # Finalize pipeline logger after LLM agent completes
        pipeline_logger.log_final_result(result.get("success", False), result)
        pipeline_logger.finalize()
        
        return {
            "success": result.get("success", False),
            "repository": repo_name,
            "commit": commit_hash,
            "method": "llm_agent",
            "result": result
        }
    
    except Exception as e:
        logger.error(f"Error processing repository {repo_name}: {e}")
        try:
            pipeline_logger.log_error("process_error", str(e), __import__('traceback').format_exc())
            pipeline_logger.finalize()
        except:
            pass  # If logging also failed, don't raise another exception
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info/{repo_name}")
async def get_repository_info(repo_name: str):
    """
    Get detailed information about a local repository
    
    Path parameter:
    - repo_name: Name of the repository directory
    """
    if not settings.LOCAL_MODE:
        raise HTTPException(
            status_code=400,
            detail="This endpoint is only available in LOCAL_MODE"
        )
    
    repo_path = local_repo_service.get_repository_path(repo_name)
    if not repo_path:
        raise HTTPException(
            status_code=404,
            detail=f"Repository '{repo_name}' not found"
        )
    
    git_info = local_repo_service._get_git_info(repo_path)
    has_pom = local_repo_service.check_pom_exists(repo_name)
    
    return {
        "name": repo_name,
        "path": str(repo_path),
        "has_pom": has_pom,
        "is_git": git_info is not None,
        "git_info": git_info
    }
