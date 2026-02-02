"""
Recipe Executor
Executes OpenRewrite recipes using Maven in a Docker container.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from contextlib import contextmanager

from app.utils.logger import logger
from app.masterthesis.agent.DockerAgent import DockerAgent, DockerError


class RecipeExecutor:
    """
    Executes OpenRewrite recipes using Maven.
    Uses Docker container to run Maven commands safely.
    """
    
    MAVEN_IMAGE = "maven:3.9.8-amazoncorretto-17"
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.docker_agent = DockerAgent(self.MAVEN_IMAGE, project_path)
        self.container = None
        self.results_dir = tempfile.mkdtemp()
    
    @contextmanager
    def start_container(self):
        """Context manager to handle container lifecycle."""
        try:
            container, setup_stdout, setup_stderr = (
                self.docker_agent.execute_command_with_mounts(
                    mounts={
                        str(self.project_path): {"bind": "/mnt/repo", "mode": "rw"},
                        self.results_dir: {"bind": "/mnt/data", "mode": "rw"},
                    },
                    setup_command="mkdir -p /app",
                )
            )
            self.container = container
            yield self.container
        finally:
            if self.container is not None:
                self.docker_agent.clean_up(self.container)
            else:
                self.docker_agent.clean_up()
            
            if os.path.exists(self.results_dir):
                shutil.rmtree(self.results_dir)
    
    def run_rewrite(self, maven_only: bool = True, timeout: int = 600) -> Tuple[bool, str, str]:
        """
        Execute 'mvn rewrite:run' to apply the OpenRewrite recipes.
        
        Args:
            maven_only: If True, use flags to skip Java compilation (for pom.xml-only recipes)
            timeout: Maximum time in seconds to wait for the command
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        if self.container is None:
            raise RuntimeError("Container not started. Use start_container() context manager.")
        
        # First, discover available recipes to verify our recipe is found
        discover_cmd = "cd /mnt/repo && mvn rewrite:discover -B 2>&1 | tail -100"
        logger.info(f"Discovering recipes: {discover_cmd}")
        
        try:
            exit_code, discover_output = self.container.exec_run(
                cmd=["sh", "-c", discover_cmd],
                workdir="/mnt/repo",
                environment={"MAVEN_OPTS": "-Xmx2g"}
            )
            discover_text = discover_output.decode('utf-8', errors='replace') if discover_output else ""
            logger.info(f"Recipe discovery result (exit={exit_code}):\n{discover_text[-1500:]}")
        except Exception as e:
            logger.warning(f"Recipe discovery failed: {e}")
        
        # For Maven-only recipes (AddDependency, UpgradeDependency, etc.):
        # We need to skip Java compilation since the project is broken
        # Use -Drewrite.pomCacheEnabled=false to avoid caching issues
        # Use -Dmaven.main.skip=true to skip main compilation
        # Use -Dcheckstyle.skip=true -Denforcer.skip=true to skip other plugins
        
        if maven_only:
            # Maven-only recipes only need to parse pom.xml, not Java sources
            # Run with compilation skipped
            command = (
                "cd /mnt/repo && mvn org.openrewrite.maven:rewrite-maven-plugin:5.43.0:run "
                "-Dmaven.main.skip=true -Dmaven.test.skip=true "
                "-Dcheckstyle.skip=true -Denforcer.skip=true "
                "-Dspotbugs.skip=true -Dpmd.skip=true "
                "-B 2>&1"
            )
        else:
            # For Java recipes, we need full compilation - but this won't work on broken projects
            # This is a known limitation - Java recipes require compilable code
            command = "cd /mnt/repo && mvn org.openrewrite.maven:rewrite-maven-plugin:5.43.0:run -B 2>&1"
        
        logger.info(f"Executing: {command}")
        
        try:
            exit_code, output = self.container.exec_run(
                cmd=["sh", "-c", command],
                workdir="/mnt/repo",
                environment={
                    "MAVEN_OPTS": "-Xmx2g"
                }
            )
            
            output_text = output.decode('utf-8', errors='replace') if output else ""
            
            success = exit_code == 0
            
            if success:
                logger.info("OpenRewrite recipes executed successfully")
                # Log what was changed
                if "Made changes to" in output_text or "Results:" in output_text:
                    # Extract relevant lines
                    for line in output_text.split('\n'):
                        if 'Made changes' in line or 'Results' in line or 'rewrite' in line.lower():
                            logger.info(f"Rewrite: {line}")
            else:
                logger.error(f"OpenRewrite execution failed with exit code {exit_code}")
                # Log the last part of output which usually contains the error
                error_lines = output_text.split('\n')
                error_section = '\n'.join(error_lines[-50:])  # Last 50 lines
                logger.error(f"Error output (last 50 lines):\n{error_section}")
            
            return success, output_text, ""
            
        except Exception as e:
            logger.error(f"Error executing rewrite:run: {e}")
            return False, "", str(e)
    
    def run_rewrite_dry_run(self, maven_only: bool = True, timeout: int = 600) -> Tuple[bool, str, str]:
        """
        Execute 'mvn rewrite:dryRun' to preview changes without applying.
        
        Args:
            maven_only: If True, use flags to skip Java compilation (for pom.xml-only recipes)
            timeout: Maximum time in seconds to wait for the command
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        if self.container is None:
            raise RuntimeError("Container not started. Use start_container() context manager.")
        
        if maven_only:
            command = (
                "cd /mnt/repo && mvn rewrite:dryRun "
                "-Dmaven.main.skip=true -Dmaven.test.skip=true "
                "-Dcheckstyle.skip=true -Denforcer.skip=true "
                "-B"
            )
        else:
            command = "cd /mnt/repo && mvn rewrite:dryRun -B"
        
        logger.info(f"Executing dry run: {command}")
        
        try:
            exit_code, output = self.container.exec_run(
                cmd=["sh", "-c", command],
                workdir="/mnt/repo",
                environment={
                    "MAVEN_OPTS": "-Xmx2g"
                }
            )
            
            output_text = output.decode('utf-8', errors='replace') if output else ""
            
            success = exit_code == 0
            
            return success, output_text, ""
            
        except Exception as e:
            logger.error(f"Error executing rewrite:dryRun: {e}")
            return False, "", str(e)
    
    def compile_after_rewrite(self, timeout: int = 300) -> Tuple[bool, str]:
        """
        Compile the project after applying OpenRewrite recipes to verify fixes.
        
        Returns:
            Tuple of (compile_success, error_output)
        """
        if self.container is None:
            raise RuntimeError("Container not started. Use start_container() context manager.")
        
        command = "cd /mnt/repo && mvn compile -B -q"
        
        logger.info("Compiling project after rewrite...")
        
        try:
            exit_code, output = self.container.exec_run(
                cmd=["sh", "-c", command],
                workdir="/mnt/repo",
                environment={
                    "MAVEN_OPTS": "-Xmx2g"
                }
            )
            
            output_text = output.decode('utf-8', errors='replace') if output else ""
            
            success = exit_code == 0
            
            if success:
                logger.info("Compilation successful after rewrite")
            else:
                logger.warning(f"Compilation failed after rewrite: {output_text[:1000]}")
            
            return success, output_text
            
        except Exception as e:
            logger.error(f"Error during compilation: {e}")
            return False, str(e)
    
    def get_git_diff(self) -> str:
        """
        Get git diff of changes made by OpenRewrite.
        Uses GitPython on the local filesystem since the Maven Docker image doesn't have git.
        
        Returns:
            Git diff string
        """
        try:
            import git
            repo = git.Repo(self.project_path)
            diff = repo.git.diff()
            return diff
        except Exception as e:
            logger.error(f"Error getting git diff: {e}")
            return ""


class RecipeExecutorLocal:
    """
    Executes OpenRewrite recipes using local Maven installation.
    Use this for environments without Docker.
    """
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
    
    def run_rewrite(self, timeout: int = 600) -> Tuple[bool, str, str]:
        """
        Execute 'mvn rewrite:run' locally.
        """
        import subprocess
        
        try:
            result = subprocess.run(
                ["mvn", "rewrite:run", "-B"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)
    
    def compile_after_rewrite(self, timeout: int = 300) -> Tuple[bool, str]:
        """
        Compile the project after applying OpenRewrite recipes.
        """
        import subprocess
        
        try:
            result = subprocess.run(
                ["mvn", "compile", "-B", "-q"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            success = result.returncode == 0
            return success, result.stdout + result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
    
    def get_git_diff(self) -> str:
        """Get git diff of changes."""
        import subprocess
        
        try:
            result = subprocess.run(
                ["git", "diff"],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            return result.stdout
        except Exception as e:
            logger.error(f"Error getting git diff: {e}")
            return ""
