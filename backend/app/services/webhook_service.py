from app.database.mongodb import get_database
from app.models.user import User
from app.models.repository import Repository
from app.models.change import Change, FixStatus
from datetime import datetime
from app.repositories.user_repository import user_repo
from app.repositories.repo_repository import repository_repo
from app.repositories.change_repository import change_repo
from app.services.github_service import github_service
from app.utils.logger import logger
import asyncio

# Flag to enable/disable recipe-based agent (set to True to use recipes first)
USE_RECIPE_AGENT = True

class WebhookService:

    async def process_webhook(self,repo_data, owner_data, commit_with_pom, installation_id):

        user = User(
            github_id=str(owner_data.get("id")),
            username=owner_data.get("login"),
            avatar_url=owner_data.get("avatar_url"),
            email=None,  # Not available in webhook
            repositories=[]
                    )
        
        user_id = await user_repo.create_or_update(user)

        
        repository = Repository(
            github_repo_id=str(repo_data.get("id")),
            name=repo_data.get("name"),
            full_name=repo_data.get("full_name"),
            owner=owner_data.get("login"),
            owner_id=str(owner_data.get("id")),
            installation_id=installation_id,
            is_active=True,
            last_commit_sha=commit_with_pom.get("id"),
            last_pom_change=datetime.utcnow()
        )

        repo_id = await repository_repo.create_or_update(repository)

        await user_repo.add_repository(user.github_id, repo_id)
        
        # Create Change record (will fetch pom.xml after cloning)
        change = Change(
            repository_id=repo_id,
            commit_sha=commit_with_pom.get("id"),
            commit_message=commit_with_pom.get("message"),
            pom_content="",  # Will be populated after cloning
            status=FixStatus.PENDING
        )
        
        change_id = await change_repo.create(change)
        logger.info(f"Change created: {change_id}")
        
        # Trigger agent in background
        asyncio.create_task(
            self._run_agent_background(
                change_id=change_id,
                repo_url=f"https://github.com/{repository.full_name}.git",
                commit_sha=commit_with_pom.get("id"),
                repo_slug=repository.full_name,
                user_id=user_id,
                repo_id=repo_id,
                user= user,
                repository=repository,
                commit_with_pom=commit_with_pom

            )
        )

        return {
            "status": "success",
            "message": "pom.xml change detected and queued for processing",
            "user": {
                "id": user_id,
                "username": user.username
            },
            "repository": {
                "id": repo_id,
                "name": repository.name,
                "full_name": repository.full_name
            },
            "change": {
                "id": change_id,
                "status": "pending",
                "commit": commit_with_pom.get("id")[:7]
            }
        }
    
    async def _run_agent_background(
        self,
        change_id: str,
        repo_url: str,
        commit_sha: str,
        repo_slug: str,
        user_id,
        repo_id,
        user,
        repository,
        commit_with_pom
    ):
        """Run agent in background - tries recipe-based fix first, then falls back to existing agent"""
        try:
            from app.agents.callback import AgentCallback
            from app.agents.service import JavaMigrationAgentService
            from app.core.config import settings
            import tempfile
            import git
            from pathlib import Path
            
            callback = AgentCallback(change_id)
            
            # Update status: cloning
            await callback.update_status("cloning", 5, "Cloning repository...")
            
            # Clone repo
            temp_dir = tempfile.mkdtemp(prefix="aura_repo_")
            repo_path = f"{temp_dir}/repo"
            
            logger.info(f"Cloning {repo_url} to {repo_path}")
            repo = git.Repo.clone_from(repo_url, repo_path)
            repo.git.checkout(commit_sha)
            
            # Read pom.xml content from cloned repo
            pom_file_path = Path(repo_path) / "pom.xml"
            if pom_file_path.exists():
                pom_content = pom_file_path.read_text(encoding="utf-8")
                # Update change record with pom content
                await callback.update_status(
                    "cloning", 
                    progress=5,
                    message="Repository cloned, pom.xml loaded"
                )
                # Update pom_content separately
                from app.repositories.change_repository import change_repo
                await change_repo.update_status(
                    change_id, 
                    FixStatus.CLONING, 
                    progress=5,
                    message="Repository cloned",
                    pom_content=pom_content
                )
            else:
                logger.error(f"pom.xml not found in {repo_path}")
                await callback.save_error("pom.xml not found in repository")
                return
            
            # Update status: preparing
            await callback.update_status("preparing", 10, "Preparing environment...")
            
            # Get initial errors (compile without changes)
            from app.common_agents.agent.MavenReproducerAgent import MavenReproducerAgent
            from pathlib import Path
            
            maven_agent = MavenReproducerAgent(Path(repo_path))
            with maven_agent.start_container():
                (compile_ok, test_ok), error_text, _ = maven_agent.compile_maven(
                    diffs=[],
                    run_tests=False,
                    timeout=300
                )
            
            initial_errors = error_text if not compile_ok else ""
            
            # Get pom.xml diff to understand what changed
            git_repo = git.Repo(repo_path)
            pom_diff = git_repo.git.diff(f"{commit_sha}~1", commit_sha, "--", "pom.xml")
            
            # ========================================
            # RECIPE-BASED AGENT (runs BEFORE existing agent)
            # ========================================
            recipe_result = None
            if USE_RECIPE_AGENT and initial_errors:
                await callback.update_status("analyzing", 15, "Analyzing with recipe agent...")
                recipe_result = await self._try_recipe_based_fix(
                    repo_path=repo_path,
                    pom_diff=pom_diff,
                    initial_errors=initial_errors,
                    commit_sha=commit_sha,
                    repo_slug=repo_slug,
                    callback=callback
                )
                
                if recipe_result and recipe_result.get("success"):
                    # Recipe-based fix succeeded!
                    logger.info(f"[RecipeAgent] Successfully fixed using recipes for change {change_id}")
                    await callback.save_result(
                        diff=recipe_result.get("diff", ""),
                        solution=f"Fixed using OpenRewrite recipes: {recipe_result.get('recipes_applied', [])}",
                        modified_files=recipe_result.get("modified_files")  # Pass actual file contents
                    )
                    return
                else:
                    logger.info(f"[RecipeAgent] Recipe-based fix not applicable or failed, falling back to existing agent")
            
            # ========================================
            # EXISTING AGENT (fallback)
            # ========================================
            # Update status: analyzing
            await callback.update_status("analyzing", 20, "Agent starting analysis...")
            
            # Run agent
            agent_service = JavaMigrationAgentService()
            
            result = agent_service.process_repository(
                repo_path=repo_path,
                commit_hash=commit_sha,
                repo_slug=repo_slug,
                pom_diff=pom_diff,
                initial_errors=initial_errors
            )
            
            if result["success"]:
                await callback.save_result(
                    diff=result["diff"],
                    solution=result["solution"]
                )
                logger.info(f"Agent completed successfully for change {change_id}")
            else:
                await callback.save_error(result.get("error", "Unknown error"))
                logger.error(f"Agent failed for change {change_id}")
                
        except Exception as e:
            logger.error(f"Error running agent: {str(e)}", exc_info=True)
            await callback.save_error(str(e))

        return {
            "user": {
                "id": user_id,
                "username": user.username
            },
            "repository": {
                "id": repo_id,
                "name": repository.name,
                "full_name": repository.full_name
            },
            "commit": {
                "sha": commit_with_pom.get("id")[:7],
                "message": commit_with_pom.get("message")
            }
        }

    async def _try_recipe_based_fix(
        self,
        repo_path: str,
        pom_diff: str,
        initial_errors: str,
        commit_sha: str,
        repo_slug: str,
        callback
    ) -> dict:
        """
        Attempt to fix the breaking change using OpenRewrite recipes.
        This runs BEFORE the existing agent.
        
        Returns:
            dict with 'success', 'diff', 'recipes_applied' or None if not applicable
        """
        try:
            from app.recipe_agent import RecipeOrchestrator
            from app.core.config import settings
            
            logger.info("[RecipeAgent] Starting recipe-based analysis...")
            await callback.update_status("analyzing", 16, "Analyzing with OpenRewrite recipes...")
            
            orchestrator = RecipeOrchestrator(settings.GROQ_API_KEY)
            
            result = orchestrator.process_breaking_change(
                repo_path=repo_path,
                pom_diff=pom_diff,
                compilation_errors=initial_errors,
                commit_sha=commit_sha,
                repo_slug=repo_slug
            )
            
            if result.get("success"):
                await callback.update_status("fixing", 80, "Recipe-based fix applied successfully!")
                return result
            else:
                logger.info(f"[RecipeAgent] Recipe result: {result.get('message', 'No message')}")
                return result
                
        except Exception as e:
            logger.error(f"[RecipeAgent] Error in recipe-based fix: {e}", exc_info=True)
            return {
                "success": False,
                "used_recipes": False,
                "should_use_existing_agent": True,
                "message": f"Recipe agent error: {e}",
                "diff": ""
            }


webhook_service = WebhookService()
