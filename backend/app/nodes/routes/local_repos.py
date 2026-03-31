"""
Local Repositories API Routes.

This module provides FastAPI endpoints for managing and processing local Java
(Maven) repositories. It includes functionality for cloning repositories,
listing available local workspaces, extracting metadata, and executing a full
migration pipeline using AI agents (Planning, Recipe, and LLM-based agents).

Typical usage involves cloning a repository via `/clone` and then triggering
the migration pipeline via `/process/{repo_name}`.
"""

import subprocess
import traceback
from pathlib import Path
from typing import Any, Final, NamedTuple

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel

from app.chains.planning_service import PlanningAgentService
from app.nodes.service import JavaMigrationAgentService
from app.config.config import settings
from app.tools.agents.JapiCmpAgent import JapiCmpAgent
from app.tools.agents.MavenReproducerAgent import MavenReproducerAgent
from app.graph.recipe_orchestrator import RecipeOrchestrator
from app.retrievers.local_repository_service import local_repo_service
from app.utilities.logger import logger
from app.utilities.pipeline_logger import PipelineLogger

__all__ = [
    "router",
    "CloneRepositoryRequest",
    "ProcessRepositoryRequest",
    "RepositoryResponse",
    "list_local_repositories",
    "clone_repository",
    "process_repository",
    "get_repository_info",
]

# --- Constants ---
LOCAL_MODE_ERROR: Final[str] = "This endpoint is only available in LOCAL_MODE"
DEFAULT_COMMIT: Final[str] = "local"
PLANNING_PROVIDER: Final[str] = "gpt-oss-120"
MAVEN_TIMEOUT_SEC: Final[int] = 300
RECIPE_AGENT_METHOD: Final[str] = "recipe_agent"
LLM_AGENT_METHOD: Final[str] = "llm_agent"

router = APIRouter()


# --- Models ---
class CloneRepositoryRequest(BaseModel):
    """
    Request payload for cloning a remote repository.

    Attributes:
        git_url: The GitHub repository URL.
        target_name: An optional custom directory name for the clone.
    """
    git_url: str
    target_name: str | None = None


class ProcessRepositoryRequest(BaseModel):
    """
    Request payload for processing a local Java repository.

    Attributes:
        repo_name: The name of the local repository directory.
        pom_diff: Optional specific pom.xml changes to analyze.
        initial_errors: Optional initial Maven compilation errors.
    """
    repo_name: str
    pom_diff: str | None = ""
    initial_errors: str | None = ""


class RepositoryResponse(BaseModel):
    """
    Response model detailing local repository information.

    Attributes:
        name: The name of the repository directory.
        path: Absolute or relative path to the repository.
        has_pom: True if a pom.xml exists at the root.
        is_git: True if it is a valid Git repository.
        git_info: Additional Git metadata, if available.
    """
    name: str
    path: str
    has_pom: bool
    is_git: bool
    git_info: dict[str, Any] | None = None


class CompilationResult(NamedTuple):
    """Internal struct representing the result of a Maven compilation check."""
    needs_fixes: bool
    errors: str


def _sanitize_initial_errors(raw_errors: str) -> str:
    """
    Keep only Maven error-relevant lines and remove [INFO] / noise lines.

    Preserves [ERROR] lines and their indented continuation details (e.g. symbol/location).
    """
    if not raw_errors:
        return ""

    cleaned_lines: list[str] = []
    previous_was_error = False

    for raw_line in raw_errors.splitlines():
        line = raw_line.rstrip("\r")
        stripped = line.strip()

        if not stripped:
            if previous_was_error:
                cleaned_lines.append("")
            continue

        if stripped.startswith("[INFO]"):
            previous_was_error = False
            continue

        if stripped.startswith("[ERROR]"):
            cleaned_lines.append(line)
            previous_was_error = True
            continue

        if previous_was_error and (line.startswith(" ") or line.startswith("\t")):
            cleaned_lines.append(line)
            continue

        if previous_was_error and (
            stripped.startswith("symbol:")
            or stripped.startswith("location:")
            or stripped.startswith("-> [Help")
            or stripped.startswith("For more information")
        ):
            cleaned_lines.append(line)
            continue

        previous_was_error = False

    return "\n".join(cleaned_lines).replace("/mnt/repo/", "").strip()


# --- Helper Functions ---
def _require_local_mode() -> None:
    """
    Enforces that the application is running in LOCAL_MODE.

    Raises:
        HTTPException: If `settings.LOCAL_MODE` is False (HTTP 400).
    """
    if not settings.LOCAL_MODE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=LOCAL_MODE_ERROR,
        )


def _run_git_command(cwd: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """
    Executes a Git command within a specific directory.

    Args:
        cwd: The working directory for the Git command.
        args: A list of string arguments for the Git CLI.

    Returns:
        The CompletedProcess instance containing stdout, stderr, and returncode.
    """
    cmd = ["git", *args]
    logger.info(f"[GIT] Command: {' '.join(cmd)}")
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, check=False
    )
    logger.info(f"[GIT] Return code: {result.returncode}")
    if result.stdout:
        logger.info(f"[GIT] Output length: {len(result.stdout)} chars")
    if result.stderr:
        logger.info(f"[GIT] Stderr: {result.stderr}")
    return result


def _detect_pom_diff(repo_path: Path) -> str:
    """
    Attempts to detect recent changes to any pom.xml files via Git history.

    Args:
        repo_path: The root path of the local repository.

    Returns:
        A string containing the Git diff of pom.xml changes, or an empty string
        if no changes were detected or an error occurred.
    """
    try:
        logger.info(f"[GIT] Searching for pom.xml files in {repo_path}")
        find_result = _run_git_command(repo_path, ["ls-files", "*pom.xml"])
        pom_files = [f.strip() for f in find_result.stdout.split("\n") if f.strip()]

        if not pom_files:
            logger.warning("[GIT] No pom.xml files found in git repo")
            return ""

        logger.info(f"[GIT] Found {len(pom_files)} pom.xml file(s): {pom_files}")

        # Strategy 1: diff against HEAD~1
        res = _run_git_command(repo_path, ["diff", "HEAD~1", "HEAD", "--", *pom_files])
        if res.returncode == 0 and res.stdout:
            logger.info("[GIT] ✓ Detected pom.xml changes from git diff (HEAD~1 vs HEAD)")
            return res.stdout

        # Strategy 2: uncommitted changes against HEAD
        logger.info("[GIT] ✗ No diff between HEAD~1 and HEAD, trying uncommitted changes...")
        res = _run_git_command(repo_path, ["diff", "HEAD", "--", *pom_files])
        if res.returncode == 0 and res.stdout:
            logger.info("[GIT] ✓ Detected uncommitted pom.xml changes")
            return res.stdout

        # Strategy 3: check log for last modification
        logger.info("[GIT] ✗ No changes detected, checking git log for pom.xml modifications...")
        res = _run_git_command(repo_path, ["log", "--pretty=format:%H", "-n", "1", "--", *pom_files])
        if res.returncode == 0 and res.stdout:
            last_commit = res.stdout.strip()
            logger.info(f"[GIT] ✓ Found pom.xml last modified in commit: {last_commit[:7]}")
            
            res_show = _run_git_command(
                repo_path, ["show", f"{last_commit}^..{last_commit}", "--", *pom_files]
            )
            if res_show.returncode == 0 and res_show.stdout:
                logger.info("[GIT] ✓ Got pom.xml changes from history")
                return res_show.stdout

        logger.warning("[GIT] ✗ Could not find any pom.xml changes")
        return ""

    except subprocess.SubprocessError as e:
        logger.warning(f"[GIT] Subprocess error during pom.xml detection: {e}")
        return ""
    except Exception as e:
        logger.warning(f"[GIT] Exception during pom.xml detection: {e}\n{traceback.format_exc()}")
        return ""


def _get_initial_errors_from_docker(repo_path: Path, repo_name: str) -> CompilationResult:
    """
    Compiles the Maven project inside a Docker container to retrieve baseline errors.

    Args:
        repo_path: Path to the local repository.
        repo_name: The name of the repository.

    Returns:
        CompilationResult containing boolean `needs_fixes` and the errors text.

    Raises:
        HTTPException: If the Docker compilation crashes.
    """
    logger.info(f"Compiling {repo_name} in Docker to get initial errors...")
    try:
        maven_agent = MavenReproducerAgent(repo_path)
        with maven_agent.start_container():
            (compile_ok, test_ok), error_text, _ = maven_agent.compile_maven(
                diffs=[],
                run_tests=False,
                timeout=MAVEN_TIMEOUT_SEC,
                collect_all_errors=True,
                errors_only=True,
                initial_error_scan=True,
            )
        error_text = _sanitize_initial_errors(error_text)

        if not compile_ok:
            logger.info(f"Compilation failed - detected errors ({len(error_text)} chars)")
            return CompilationResult(needs_fixes=True, errors=error_text)

        if not test_ok:
            logger.info(f"Tests failed - detected errors ({len(error_text)} chars)")
            return CompilationResult(needs_fixes=True, errors=error_text)

        logger.info("Project compiles and tests successfully - no errors to fix")
        return CompilationResult(needs_fixes=False, errors="")

    except Exception as e:
        logger.error(f"Error during initial compilation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile project: {e}"
        )


def _generate_api_changes(
    repo_path: Path,
    pom_diff: str,
    initial_errors: str,
    pipeline_logger: PipelineLogger
) -> str:
    """
    Generates API changes mapping by running the JapiCmp tool.

    Args:
        repo_path: Path to the local repository.
        pom_diff: The detected diff in pom.xml files.
        initial_errors: The compilation errors to filter relevant API changes.
        pipeline_logger: Active logger to record process metrics.

    Returns:
        Filtered API changes text. Empty string if tool fails or no changes found.
    """
    if not pom_diff:
        return ""

    try:
        api_change_agent = JapiCmpAgent(pipeline_logger=pipeline_logger)
        api_result = api_change_agent.generate_api_changes_with_raw(
            repo_path=str(repo_path),
            pom_diff=pom_diff,
            compilation_errors=initial_errors,
        )

        raw_changes = api_result.get("raw", "")
        if raw_changes:
            logger.info(f"[REVAPI] Full raw API changes ({len(raw_changes)} chars):")
            logger.info(raw_changes[:500])

        filtered_changes = api_result.get("filtered", "")
        if filtered_changes:
            logger.info(f"Generated API changes ({len(filtered_changes)} chars)")
        else:
            logger.info("No API changes generated (tool not configured or no changes found)")
        
        return filtered_changes

    except Exception as e:
        logger.warning(f"API change analysis failed: {e}")
        return ""


def _create_migration_plan(
    repo_path: Path,
    commit_hash: str,
    repo_slug: str,
    pom_diff: str,
    initial_errors: str,
    api_changes_text: str,
    pipeline_logger: PipelineLogger,
) -> str:
    """
    Uses the Planning Agent to generate a migration strategy.

    Args:
        repo_path: Path to the repository.
        commit_hash: Current Git commit SHA.
        repo_slug: Repository directory name.
        pom_diff: Diff of the pom.xml file.
        initial_errors: Output of initial failed compilation.
        api_changes_text: Extracted JapiCmp API diffs.
        pipeline_logger: Pipeline logger to store the plan text file.

    Returns:
        The generated migration plan string, or an empty string on failure.
    """
    if not initial_errors:
        return ""

    logger.info(f"[PlanningAgent] Generating migration plan for {repo_slug}")
    try:
        planning_service = PlanningAgentService(provider=PLANNING_PROVIDER)
        plan_result = planning_service.create_plan(
            repo_path=str(repo_path),
            commit_hash=commit_hash,
            repo_slug=repo_slug,
            pom_diff=pom_diff,
            initial_errors=initial_errors,
            api_changes_text=api_changes_text,
            pipeline_logger=pipeline_logger,
        )
        
        if plan_result and plan_result.get("success"):
            migration_plan = plan_result.get("plan", "")
            logger.info(f"[PlanningAgent] Migration plan ready ({len(migration_plan)} chars)")

            pipeline_logger.log_stage("planning_agent_output", {
                "migration_plan": migration_plan,
                "plan_length": len(migration_plan),
            })

            plan_text_path = pipeline_logger.log_dir / "01_migration_plan.txt"
            plan_text_path.write_text(migration_plan, encoding="utf-8")
            logger.info(f"[PlanningAgent] Migration plan saved to {plan_text_path}")
            return migration_plan
        
        logger.warning(
            f"[PlanningAgent] Planning failed: {plan_result.get('error')}, continuing without plan"
        )
    except Exception as e:
        logger.warning(f"[PlanningAgent] Planning agent error: {e}, continuing without plan")
    
    return ""


def _apply_recipe_agent(
    repo_path: Path,
    pom_diff: str,
    migration_plan: str,
    commit_hash: str,
    repo_name: str,
    pipeline_logger: PipelineLogger,
) -> dict[str, Any] | None:
    """
    Attempts to fix the code using deterministic recipes via RecipeOrchestrator.

    Args:
        repo_path: Path to the repository.
        pom_diff: Contextual pom diff.
        migration_plan: Guided plan from the Planning Agent.
        commit_hash: Current commit SHA.
        repo_name: Repository directory name.
        pipeline_logger: The active pipeline logger.

    Returns:
        A dictionary containing the successful recipe result, or None if failed/skipped.
    """
    logger.info(f"[RecipeAgent] Attempting recipe-based fix for {repo_name}")
    
    pipeline_logger.log_stage("recipe_agent_input", {
        "pom_diff": pom_diff,
        "migration_plan": migration_plan,
        "commit_sha": commit_hash,
        "repo_slug": repo_name,
    })
    
    recipe_input_dir = pipeline_logger.log_dir / "recipe_agent_input"
    recipe_input_dir.mkdir(exist_ok=True)
    if pom_diff:
        (recipe_input_dir / "pom_diff.txt").write_text(pom_diff, encoding="utf-8")
    if migration_plan:
        (recipe_input_dir / "migration_plan.txt").write_text(migration_plan, encoding="utf-8")
        
    logger.info(f"[RecipeAgent] Input logged at {recipe_input_dir}")
    
    try:
        orchestrator = RecipeOrchestrator(
            settings.GROQ_API_KEY, pipeline_logger=pipeline_logger
        )
        recipe_result = orchestrator.process_breaking_change(
            repo_path=str(repo_path),
            pom_diff=pom_diff,
            migration_plan=migration_plan,
            commit_sha=commit_hash,
            repo_slug=repo_name,
        )
        
        if recipe_result and recipe_result.get("success"):
            logger.info(f"[RecipeAgent] Successfully fixed using recipes for {repo_name}")
            return recipe_result
            
        logger.info("[RecipeAgent] Recipe fix not applicable, falling back to LLM agent")
    except Exception as e:
        logger.warning(f"[RecipeAgent] Recipe agent failed: {e}, falling back to LLM agent")
    
    return None


def _apply_llm_agent(
    repo_path: Path,
    pom_diff: str,
    migration_plan: str,
    commit_hash: str,
    repo_name: str,
    pipeline_logger: PipelineLogger,
) -> dict[str, Any]:
    """
    Applies the generative LLM Agent as the primary fix or fallback mechanism.

    Args:
        repo_path: Path to the repository.
        pom_diff: Contextual pom diff.
        migration_plan: Guided plan from the Planning Agent.
        commit_hash: Current commit SHA.
        repo_name: Repository directory name.
        pipeline_logger: The active pipeline logger.

    Returns:
        A dictionary containing the agent's processing result.
    """
    agent_service = JavaMigrationAgentService()

    pipeline_logger.log_stage("llm_agent_input", {
        "pom_diff": pom_diff,
        "migration_plan": migration_plan,
        "commit_hash": commit_hash,
        "repo_slug": repo_name,
    })
    
    llm_input_dir = pipeline_logger.log_dir / "llm_agent_input"
    llm_input_dir.mkdir(exist_ok=True)
    if pom_diff:
        (llm_input_dir / "pom_diff.txt").write_text(pom_diff, encoding="utf-8")
    if migration_plan:
        (llm_input_dir / "migration_plan.txt").write_text(migration_plan, encoding="utf-8")
        
    logger.info(f"[LLM Agent] Input logged at {llm_input_dir}")
    logger.info(f"Starting agent processing for {repo_name}")

    return agent_service.process_repository(
        repo_path=str(repo_path),
        commit_hash=commit_hash,
        repo_slug=repo_name,
        pom_diff=pom_diff,
        migration_plan=migration_plan,
        pipeline_logger=pipeline_logger,
    )


# --- API Routes ---
@router.get("/list", response_model=list[RepositoryResponse])
async def list_local_repositories() -> list[dict[str, Any]]:
    """
    List all local Java (Maven) repositories in the workspace.
    
    Only includes directories with `pom.xml` files.

    Returns:
        A list of repository details matching the RepositoryResponse model.

    Raises:
        HTTPException: If the server is not in LOCAL_MODE (400) or fails to read dirs (500).
    """
    _require_local_mode()
    
    try:
        return local_repo_service.list_local_repositories()
    except Exception as e:
        logger.error(f"Error listing repositories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/clone")
async def clone_repository(request: CloneRepositoryRequest) -> dict[str, Any]:
    """
    Clone a repository from GitHub to the local workspace.

    Args:
        request: The payload containing the git_url and optional target_name.

    Returns:
        A dictionary containing success status, message, path, and pom metadata.

    Raises:
        HTTPException: If not in LOCAL_MODE (400) or cloning fails (500).
    """
    _require_local_mode()
    
    try:
        repo_path = local_repo_service.clone_repository(
            git_url=request.git_url,
            target_name=request.target_name
        )
        
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(e)
        )


@router.post("/process/{repo_name}")
async def process_repository(
    repo_name: str,
    request: ProcessRepositoryRequest,
    background_tasks: BackgroundTasks
) -> dict[str, Any]:
    """
    Process a local repository utilizing the Java migration agent pipeline.

    Args:
        repo_name: The target repository directory name in the workspace.
        request: Process parameters (pom modifications, error logs).
        background_tasks: FastAPI background tasks dependency.

    Returns:
        A dictionary containing the success flag, the applied method, and detailed
        execution results.

    Raises:
        HTTPException: 400 if not LOCAL_MODE or missing pom.xml.
        HTTPException: 404 if the repo is not found.
        HTTPException: 500 if the process critically fails.
    """
    _require_local_mode()
    
    repo_path = local_repo_service.get_repository_path(repo_name)
    if not repo_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repo_name}' not found in workspace"
        )
    
    if not local_repo_service.check_pom_exists(repo_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository '{repo_name}' does not contain pom.xml"
        )
    
    git_info = local_repo_service._get_git_info(repo_path)
    commit_hash = git_info.get("commit", DEFAULT_COMMIT) if git_info else DEFAULT_COMMIT
    
    # 1. Diff Detection
    pom_diff = request.pom_diff or _detect_pom_diff(repo_path)
    logger.info(f"[GIT] Final result: pom_diff length = {len(pom_diff)} chars")
    
    # 2. Baseline Docker Compilation
    initial_errors = _sanitize_initial_errors(request.initial_errors or "")
    if not initial_errors:
        comp_result = _get_initial_errors_from_docker(repo_path, repo_name)
        if not comp_result.needs_fixes:
            return {
                "success": True,
                "repository": repo_name,
                "message": "Project compiles and tests successfully, no fixes needed"
            }
        initial_errors = comp_result.errors

    # 3. Pipeline Initialization
    pipeline_logger = PipelineLogger(repo_name)
    pipeline_logger.log_input(
        pom_diff=pom_diff,
        initial_errors=initial_errors,
        repo_path=str(repo_path),
        commit_hash=commit_hash
    )

    # 4. Agent Execution Flow
    try:
        # 4a. JApiCmp / API Changes
        api_changes_text = _generate_api_changes(
            repo_path=repo_path,
            pom_diff=pom_diff,
            initial_errors=initial_errors,
            pipeline_logger=pipeline_logger,
        )

        # 4b. Planning
        migration_plan = _create_migration_plan(
            repo_path=repo_path,
            commit_hash=commit_hash,
            repo_slug=repo_name,
            pom_diff=pom_diff,
            initial_errors=initial_errors,
            api_changes_text=api_changes_text,
            pipeline_logger=pipeline_logger,
        )

        # 4c. Recipe Execution
        if initial_errors:
            recipe_result = _apply_recipe_agent(
                repo_path=repo_path,
                pom_diff=pom_diff,
                migration_plan=migration_plan,
                commit_hash=commit_hash,
                repo_name=repo_name,
                pipeline_logger=pipeline_logger,
            )
            
            if recipe_result:
                pipeline_logger.log_final_result(True, recipe_result)
                pipeline_logger.finalize()
                return {
                    "success": True,
                    "repository": repo_name,
                    "commit": commit_hash,
                    "method": RECIPE_AGENT_METHOD,
                    "recipes_applied": recipe_result.get("recipes_applied", []),
                    "result": recipe_result
                }

        # # 4d. LLM Fallback / Primary Engine
        # llm_result = _apply_llm_agent(
        #     repo_path=repo_path,
        #     pom_diff=pom_diff,
        #     migration_plan=migration_plan,
        #     commit_hash=commit_hash,
        #     repo_name=repo_name,
        #     pipeline_logger=pipeline_logger,
        # )

        # pipeline_logger.log_final_result(llm_result.get("success", False), llm_result)
        # pipeline_logger.finalize()
        
        # return {
        #     "success": llm_result.get("success", False),
        #     "repository": repo_name,
        #     "commit": commit_hash,
        #     "method": LLM_AGENT_METHOD,
        #     "result": llm_result
        # }

    except Exception as e:
        logger.error(f"Error processing repository {repo_name}: {e}")
        try:
            pipeline_logger.log_error("process_error", str(e), traceback.format_exc())
            pipeline_logger.finalize()
        except Exception:
            pass  # Suppress secondary logging errors to ensure primary exception surfaces
            
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/info/{repo_name}")
async def get_repository_info(repo_name: str) -> dict[str, Any]:
    """
    Get detailed Git and path information about a local repository.

    Args:
        repo_name: Name of the repository directory.

    Returns:
        A dictionary containing path, pom, and Git metadata.

    Raises:
        HTTPException: If not in LOCAL_MODE (400) or repo is not found (404).
    """
    _require_local_mode()
    
    repo_path = local_repo_service.get_repository_path(repo_name)
    if not repo_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
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