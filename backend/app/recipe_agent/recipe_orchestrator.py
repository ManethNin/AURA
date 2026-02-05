"""
Recipe Orchestrator
Coordinates the recipe-based repair workflow.
Runs BEFORE the existing repair agent and decides whether to use recipes or fall back.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import git

from app.core.config import settings
from app.utils.logger import logger
from app.recipe_agent.recipe_service import RecipeAgentService
from app.recipe_agent.recipe_generator import RecipeGenerator
from app.recipe_agent.recipe_executor import RecipeExecutor
from app.masterthesis.agent.MavenReproducerAgent import MavenReproducerAgent


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
    
    # Known correct versions for common dependencies
    # When LLM provides incomplete versions, use these
    # Maven Central requires exact version strings - incomplete versions will fail
    KNOWN_VERSIONS = {
        "commons-codec:commons-codec": {
            "1.16": "1.16.1",  # 1.16 doesn't exist, use 1.16.1
            "1.15": "1.15",
            "1.17": "1.17",
            "1.11": "1.11",
        },
        "commons-io:commons-io": {
            "2.15": "2.15.1",
            "2.14": "2.14.0",
            "2.11": "2.11.0",
            "2.6": "2.6",
        },
        "org.apache.commons:commons-lang3": {
            "3.14": "3.14.0",
            "3.13": "3.13.0",
            "3.12": "3.12.0",
        },
        "com.google.guava:guava": {
            "32": "32.1.3-jre",
            "31": "31.1-jre",
            "30": "30.1.1-jre",
        },
        "org.slf4j:slf4j-api": {
            "2.0": "2.0.9",
            "1.7": "1.7.36",
        },
    }
    
    def __init__(self, groq_api_key: str = None, pipeline_logger=None):
        self.recipe_service = RecipeAgentService(groq_api_key)
        self.groq_api_key = groq_api_key or settings.GROQ_API_KEY
        self.pipeline_logger = pipeline_logger
    
    def _normalize_version(self, version: str, group_id: str = None, artifact_id: str = None) -> str:
        """
        Normalize version numbers to ensure Maven can resolve them.
        LLM sometimes provides incomplete versions like "1.16" instead of "1.16.0".
        
        IMPORTANT: Maven Central requires exact version strings. Version "1.16" is NOT
        the same as "1.16.0" and will fail to resolve if the exact version doesn't exist.
        """
        if not version:
            return version
        
        version = version.strip()
        original_version = version
            
        # Check if we have a known mapping
        if group_id and artifact_id:
            key = f"{group_id}:{artifact_id}"
            if key in self.KNOWN_VERSIONS:
                if version in self.KNOWN_VERSIONS[key]:
                    normalized = self.KNOWN_VERSIONS[key][version]
                    logger.info(f"[RecipeOrchestrator] Normalized version {group_id}:{artifact_id}:{version} -> {normalized}")
                    return normalized
        
        # Specific fixes for commonly mis-versioned dependencies
        # commons-codec 1.16 doesn't exist, but 1.16.0 and 1.16.1 do
        if artifact_id == "commons-codec" and version == "1.16":
            logger.info(f"[RecipeOrchestrator] Normalized commons-codec:1.16 -> 1.16.1")
            return "1.16.1"
        
        # General heuristic: if version has only 2 parts (X.Y), try X.Y.0
        # But warn that this may not always work
        parts = version.split('.')
        if len(parts) == 2:
            # Check if both parts are numeric
            try:
                int(parts[0])
                int(parts[1])
                normalized = f"{version}.0"
                logger.warning(f"[RecipeOrchestrator] Version {version} has only 2 parts, trying {normalized} (may not exist)")
                return normalized
            except ValueError:
                pass
        
        return version
    
    def process_breaking_change(
        self,
        repo_path: str,
        pom_diff: str,
        compilation_errors: str,
        commit_sha: str,
        repo_slug: str,
        api_changes: str = ""
    ) -> Dict[str, Any]:
        """
        Attempt to fix breaking changes using OpenRewrite recipes.
        
        Args:
            repo_path: Path to the cloned repository
            pom_diff: Git diff of pom.xml changes
            compilation_errors: Maven compilation errors
            commit_sha: Current commit hash
            repo_slug: Repository slug (owner/repo)
            api_changes: Filtered API changes from REVAPI/JApiCmp
            
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
        
        # Step 1: Analyze the breaking change with LLM
        logger.info("[RecipeOrchestrator] Analyzing breaking change with LLM...")
        analysis = self.recipe_service.analyze_breaking_change(
            pom_diff=pom_diff,
            compilation_errors=compilation_errors,
            pom_content=pom_content,
            api_changes=api_changes
        )
        
        # Log the analysis result
        if self.pipeline_logger:
            self.pipeline_logger.log_recipe_analysis(analysis)
        
        # Step 2: Check if recipes can handle this
        if not analysis.get("can_use_recipes", False):
            logger.info(f"[RecipeOrchestrator] Recipes cannot fix this issue: {analysis.get('reasoning')}")
            return {
                "success": False,
                "used_recipes": False,
                "should_use_existing_agent": True,
                "message": f"Recipes not applicable: {analysis.get('reasoning')}",
                "diff": ""
            }
        
        selected_recipes = analysis.get("selected_recipes", [])
        if not selected_recipes:
            logger.info("[RecipeOrchestrator] No recipes selected by LLM")
            return {
                "success": False,
                "used_recipes": False,
                "should_use_existing_agent": True,
                "message": "No recipes selected",
                "diff": ""
            }
        
        # SAFETY & NORMALIZATION: Clean up recipe arguments
        for recipe in selected_recipes:
            recipe_name = recipe.get("name", "")
            args = recipe.get("arguments", {})
            
            # Remove 'onlyIfUsing' from AddDependency recipes
            # This parameter requires Java source parsing which fails on broken projects
            if recipe_name == "org.openrewrite.maven.AddDependency":
                if "onlyIfUsing" in args:
                    logger.warning(f"[RecipeOrchestrator] Removing 'onlyIfUsing' from AddDependency (not supported for broken projects)")
                    del args["onlyIfUsing"]
            
            # Normalize version numbers for all recipes that have version parameters
            # This is CRITICAL - Maven Central requires exact version strings
            if "version" in args:
                group_id = args.get("groupId", "")
                artifact_id = args.get("artifactId", "")
                old_version = args["version"]
                args["version"] = self._normalize_version(old_version, group_id, artifact_id)
                if args["version"] != old_version:
                    logger.info(f"[RecipeOrchestrator] Recipe version normalized: {old_version} -> {args['version']}")
            
            if "newVersion" in args:
                group_id = args.get("groupId", args.get("newGroupId", ""))
                artifact_id = args.get("artifactId", args.get("newArtifactId", ""))
                old_version = args["newVersion"]
                args["newVersion"] = self._normalize_version(old_version, group_id, artifact_id)
                if args["newVersion"] != old_version:
                    logger.info(f"[RecipeOrchestrator] Recipe newVersion normalized: {old_version} -> {args['newVersion']}")
        
        # Step 3: Generate rewrite.yaml and update pom.xml
        logger.info(f"[RecipeOrchestrator] Generating rewrite.yaml with {len(selected_recipes)} recipes...")
        logger.info(f"[RecipeOrchestrator] Selected recipes: {selected_recipes}")
        
        recipe_name = analysis.get("recipe_name", "com.aura.fix.AutoGeneratedFix")
        display_name = analysis.get("recipe_display_name", "AURA Auto-Generated Fix")
        description = analysis.get("recipe_description", "Automatically generated fix for breaking changes")
        
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
            r.get("name", "") in MAVEN_ONLY_RECIPES or r.get("name", "").startswith("org.openrewrite.maven.")
            for r in selected_recipes
        )
        
        # Java recipes require the project to compile - warn if selected for broken projects
        java_recipes = [r.get("name") for r in selected_recipes if r.get("name", "").startswith("org.openrewrite.java.")]
        if java_recipes:
            logger.warning(f"[RecipeOrchestrator] Java recipes selected: {java_recipes}")
            logger.warning("[RecipeOrchestrator] Java recipes require compilable code - may fail on broken projects")
        
        logger.info(f"[RecipeOrchestrator] Maven-only recipes: {maven_only}")
        
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
            
            # Add plugin to pom.xml (skip Java parsing for Maven-only recipes)
            if not generator.add_rewrite_plugin_to_pom(recipe_name, maven_only_recipes=maven_only):
                logger.error("[RecipeOrchestrator] Failed to add plugin to pom.xml")
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
                    self._remove_rewrite_plugin_from_pom(project_path)
                    
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
                        "recipes_applied": [r.get("name") for r in selected_recipes]
                    }
                    
                    # Log final result
                    if self.pipeline_logger:
                        self.pipeline_logger.log_recipe_result(result)
                    
                    return result
                else:
                    logger.warning(f"[RecipeOrchestrator] Compilation still fails after rewrite: {compile_output[:500]}")
                    
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
                    timeout=300
                )
                
                if not compile_ok:
                    return error_text
                return ""
        except Exception as e:
            logger.error(f"[RecipeOrchestrator] Error getting compilation errors: {e}")
            return str(e)
