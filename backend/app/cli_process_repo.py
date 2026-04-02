"""
CLI entrypoint for processing a local repository through the migration pipeline.

Usage examples:
    python -m app.cli_process_repo my-repo
    python -m app.cli_process_repo my-repo --pom-diff-file .\\pom.diff
    python -m app.cli_process_repo my-repo --initial-errors-file .\\errors.txt
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Allow running from either backend root or backend/app by ensuring the
# package root (backend) is importable as 'app'.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if Path.cwd() != BACKEND_ROOT:
    os.chdir(BACKEND_ROOT)

try:
    from app.retrievers.local_repository_service import local_repo_service
    from app.utilities.logger import logger
    from app.utilities.pipeline_logger import PipelineLogger
except ModuleNotFoundError:
    from retrievers.local_repository_service import local_repo_service
    from utilities.logger import logger
    from utilities.pipeline_logger import PipelineLogger


def _read_optional_file(path_value: str | None) -> str:
    if not path_value:
        return ""
    path = Path(path_value)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_text(encoding="utf-8")


def process_repository(
    repo_name: str,
    pom_diff: str = "",
    initial_errors: str = "",
) -> dict[str, Any]:
    """Run the local repository migration pipeline and return the result payload."""
    try:
        from app.nodes.routes.local_repos import (
            DEFAULT_COMMIT,
            LLM_AGENT_METHOD,
            RECIPE_AGENT_METHOD,
            _apply_llm_agent,
            _apply_recipe_agent,
            _create_migration_plan,
            _detect_pom_diff,
            _generate_api_changes,
            _get_initial_errors_from_docker,
            _sanitize_initial_errors,
        )
    except ModuleNotFoundError:
        from nodes.routes.local_repos import (
            DEFAULT_COMMIT,
            LLM_AGENT_METHOD,
            RECIPE_AGENT_METHOD,
            _apply_llm_agent,
            _apply_recipe_agent,
            _create_migration_plan,
            _detect_pom_diff,
            _generate_api_changes,
            _get_initial_errors_from_docker,
            _sanitize_initial_errors,
        )

    repo_path = local_repo_service.get_repository_path(repo_name)
    if not repo_path:
        raise FileNotFoundError(f"Repository '{repo_name}' not found in workspace")

    if not local_repo_service.check_pom_exists(repo_name):
        raise ValueError(f"Repository '{repo_name}' does not contain pom.xml")

    git_info = local_repo_service._get_git_info(repo_path)
    commit_hash = git_info.get("commit", DEFAULT_COMMIT) if git_info else DEFAULT_COMMIT

    pom_diff_text = pom_diff or _detect_pom_diff(repo_path)
    logger.info(f"[GIT] Final result: pom_diff length = {len(pom_diff_text)} chars")

    sanitized_errors = _sanitize_initial_errors(initial_errors or "")
    if not sanitized_errors:
        comp_result = _get_initial_errors_from_docker(repo_path, repo_name)
        if not comp_result.needs_fixes:
            return {
                "success": True,
                "repository": repo_name,
                "message": "Project compiles and tests successfully, no fixes needed",
            }
        sanitized_errors = comp_result.errors

    pipeline_logger = PipelineLogger(repo_name)
    pipeline_logger.log_input(
        pom_diff=pom_diff_text,
        initial_errors=sanitized_errors,
        repo_path=str(repo_path),
        commit_hash=commit_hash,
    )

    try:
        api_changes_text = _generate_api_changes(
            repo_path=repo_path,
            pom_diff=pom_diff_text,
            initial_errors=sanitized_errors,
            pipeline_logger=pipeline_logger,
        )

        migration_plan = _create_migration_plan(
            repo_path=repo_path,
            commit_hash=commit_hash,
            repo_slug=repo_name,
            pom_diff=pom_diff_text,
            initial_errors=sanitized_errors,
            api_changes_text=api_changes_text,
            pipeline_logger=pipeline_logger,
        )

        if sanitized_errors:
            recipe_result = _apply_recipe_agent(
                repo_path=repo_path,
                pom_diff=pom_diff_text,
                migration_plan=migration_plan,
                commit_hash=commit_hash,
                repo_name=repo_name,
                pipeline_logger=pipeline_logger,
            )
            if recipe_result:
                pipeline_logger.log_final_result(
                    True,
                    recipe_result,
                    agent_method=RECIPE_AGENT_METHOD,
                )
                pipeline_logger.finalize()
                return {
                    "success": True,
                    "repository": repo_name,
                    "commit": commit_hash,
                    "method": RECIPE_AGENT_METHOD,
                    "recipes_applied": recipe_result.get("recipes_applied", []),
                    "result": recipe_result,
                }

        llm_result = _apply_llm_agent(
            repo_path=repo_path,
            pom_diff=pom_diff_text,
            initial_errors=sanitized_errors,
            migration_plan=migration_plan,
            commit_hash=commit_hash,
            repo_name=repo_name,
            pipeline_logger=pipeline_logger,
        )

        pipeline_logger.log_final_result(
            llm_result.get("success", False),
            llm_result,
            agent_method=LLM_AGENT_METHOD,
        )
        pipeline_logger.finalize()

        return {
            "success": llm_result.get("success", False),
            "repository": repo_name,
            "commit": commit_hash,
            "method": LLM_AGENT_METHOD,
            "result": llm_result,
        }

    except Exception:
        try:
            pipeline_logger.finalize()
        except Exception:
            pass
        raise


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Process a local Maven repository via the migration pipeline.",
    )
    parser.add_argument("repo_name", help="Local repository directory name")
    parser.add_argument(
        "--pom-diff",
        default="",
        help="Optional raw pom diff text",
    )
    parser.add_argument(
        "--pom-diff-file",
        default="",
        help="Optional file path containing pom diff text",
    )
    parser.add_argument(
        "--initial-errors",
        default="",
        help="Optional raw Maven error text",
    )
    parser.add_argument(
        "--initial-errors-file",
        default="",
        help="Optional file path containing Maven error text",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        pom_diff_from_file = _read_optional_file(args.pom_diff_file)
        initial_errors_from_file = _read_optional_file(args.initial_errors_file)

        result = process_repository(
            repo_name=args.repo_name,
            pom_diff=args.pom_diff or pom_diff_from_file,
            initial_errors=args.initial_errors or initial_errors_from_file,
        )
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0 if result.get("success") else 1

    except Exception as exc:
        logger.exception("CLI process_repository failed")
        print(
            json.dumps(
                {
                    "success": False,
                    "error": str(exc),
                    "repository": args.repo_name,
                },
                indent=2,
                ensure_ascii=True,
            )
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
