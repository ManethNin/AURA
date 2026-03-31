"""
Recipe Orchestrator
Coordinates the recipe-based repair workflow.
Runs BEFORE the existing repair agent and decides whether to use recipes or fall back.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import git

from app.config.config import settings
from app.utilities.logger import logger
from app.nodes.recipe_service import RecipeAgentService, Recipe
from app.tools.recipe_generator import RecipeGenerator
from app.tools.recipe_executor import RecipeExecutor
from app.tools.tools import verify_maven_dependency_version
from app.tools.agents.MavenReproducerAgent import MavenReproducerAgent

RECIPE_MODULE_REQUIREMENTS = {
                "org.openrewrite.java.migrate.ChangeMethodInvocationReturnType": 
                    "org.openrewrite.recipe:rewrite-migrate-java:3.22.0",
                "org.openrewrite.java.spring.ChangeMethodParameter": 
                    "org.openrewrite.recipe:rewrite-spring:6.24.1",
}

class RecipeOrchestrator:
    """
    Orchestrates the recipe-based repair workflow.
    
    Workflow:
    1. Analyze the breaking change with LLM
    2. If recipes can fix it:
       a. Generate rewrite.yaml
       b. Add plugin to pom.xml
       c. Run mvn rewrite:run
       d. Verify compilation
       e. Get diff and commit
    3. If recipes cannot fix or fail, return signal to use existing agent
    """
    
    def __init__(self, groq_api_key: str = None, pipeline_logger=None):
        self.recipe_service = RecipeAgentService(groq_api_key)
        self.groq_api_key = groq_api_key or settings.GROQ_API_KEY
        self.pipeline_logger = pipeline_logger
    
    def _verify_version(self, version: str, group_id: str = None, artifact_id: str = None) -> Optional[str]:
        """
        Verify a dependency version using the shared Maven verification tool logic.
        
        This reuses the same verification flow as the verify_maven_dependency tool
        so AddDependency recipes are validated in the pipeline without involving the LLM.
        """
        if not version or not group_id or not artifact_id:
            return version

        resolved, exists = verify_maven_dependency_version(group_id, artifact_id, version)
        if resolved is None:
            logger.error(f"[RecipeOrchestrator] Artifact does not exist on Maven Central: {group_id}:{artifact_id}")
            return None
        if resolved != version.strip():
            logger.info(f"[RecipeOrchestrator] Version resolved via Maven Central: {group_id}:{artifact_id}:{version} -> {resolved}")
        elif exists:
            logger.info(f"[RecipeOrchestrator] Verified dependency version exists: {group_id}:{artifact_id}:{resolved}")
        else:
            logger.warning(f"[RecipeOrchestrator] Could not fully verify dependency version, using resolved value: {group_id}:{artifact_id}:{resolved}")
        return resolved

    def _extract_dependency_version_changes(self, pom_diff: str) -> List[Dict[str, str]]:
        """Extract dependency version changes from a pom.xml diff."""
        if not pom_diff:
            return []

        group_id = None
        artifact_id = None
        old_version = None
        new_version = None
        in_dependency = False
        changes: List[Dict[str, str]] = []

        for raw_line in pom_diff.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line[0] in {"+", "-", " "}:
                content = line[1:].strip()
            else:
                content = line

            if "<dependency>" in content:
                in_dependency = True

            if in_dependency:
                if "<groupId>" in content and "</groupId>" in content:
                    group_id = content.split("<groupId>", 1)[1].split("</groupId>", 1)[0].strip()

                if "<artifactId>" in content and "</artifactId>" in content:
                    artifact_id = content.split("<artifactId>", 1)[1].split("</artifactId>", 1)[0].strip()

                if line.startswith("-") and "<version>" in content and "</version>" in content:
                    old_version = content.split("<version>", 1)[1].split("</version>", 1)[0].strip()

                if line.startswith("+") and "<version>" in content and "</version>" in content:
                    new_version = content.split("<version>", 1)[1].split("</version>", 1)[0].strip()

            if "</dependency>" in content:
                if group_id and artifact_id and old_version and new_version:
                    changes.append({
                        "groupId": group_id,
                        "artifactId": artifact_id,
                        "oldVersion": old_version,
                        "newVersion": new_version,
                    })
                group_id = None
                artifact_id = None
                old_version = None
                new_version = None
                in_dependency = False

        if group_id and artifact_id and old_version and new_version:
            changes.append({
                "groupId": group_id,
                "artifactId": artifact_id,
                "oldVersion": old_version,
                "newVersion": new_version,
            })

        return changes

    def _append_dependency_upgrade_recipes(self, selected_recipes: List[Recipe], pom_diff: str) -> List[Recipe]:
        """Append dependency upgrade recipes so Java recipe execution order is preserved."""
        version_changes = self._extract_dependency_version_changes(pom_diff)
        if not version_changes:
            logger.info("[RecipeOrchestrator] No dependency version changes detected to prepend")
            return selected_recipes

        existing_upgrades = {
            (
                recipe.arguments.get("groupId"),
                recipe.arguments.get("artifactId"),
                recipe.arguments.get("newVersion"),
            )
            for recipe in selected_recipes
            if recipe.name == "org.openrewrite.maven.UpgradeDependencyVersion"
        }

        appended_recipes: List[Recipe] = []
        for change in version_changes:
            signature = (change["groupId"], change["artifactId"], change["newVersion"])
            if signature in existing_upgrades:
                continue

            appended_recipes.append(
                Recipe(
                    name="org.openrewrite.maven.UpgradeDependencyVersion",
                    arguments={
                        "groupId": change["groupId"],
                        "artifactId": change["artifactId"],
                        "newVersion": change["newVersion"],
                    },
                )
            )

        if appended_recipes:
            logger.info(
                f"[RecipeOrchestrator] Appended {len(appended_recipes)} UpgradeDependencyVersion recipe(s) for Java execution"
            )

        return selected_recipes + appended_recipes

    def _restore_previous_pom(self, project_path: Path, commit_sha: str) -> bool:
        """Restore the previous pom.xml so Java recipes can run on compilable sources."""
        pom_path = project_path / "pom.xml"
        if not pom_path.exists():
            logger.error("[RecipeOrchestrator] pom.xml not found for restoration")
            return False

        try:
            repo = git.Repo(project_path)
            revision_candidates = []
            if commit_sha:
                revision_candidates.append(f"{commit_sha}~1:pom.xml")
            revision_candidates.append("HEAD~1:pom.xml")

            seen = set()
            for revision in revision_candidates:
                if revision in seen:
                    continue
                seen.add(revision)
                try:
                    previous_pom = repo.git.show(revision)
                except git.GitCommandError:
                    continue

                if previous_pom.strip():
                    pom_path.write_text(previous_pom, encoding="utf-8")
                    logger.info(f"[RecipeOrchestrator] Restored previous pom.xml from {revision}")
                    return True

        except Exception as e:
            logger.error(f"[RecipeOrchestrator] Error restoring previous pom.xml: {e}")

        logger.error("[RecipeOrchestrator] Failed to restore previous pom.xml")
        return False
    
    def process_breaking_change(
        self,
        repo_path: str,
        pom_diff: str,
        migration_plan: str = "",
        commit_sha: str = "",
        repo_slug: str = "",
    ) -> Dict[str, Any]:
        """
        Attempt to fix breaking changes using OpenRewrite recipes.

        Args:
            repo_path: Path to the cloned repository
            pom_diff: Git diff of pom.xml changes
            migration_plan: Plan produced by the planning agent
            commit_sha: Current commit hash
            repo_slug: Repository slug (owner/repo)

        Returns:
            Dict with:
                - success: bool - whether the fix was successful
                - used_recipes: bool - whether recipes were used
                - diff: str - the fix diff (if successful)
                - should_use_existing_agent: bool - whether to fall back to existing agent
                - message: str - status message
        """
        logger.info(f"[RecipeOrchestrator] Starting recipe-based analysis for {repo_slug}")

        project_path = Path(repo_path)

        # Read pom.xml content for context
        pom_path = project_path / "pom.xml"
        pom_content = ""
        if pom_path.exists():
            with open(pom_path, 'r', encoding='utf-8') as f:
                pom_content = f.read()

        # Log the full context that will be sent to the recipe agent's LLM
        if self.pipeline_logger:
            pom_preview = pom_content[:3000] if pom_content else "Not provided"
            recipe_llm_input = (
                "=== RECIPE AGENT LLM INPUT ===\n"
                "(Exact content sent to the Recipe Agent LLM for recipe selection)\n\n"
                "## POM.XML CHANGES (Git Diff):\n"
                f"{pom_diff}\n\n"
                "## MIGRATION PLAN (from Planning Agent):\n"
                f"{migration_plan or 'Not provided'}\n\n"
                "## POM.XML CONTENT (first 3000 chars):\n"
                f"{pom_preview}\n"
            )
            (self.pipeline_logger.log_dir / "recipe_agent_llm_prompt.txt").write_text(
                recipe_llm_input, encoding="utf-8"
            )
            logger.info("[RecipeOrchestrator] Recipe LLM input saved to recipe_agent_llm_prompt.txt")

        # Step 1: Analyze the breaking change with LLM using migration plan
        logger.info("[RecipeOrchestrator] Analyzing breaking change with LLM...")
        analysis = self.recipe_service.analyze_breaking_change(
            pom_diff=pom_diff,
            migration_plan=migration_plan,
            pom_content=pom_content,
        )
        
        # Log the analysis result
        if self.pipeline_logger:
            self.pipeline_logger.log_recipe_analysis(analysis)
        
        # Step 2: Check if recipes can handle this
        if not analysis.can_use_recipes:
            logger.info(f"[RecipeOrchestrator] Recipes cannot fix this issue: {analysis.reasoning}")
            
            # Log recipe decision stage
            if self.pipeline_logger:
                self.pipeline_logger.log_stage("recipe_decision", {
                    "can_use_recipes": False,
                    "reasoning": analysis.reasoning or "Unknown reason",
                    "selected_recipes": [],
                    "fallback_to_existing_agent": True,
                    "decision_timestamp": __import__('datetime').datetime.now().isoformat()
                })
            
            return {
                "success": False,
                "used_recipes": False,
                "should_use_existing_agent": True,
                "message": f"Recipes not applicable: {analysis.reasoning}",
                "diff": ""
            }
        
        selected_recipes = analysis.selected_recipes
        if not selected_recipes:
            logger.info("[RecipeOrchestrator] No recipes selected by LLM")
            
            # Log recipe decision stage
            if self.pipeline_logger:
                self.pipeline_logger.log_stage("recipe_decision", {
                    "can_use_recipes": True,
                    "reasoning": "No recipes selected despite can_use_recipes=True",
                    "selected_recipes": [],
                    "fallback_to_existing_agent": True,
                    "decision_timestamp": __import__('datetime').datetime.now().isoformat()
                })
            
            return {
                "success": False,
                "used_recipes": False,
                "should_use_existing_agent": True,
                "message": "No recipes selected",
                "diff": ""
            }
        
        # SAFETY & NORMALIZATION: Clean up recipe arguments
        normalized_recipes: List[Recipe] = []
        for recipe in selected_recipes:
            recipe_name = recipe.name
            args = recipe.arguments
            
            # Remove 'onlyIfUsing' from AddDependency recipes
            # This parameter requires Java source parsing which fails on broken projects
            if recipe_name == "org.openrewrite.maven.AddDependency":
                if "onlyIfUsing" in args:
                    logger.warning(f"[RecipeOrchestrator] Removing 'onlyIfUsing' from AddDependency (not supported for broken projects)")
                    del args["onlyIfUsing"]

            if recipe_name == "org.openrewrite.java.ChangeType":
                if "ignoreDefinition" not in args:
                    logger.info("[RecipeOrchestrator] Setting ignoreDefinition=true for ChangeType")
                    args["ignoreDefinition"] = True
            
            # Verify version numbers against Maven Central for all recipes
            # This is CRITICAL - Maven Central requires exact version strings
            if "version" in args:
                group_id = args.get("groupId", "")
                artifact_id = args.get("artifactId", "")
                old_version = args["version"]
                verified_version = self._verify_version(old_version, group_id, artifact_id)
                if verified_version is None and recipe_name == "org.openrewrite.maven.AddDependency":
                    logger.warning(
                        f"[RecipeOrchestrator] Dropping AddDependency recipe for nonexistent artifact {group_id}:{artifact_id}"
                    )
                    continue
                args["version"] = verified_version or old_version
                if args["version"] != old_version:
                    logger.info(f"[RecipeOrchestrator] Recipe version verified: {old_version} -> {args['version']}")

            if "newVersion" in args:
                group_id = args.get("groupId", args.get("newGroupId", ""))
                artifact_id = args.get("artifactId", args.get("newArtifactId", ""))
                old_version = args["newVersion"]
                verified_version = self._verify_version(old_version, group_id, artifact_id)
                if verified_version is not None:
                    args["newVersion"] = verified_version
                if args["newVersion"] != old_version:
                    logger.info(f"[RecipeOrchestrator] Recipe newVersion verified: {old_version} -> {args['newVersion']}")

            normalized_recipes.append(recipe)

        selected_recipes = normalized_recipes

        if not selected_recipes:
            logger.info("[RecipeOrchestrator] No valid recipes remain after dependency validation")
            return {
                "success": False,
                "used_recipes": False,
                "should_use_existing_agent": True,
                "message": "No valid recipes remain after Maven dependency validation",
                "diff": ""
            }
        
        recipe_name = analysis.recipe_name or "com.aura.fix.AutoGeneratedFix"
        display_name = analysis.recipe_display_name or "AURA Auto-Generated Fix"
        description = analysis.recipe_description or "Automatically generated fix for breaking changes"
        
        # Check if all recipes are Maven-only (don't need Java source parsing)
        # Maven-only recipes can work on broken projects because they only modify pom.xml
        MAVEN_ONLY_RECIPES = [
            "org.openrewrite.maven.AddDependency",
            "org.openrewrite.maven.RemoveDependency",
            "org.openrewrite.maven.UpgradeDependency",
            "org.openrewrite.maven.ChangeDependencyGroupIdAndArtifactId",
            "org.openrewrite.maven.AddPlugin",
            "org.openrewrite.maven.ChangePluginConfiguration",
            "org.openrewrite.maven.ChangePropertyValue",
            "org.openrewrite.maven.AddProperty",
        ]
        maven_only = all(
            r.name in MAVEN_ONLY_RECIPES or r.name.startswith("org.openrewrite.maven.")
            for r in selected_recipes
        )
        
        # Java recipes require the project to compile - warn if selected for broken projects
        java_recipes = [r.name for r in selected_recipes if r.name.startswith("org.openrewrite.java.")]
        if java_recipes:
            logger.warning(f"[RecipeOrchestrator] Java recipes selected: {java_recipes}")
            logger.info("[RecipeOrchestrator] Restoring previous pom.xml before executing Java recipes")
            if not self._restore_previous_pom(project_path, commit_sha):
                return {
                    "success": False,
                    "used_recipes": True,
                    "should_use_existing_agent": True,
                    "message": "Failed to restore previous pom.xml for Java recipe execution",
                    "diff": ""
                }
            selected_recipes = self._append_dependency_upgrade_recipes(selected_recipes, pom_diff)
        
        logger.info(f"[RecipeOrchestrator] Maven-only recipes: {maven_only}")
        logger.info(f"[RecipeOrchestrator] Generating rewrite.yaml with {len(selected_recipes)} recipes...")
        logger.info(f"[RecipeOrchestrator] Selected recipes: {selected_recipes}")

        # Log recipe decision - recipes will be attempted
        if self.pipeline_logger:
            self.pipeline_logger.log_stage("recipe_decision", {
                "can_use_recipes": True,
                "recipes_selected": len(selected_recipes),
                "recipes_details": [{"name": r.name, "arguments": r.arguments} for r in selected_recipes],
                "recipe_name": recipe_name,
                "recipe_display_name": display_name,
                "fallback_to_existing_agent": False,
                "decision_timestamp": __import__('datetime').datetime.now().isoformat()
            })
        
        generator = RecipeGenerator(project_path)
        
        # Always use OpenRewrite for recipe execution (no direct pom.xml modification)
        try:
            # Write rewrite.yaml
            yaml_path = generator.write_rewrite_yaml(
                recipe_name=recipe_name,
                display_name=display_name,
                description=description,
                recipe_list=selected_recipes
            )
            logger.info(f"[RecipeOrchestrator] Created rewrite.yaml at: {yaml_path}")
            
            # Log the content for debugging
            with open(yaml_path, 'r') as f:
                yaml_content = f.read()
            logger.info(f"[RecipeOrchestrator] rewrite.yaml content:\n{yaml_content}")
            
            # Log rewrite.yaml generation
            if self.pipeline_logger:
                self.pipeline_logger.log_recipe_execution(
                    "rewrite_yaml_generation",
                    True,
                    yaml_content,
                    ""
                )

             
            migration_deps = [
                    # Old dependency (so Rewrite can find the old type)
                        {
                        'groupId': 'org.apache.maven.doxia',
                        'artifactId': 'doxia-module-xhtml',
                        'version': '1.0'
                        },
                    # New dependency (optional, but often needed on classpath)
                        {
                        'groupId': 'org.apache.maven.doxia',
                        'artifactId': 'doxia-site-renderer',
                        'version': '1.11.1'
                        }
                ]
            
            # Add plugin to pom.xml (skip Java parsing for Maven-only recipes)
            if not generator.add_rewrite_plugin_to_pom(recipe_name, maven_only_recipes=maven_only, plugin_dependencies=migration_deps):
                logger.error("[RecipeOrchestrator] Failed to add plugin to pom.xml")
                
                # Log recipe failure
                if self.pipeline_logger:
                    self.pipeline_logger.log_stage("recipe_failure", {
                        "stage": "add_plugin_to_pom",
                        "reason": "Failed to add OpenRewrite plugin to pom.xml",
                        "recipes_attempted": [r.name for r in selected_recipes],
                        "failure_timestamp": __import__('datetime').datetime.now().isoformat()
                    })
                
                generator.cleanup()
                return {
                    "success": False,
                    "used_recipes": True,
                    "should_use_existing_agent": True,
                    "message": "Failed to add OpenRewrite plugin to pom.xml",
                    "diff": ""
                }
            
        except Exception as e:
            logger.error(f"[RecipeOrchestrator] Error generating recipe files: {e}")
            
            # Log recipe failure
            if self.pipeline_logger:
                self.pipeline_logger.log_error(
                    "recipe_file_generation",
                    str(e),
                    __import__('traceback').format_exc()
                )
            
            generator.cleanup()
            return {
                "success": False,
                "used_recipes": True,
                "should_use_existing_agent": True,
                "message": f"Error generating recipe files: {e}",
                "diff": ""
            }
        
        # Step 4: Execute mvn rewrite:run
        logger.info("[RecipeOrchestrator] Executing mvn rewrite:run...")
        
        executor = RecipeExecutor(project_path)
        
        try:
            with executor.start_container():
                # Run rewrite with maven_only flag to skip compilation if appropriate
                rewrite_success, rewrite_output, rewrite_error = executor.run_rewrite(maven_only=maven_only)
                
                # Log rewrite execution
                if self.pipeline_logger:
                    self.pipeline_logger.log_recipe_execution(
                        "mvn_rewrite_run",
                        rewrite_success,
                        rewrite_output,
                        rewrite_error
                    )
                
                if not rewrite_success:
                    logger.error(f"[RecipeOrchestrator] rewrite:run failed: {rewrite_error or rewrite_output[:500]}")
                    
                    # Log rewrite failure
                    if self.pipeline_logger:
                        self.pipeline_logger.log_stage("recipe_failure", {
                            "stage": "mvn_rewrite_run",
                            "reason": "OpenRewrite execution failed",
                            "error": rewrite_error[:500] if rewrite_error else rewrite_output[:500],
                            "recipes_attempted": [r.name for r in selected_recipes],
                            "failure_timestamp": __import__('datetime').datetime.now().isoformat()
                        })
                    
                    generator.cleanup()
                    return {
                        "success": False,
                        "used_recipes": True,
                        "should_use_existing_agent": True,
                        "message": f"OpenRewrite execution failed: {rewrite_error or rewrite_output[:200]}",
                        "diff": ""
                    }
                
                # Step 5: Verify compilation
                logger.info("[RecipeOrchestrator] Verifying compilation after rewrite...")
                compile_success, compile_output = executor.compile_after_rewrite()
                
                # Log compilation result
                if self.pipeline_logger:
                    self.pipeline_logger.log_recipe_execution(
                        "post_rewrite_compilation",
                        compile_success,
                        compile_output,
                        ""
                    )
                
                if compile_success:
                    logger.info("[RecipeOrchestrator] ✅ Recipe-based fix successful!")
                    
                    # Clean up OpenRewrite artifacts BEFORE getting the diff
                    # This removes rewrite.yaml and the plugin from pom.xml
                    # so the diff only contains the actual fix
                    generator.cleanup()
                    generator.remove_rewrite_plugin_from_pom()
                    
                    # Read the actual modified file contents
                    # These are CORRECTLY modified by OpenRewrite, so we use them directly
                    # instead of trying to re-apply the diff later
                    modified_files = self._read_modified_files(project_path)
                    
                    # Also get the diff for display/logging purposes
                    diff = executor.get_git_diff()
                    
                    # IMPORTANT: Revert changes after capturing diff
                    # This ensures the repository stays clean for repeated testing
                    # Similar to LLM agent pipeline pattern
                    self._revert_changes(project_path, commit_sha)
                    logger.info("[RecipeOrchestrator] Repository reverted to original state (can test again)")
                    
                    result = {
                        "success": True,
                        "used_recipes": True,
                        "should_use_existing_agent": False,
                        "message": "Successfully fixed using OpenRewrite recipes",
                        "diff": diff,
                        "modified_files": modified_files,  # Actual file contents!
                        "recipe_name": recipe_name,
                        "recipes_applied": [r.name for r in selected_recipes]
                    }
                    
                    # Log final result
                    if self.pipeline_logger:
                        self.pipeline_logger.log_recipe_result(result)
                    
                    return result
                else:
                    logger.warning(f"[RecipeOrchestrator] Compilation still fails after rewrite: {compile_output[:500]}")

                    # Write maven errors to docker_build_errors.txt in the root log dir
                    if self.pipeline_logger:
                        self.pipeline_logger.log_docker_build_errors(compile_output, compile_output)
                    
                    # Log recipe failure
                    if self.pipeline_logger:
                        self.pipeline_logger.log_stage("recipe_failure", {
                            "stage": "post_rewrite_compilation",
                            "reason": "Compilation failed after rewrite",
                            "error": compile_output[:500],
                            "recipes_attempted": [r.name for r in selected_recipes],
                            "failure_timestamp": __import__('datetime').datetime.now().isoformat()
                        })
                    
                    # Revert the changes
                    self._revert_changes(project_path, commit_sha)
                    generator.cleanup()
                    
                    return {
                        "success": False,
                        "used_recipes": True,
                        "should_use_existing_agent": True,
                        "message": f"Compilation failed after rewrite: {compile_output[:200]}",
                        "diff": ""
                    }
                    
        except Exception as e:
            logger.error(f"[RecipeOrchestrator] Error executing recipes: {e}")
            
            # Log recipe execution error
            if self.pipeline_logger:
                self.pipeline_logger.log_error(
                    "recipe_execution",
                    str(e),
                    __import__('traceback').format_exc()
                )
            
            generator.cleanup()
            return {
                "success": False,
                "used_recipes": True,
                "should_use_existing_agent": True,
                "message": f"Error executing recipes: {e}",
                "diff": ""
            }
    
    def _read_modified_files(self, project_path: Path) -> Dict[str, str]:
        """
        Read all modified files from the repository.
        These are the actual fixed file contents created by OpenRewrite.
        
        Returns:
            Dict mapping relative file paths to their contents
        """
        modified_files = {}
        
        try:
            repo = git.Repo(project_path)
            
            # Get list of modified files from git
            # This includes both staged and unstaged changes
            diff_index = repo.index.diff(None)  # Unstaged changes
            diff_head = repo.index.diff(repo.head.commit)  # Staged changes
            
            modified_paths = set()
            for diff in diff_index:
                if diff.a_path:
                    modified_paths.add(diff.a_path)
                if diff.b_path:
                    modified_paths.add(diff.b_path)
            for diff in diff_head:
                if diff.a_path:
                    modified_paths.add(diff.a_path)
                if diff.b_path:
                    modified_paths.add(diff.b_path)
            
            # Also check for untracked files that might be relevant
            # (though OpenRewrite typically modifies existing files)
            
            # Read the content of each modified file
            for rel_path in modified_paths:
                file_path = project_path / rel_path
                if file_path.exists() and file_path.is_file():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            modified_files[rel_path] = f.read()
                        logger.info(f"[RecipeOrchestrator] Captured modified file: {rel_path}")
                    except Exception as e:
                        logger.warning(f"[RecipeOrchestrator] Could not read {rel_path}: {e}")
            
            logger.info(f"[RecipeOrchestrator] Captured {len(modified_files)} modified files")
            
        except Exception as e:
            logger.error(f"[RecipeOrchestrator] Error reading modified files: {e}")
        
        return modified_files
    
    def _revert_changes(self, project_path: Path, commit_sha: str) -> None:
        """Revert all changes in the repository."""
        try:
            repo = git.Repo(project_path)
            repo.git.checkout("--", ".")
            repo.git.clean("-fd")
            logger.info("[RecipeOrchestrator] Reverted changes after failed recipe application")
        except Exception as e:
            logger.error(f"[RecipeOrchestrator] Error reverting changes: {e}")
    
    def _remove_rewrite_plugin_from_pom(self, project_path: Path) -> None:
        """
        Remove the rewrite-maven-plugin from pom.xml after successful recipe execution.
        This ensures the diff only contains the actual fix, not the OpenRewrite tooling.
        """
        import xml.etree.ElementTree as ET
        
        pom_path = project_path / "pom.xml"
        if not pom_path.exists():
            return
        
        try:
            # Register namespace to preserve it
            ET.register_namespace('', 'http://maven.apache.org/POM/4.0.0')
            
            tree = ET.parse(pom_path)
            root = tree.getroot()
            
            # Handle namespace
            ns_uri = ""
            if root.tag.startswith('{'):
                ns_uri = root.tag.split('}')[0] + '}'
            
            # Find plugins section
            build = root.find(f"{ns_uri}build")
            if build is None:
                return
            
            plugins = build.find(f"{ns_uri}plugins")
            if plugins is None:
                return
            
            # Find and remove rewrite-maven-plugin
            for plugin in plugins.findall(f"{ns_uri}plugin"):
                artifact_id = plugin.find(f"{ns_uri}artifactId")
                if artifact_id is not None and artifact_id.text == "rewrite-maven-plugin":
                    plugins.remove(plugin)
                    logger.info("[RecipeOrchestrator] Removed rewrite-maven-plugin from pom.xml")
                    break
            
            # Write back
            tree.write(pom_path, encoding='utf-8', xml_declaration=True)
            
        except Exception as e:
            logger.error(f"[RecipeOrchestrator] Error removing rewrite plugin: {e}")

    def get_initial_compilation_errors(self, repo_path: str) -> str:
        """
        Get initial compilation errors from the repository.
        Uses MavenReproducerAgent for consistency with existing workflow.
        """
        project_path = Path(repo_path)
        maven_agent = MavenReproducerAgent(project_path)
        
        try:
            with maven_agent.start_container():
                (compile_ok, test_ok), error_text, _ = maven_agent.compile_maven(
                    diffs=[],
                    run_tests=False,
                    timeout=300,
                    collect_all_errors=True,
                    errors_only=True,
                    initial_error_scan=True,
                )
                
                if not compile_ok:
                    return error_text
                return ""
        except Exception as e:
            logger.error(f"[RecipeOrchestrator] Error getting compilation errors: {e}")
            return str(e)
