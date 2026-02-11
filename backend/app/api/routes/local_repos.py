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

# Import the agent services
from app.agents.service import JavaMigrationAgentService
from app.agents.planning_service import PlanningAgentService


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
        # Try to get recent git diff for pom.xml (including nested ones)
        try:
            import subprocess
            
            # First, find all pom.xml files in the repo
            logger.info(f"[GIT] Searching for pom.xml files in {repo_path}")
            find_result = subprocess.run(
                ["git", "ls-files", "*pom.xml"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            logger.info(f"[GIT] Command: git ls-files *pom.xml")
            logger.info(f"[GIT] Return code: {find_result.returncode}")
            if find_result.stderr:
                logger.info(f"[GIT] Stderr: {find_result.stderr}")
            
            pom_files = [f.strip() for f in find_result.stdout.split('\n') if f.strip()]
            logger.info(f"[GIT] Found {len(pom_files)} pom.xml file(s): {pom_files}")
            
            if not pom_files:
                logger.warning(f"[GIT] No pom.xml files found in git repo")
            else:
                # Try HEAD~1 first (most recent change)
                cmd = ["git", "diff", "HEAD~1", "HEAD", "--"] + pom_files
                logger.info(f"[GIT] Command: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                
                logger.info(f"[GIT] Return code: {result.returncode}")
                logger.info(f"[GIT] Output length: {len(result.stdout)} chars")
                if result.stderr:
                    logger.info(f"[GIT] Stderr: {result.stderr}")
                
                if result.returncode == 0 and result.stdout:
                    pom_diff = result.stdout
                    logger.info(f"[GIT] ✓ Detected pom.xml changes from git diff (HEAD~1 vs HEAD)")
                else:
                    # Try without HEAD~1 (in case only one commit exists)
                    logger.info(f"[GIT] ✗ No diff between HEAD~1 and HEAD, trying uncommitted changes...")
                    cmd = ["git", "diff", "HEAD", "--"] + pom_files
                    logger.info(f"[GIT] Command: {' '.join(cmd)}")
                    result = subprocess.run(
                        cmd,
                        cwd=repo_path,
                        capture_output=True,
                        text=True
                    )
                    
                    logger.info(f"[GIT] Return code: {result.returncode}")
                    logger.info(f"[GIT] Output length: {len(result.stdout)} chars")
                    if result.stderr:
                        logger.info(f"[GIT] Stderr: {result.stderr}")
                    
                    if result.returncode == 0 and result.stdout:
                        pom_diff = result.stdout
                        logger.info(f"[GIT] ✓ Detected uncommitted pom.xml changes")
                    else:
                        # Try to get diffs of last changes to any pom.xml
                        logger.info(f"[GIT] ✗ No changes detected, checking git log for pom.xml modifications...")
                        cmd = ["git", "log", "--pretty=format:%H", "-n", "1", "--"] + pom_files
                        logger.info(f"[GIT] Command: {' '.join(cmd)}")
                        result = subprocess.run(
                            cmd,
                            cwd=repo_path,
                            capture_output=True,
                            text=True
                        )
                        
                        logger.info(f"[GIT] Return code: {result.returncode}")
                        logger.info(f"[GIT] Output length: {len(result.stdout)} chars")
                        if result.stderr:
                            logger.info(f"[GIT] Stderr: {result.stderr}")
                        
                        if result.returncode == 0 and result.stdout:
                            last_commit = result.stdout.strip()
                            logger.info(f"[GIT] ✓ Found pom.xml last modified in commit: {last_commit[:7]}")
                            # Get diff of last change to any pom.xml
                            cmd = ["git", "show", f"{last_commit}^..{last_commit}", "--"] + pom_files
                            logger.info(f"[GIT] Command: {' '.join(cmd)}")
                            result = subprocess.run(
                                cmd,
                                cwd=repo_path,
                                capture_output=True,
                                text=True
                            )
                            
                            logger.info(f"[GIT] Return code: {result.returncode}")
                            logger.info(f"[GIT] Output length: {len(result.stdout)} chars")
                            if result.stderr:
                                logger.info(f"[GIT] Stderr: {result.stderr}")
                            
                            if result.returncode == 0 and result.stdout:
                                pom_diff = result.stdout
                                logger.info(f"[GIT] ✓ Got pom.xml changes from history")
                        
                        if not pom_diff:
                            logger.warning(f"[GIT] ✗ Could not find any pom.xml changes")
                            pom_diff = ""
        except Exception as e:
            logger.warning(f"[GIT] Exception during pom.xml detection: {e}")
            import traceback
            logger.warning(traceback.format_exc())
            pom_diff = ""
    
    logger.info(f"[GIT] Final result: pom_diff length = {len(pom_diff) if pom_diff else 0} chars")
    
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
    api_result = {"raw": "", "filtered": "", "tool_used": "none"}  # Initialize with defaults
    
    if pom_diff:
        try:
            from app.masterthesis.agent.JapiCmpAgent import JapiCmpAgent

            api_change_agent = JapiCmpAgent(pipeline_logger=pipeline_logger)
            api_result = api_change_agent.generate_api_changes_with_raw(
                repo_path=str(repo_path),
                pom_diff=pom_diff,
                compilation_errors=initial_errors  # Filter API changes to only relevant ones
            )
            
            # Log full/raw API changes result
            if api_result.get("raw"):
                logger.info(f"[REVAPI] Full raw API changes ({len(api_result['raw'])} chars):")
                logger.info(api_result["raw"][:500])  # Log first 500 chars to console
            
            # Use filtered version for next stage (LLM processing)
            api_changes_text = api_result.get("filtered", "")
            
            if api_changes_text:
                logger.info(f"Generated API changes ({len(api_changes_text)} chars)")
            else:
                logger.info("No API changes generated (tool not configured or no changes found)")
        except Exception as e:
            logger.warning(f"API change analysis failed: {e}")
    
    try:
        # ========================================
        # PLANNING AGENT (runs first, creates migration plan)
        # ========================================
        # migration_plan = ""
        # if initial_errors:
        #     logger.info(f"[PlanningAgent] Generating migration plan for {repo_name}")
        #     try:
        #         planning_service = PlanningAgentService()
        #         plan_result = planning_service.create_plan(
        #             repo_path=str(repo_path),
        #             commit_hash=commit_hash,
        #             repo_slug=repo_name,
        #             pom_diff=pom_diff,
        #             initial_errors=initial_errors,
        #             api_changes_text=api_changes_text,
        #             pipeline_logger=pipeline_logger,
        #         )
        #         if plan_result and plan_result.get("success"):
        #             migration_plan = plan_result["plan"]
        #             logger.info(f"[PlanningAgent] Migration plan ready ({len(migration_plan)} chars)")
        #         else:
        #             logger.warning(f"[PlanningAgent] Planning failed: {plan_result.get('error')}, continuing without plan")
        #     except Exception as e:
        #         logger.warning(f"[PlanningAgent] Planning agent error: {e}, continuing without plan")

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
                    api_changes=api_changes_text,  # Pass filtered API changes
                    api_changes_raw=api_result.get("raw", "")  # Pass full/raw API changes for logging
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
            pipeline_logger=pipeline_logger,  # Pass the same logger instance
            # migration_plan=migration_plan,  # Pass the planning agent's output
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
