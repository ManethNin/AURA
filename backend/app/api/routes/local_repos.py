"""
Local repositories API routes
Endpoints for managing and processing local Java repositories

This module uses Docker containers to ensure proper dependency resolution:
- MavenReproducerAgent: Uses `maven:3.9.8-amazoncorretto-17` for compilation
- LSPAgent: Uses `ghcr.io/lukvonstrom/multilspy-java-docker:latest` for LSP analysis

Docker must be running for these endpoints to work properly.
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

# Docker-based agents for proper dependency management
from app.masterthesis.agent.MavenReproducerAgent import MavenReproducerAgent
from app.masterthesis.agent.LSPAgent import LSPAgent, extract_error_lines
from app.masterthesis.agent.DockerAgent import DockerError


router = APIRouter()

# Docker images required for the pipeline
REQUIRED_DOCKER_IMAGES = [
    "maven:3.9.8-amazoncorretto-17",  # For Maven compilation
    "ghcr.io/lukvonstrom/multilspy-java-docker:latest",  # For LSP analysis
]


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


class DockerStatusResponse(BaseModel):
    docker_available: bool
    images: List[Dict[str, Any]]
    missing_images: List[str]
    message: str


@router.get("/docker/status", response_model=DockerStatusResponse)
async def check_docker_status():
    """
    Check Docker availability and list required images.
    
    This endpoint verifies:
    - Docker daemon is running
    - Required images are available locally
    
    Required images:
    - maven:3.9.8-amazoncorretto-17 (Maven compilation)
    - ghcr.io/lukvonstrom/multilspy-java-docker:latest (LSP analysis)
    """
    if not settings.LOCAL_MODE:
        raise HTTPException(
            status_code=400,
            detail="This endpoint is only available in LOCAL_MODE"
        )
    
    try:
        import docker
        client = docker.from_env()
        client.ping()
        
        # Check which images are available
        available_images = []
        missing_images = []
        
        for image_name in REQUIRED_DOCKER_IMAGES:
            try:
                image = client.images.get(image_name)
                available_images.append({
                    "name": image_name,
                    "id": image.short_id,
                    "created": str(image.attrs.get("Created", "unknown")),
                    "size_mb": round(image.attrs.get("Size", 0) / (1024 * 1024), 2)
                })
            except docker.errors.ImageNotFound:
                missing_images.append(image_name)
        
        message = "Docker is available."
        if missing_images:
            message += f" Missing {len(missing_images)} image(s). Run /docker/pull to download them."
        else:
            message += " All required images are available."
        
        return DockerStatusResponse(
            docker_available=True,
            images=available_images,
            missing_images=missing_images,
            message=message
        )
    except Exception as e:
        return DockerStatusResponse(
            docker_available=False,
            images=[],
            missing_images=REQUIRED_DOCKER_IMAGES,
            message=f"Docker is not available: {str(e)}. Please start Docker Desktop."
        )


@router.post("/docker/pull")
async def pull_docker_images(background_tasks: BackgroundTasks):
    """
    Pull all required Docker images for the pipeline.
    
    This downloads:
    - maven:3.9.8-amazoncorretto-17 (~500MB) - For Maven compilation
    - ghcr.io/lukvonstrom/multilspy-java-docker:latest (~1GB) - For LSP analysis
    
    Note: This may take several minutes depending on your internet connection.
    """
    if not settings.LOCAL_MODE:
        raise HTTPException(
            status_code=400,
            detail="This endpoint is only available in LOCAL_MODE"
        )
    
    try:
        import docker
        client = docker.from_env()
        client.ping()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Docker is not available: {str(e)}. Please start Docker Desktop."
        )
    
    results = []
    for image_name in REQUIRED_DOCKER_IMAGES:
        try:
            logger.info(f"[Docker] Pulling image: {image_name}...")
            image = client.images.pull(image_name)
            results.append({
                "image": image_name,
                "status": "pulled",
                "id": image.short_id
            })
            logger.info(f"[Docker] Successfully pulled: {image_name}")
        except Exception as e:
            results.append({
                "image": image_name,
                "status": "failed",
                "error": str(e)
            })
            logger.error(f"[Docker] Failed to pull {image_name}: {e}")
    
    success_count = sum(1 for r in results if r["status"] == "pulled")
    return {
        "success": success_count == len(REQUIRED_DOCKER_IMAGES),
        "message": f"Pulled {success_count}/{len(REQUIRED_DOCKER_IMAGES)} images",
        "results": results
    }


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
    
    # ========================================
    # DOCKER-BASED COMPILATION (Step 1)
    # ========================================
    # Using Docker ensures all dependencies are properly resolved
    # regardless of the local system's Java/Maven installation
    initial_errors = request.initial_errors
    if not initial_errors:
        logger.info(f"[Docker] Compiling {repo_name} in Docker container (maven:3.9.8-amazoncorretto-17)...")
        try:
            # Ensure Docker is available
            try:
                import docker
                client = docker.from_env()
                client.ping()
            except Exception as docker_err:
                raise HTTPException(
                    status_code=503,
                    detail=f"Docker is not available. Please ensure Docker Desktop is running. Error: {str(docker_err)}"
                )
            
            # Use MavenReproducerAgent which handles Docker container lifecycle
            maven_agent = MavenReproducerAgent(Path(repo_path))
            
            # Pull the Docker image if not available (first run)
            logger.info(f"[Docker] Ensuring Maven Docker image is available...")
            maven_agent.dockerAgent.pull_image()
            
            with maven_agent.start_container() as container:
                logger.info(f"[Docker] Container started, running mvn clean compile...")
                (compile_ok, test_ok), error_text, _ = maven_agent.compile_maven(
                    diffs=[],
                    run_tests=False,
                    timeout=300
                )
            
            if not compile_ok:
                initial_errors = error_text
                # Clean up the error text to remove Docker-specific paths
                initial_errors = initial_errors.replace("/mnt/repo/", "")
                logger.info(f"[Docker] Compilation failed - detected errors ({len(initial_errors)} chars)")
            else:
                logger.info("[Docker] Project compiles successfully - no errors to fix")
                return {
                    "success": True,
                    "repository": repo_name,
                    "message": "Project compiles successfully in Docker, no fixes needed"
                }
        except DockerError as e:
            logger.error(f"[Docker] Docker error during compilation: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Docker compilation failed: {str(e)}. Ensure Docker Desktop is running."
            )
        except HTTPException:
            raise  # Re-raise HTTP exceptions as-is
        except Exception as e:
            logger.error(f"[Docker] Error during initial compilation: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to compile project in Docker: {str(e)}")

    # Initialize pipeline logger early so it can be used by API change analysis
    pipeline_logger = PipelineLogger(repo_name)
    pipeline_logger.log_stage("docker_compilation_complete", {
        "has_errors": bool(initial_errors),
        "error_length": len(initial_errors) if initial_errors else 0
    })

    # ========================================
    # API CHANGES ANALYSIS (Step 2)
    # ========================================
    # Generate API changes from dependency diff (REVAPI/JApiCmp)
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
        
        return {
            "success": result.get("success", False),
            "repository": repo_name,
            "commit": commit_hash,
            "method": "llm_agent",
            "result": result
        }
    
    except Exception as e:
        logger.error(f"Error processing repository {repo_name}: {e}")
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


class CompileRequest(BaseModel):
    repo_name: str
    run_tests: bool = False
    timeout: int = 300


class CompileResponse(BaseModel):
    success: bool
    compilation_succeeded: bool
    test_succeeded: bool
    error_text: str
    docker_image: str


@router.post("/compile/{repo_name}", response_model=CompileResponse)
async def compile_in_docker(repo_name: str, run_tests: bool = False, timeout: int = 300):
    """
    Compile a repository using Docker (maven:3.9.8-amazoncorretto-17).
    
    This ensures proper dependency resolution regardless of local system configuration.
    
    Path parameter:
    - repo_name: Name of the repository directory
    
    Query parameters:
    - run_tests: Whether to run tests (default: false)
    - timeout: Compilation timeout in seconds (default: 300)
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
    
    if not local_repo_service.check_pom_exists(repo_name):
        raise HTTPException(
            status_code=400,
            detail=f"Repository '{repo_name}' does not contain pom.xml"
        )
    
    try:
        # Check Docker availability
        import docker
        client = docker.from_env()
        client.ping()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Docker is not available: {str(e)}. Please start Docker Desktop."
        )
    
    try:
        logger.info(f"[Docker] Starting compilation for {repo_name}...")
        maven_agent = MavenReproducerAgent(Path(repo_path))
        
        with maven_agent.start_container() as container:
            (compile_ok, test_ok), error_text, _ = maven_agent.compile_maven(
                diffs=[],
                run_tests=run_tests,
                timeout=timeout
            )
        
        # Clean up Docker paths from error text
        error_text = error_text.replace("/mnt/repo/", "")
        
        return CompileResponse(
            success=compile_ok and (test_ok if run_tests else True),
            compilation_succeeded=compile_ok,
            test_succeeded=test_ok,
            error_text=error_text if not compile_ok or (run_tests and not test_ok) else "",
            docker_image="maven:3.9.8-amazoncorretto-17"
        )
    except DockerError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Docker error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"[Docker] Compilation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class LSPValidateRequest(BaseModel):
    repo_name: str
    file_path: str
    diff: str = ""


@router.post("/lsp/validate")
async def validate_with_lsp(request: LSPValidateRequest):
    """
    Validate a file using the Java Language Server in Docker.
    
    Uses the ghcr.io/lukvonstrom/multilspy-java-docker:latest image to provide
    accurate Java diagnostics regardless of local system configuration.
    
    Request body:
    - repo_name: Name of the repository
    - file_path: Path to the Java file (relative to repo root)
    - diff: Optional diff to validate (if empty, validates current file state)
    """
    if not settings.LOCAL_MODE:
        raise HTTPException(
            status_code=400,
            detail="This endpoint is only available in LOCAL_MODE"
        )
    
    repo_path = local_repo_service.get_repository_path(request.repo_name)
    if not repo_path:
        raise HTTPException(
            status_code=404,
            detail=f"Repository '{request.repo_name}' not found"
        )
    
    try:
        # Check Docker availability
        import docker
        client = docker.from_env()
        client.ping()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Docker is not available: {str(e)}. Please start Docker Desktop."
        )
    
    try:
        logger.info(f"[Docker] Starting LSP validation for {request.file_path}...")
        lsp_agent = LSPAgent(Path(repo_path))
        
        with lsp_agent.start_container() as container:
            if request.diff:
                # Validate with changes
                initial_results, edit_results = lsp_agent.validate_changes(
                    Path(request.file_path),
                    [request.diff]
                )
                
                # Process diagnostics to find new issues introduced by the diff
                def diagnostic_stringifier(diagnostic):
                    message = diagnostic.get("message", "").replace("/mnt/repo/", "")
                    start_line = diagnostic["range"]["start"].get("line", 0)
                    return f"Line {start_line}: {message}"
                
                initial_set = set(diagnostic_stringifier(d) for d in initial_results.get("diagnostics", []))
                edit_set = set(diagnostic_stringifier(d) for d in edit_results.get("diagnostics", []))
                new_issues = list(edit_set - initial_set)
                
                return {
                    "success": len(new_issues) == 0,
                    "file_path": request.file_path,
                    "initial_diagnostics_count": len(initial_results.get("diagnostics", [])),
                    "edit_diagnostics_count": len(edit_results.get("diagnostics", [])),
                    "new_issues": new_issues,
                    "docker_image": "ghcr.io/lukvonstrom/multilspy-java-docker:latest"
                }
            else:
                # Validate current state
                results = lsp_agent.validate_file(Path(request.file_path))
                diagnostics = results.get("diagnostics", [])
                
                return {
                    "success": True,
                    "file_path": request.file_path,
                    "diagnostics_count": len(diagnostics),
                    "diagnostics": [
                        {
                            "line": d["range"]["start"].get("line", 0),
                            "message": d.get("message", "").replace("/mnt/repo/", ""),
                            "severity": d.get("severity", "unknown")
                        }
                        for d in diagnostics
                    ],
                    "docker_image": "ghcr.io/lukvonstrom/multilspy-java-docker:latest"
                }
    except DockerError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Docker error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"[Docker] LSP validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))