"""
Recipe Executor
Executes OpenRewrite recipes using Maven in a Docker container.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Tuple
from contextlib import contextmanager

from app.config.config import settings
from app.utilities.logger import logger
from app.tools.agents.DockerAgent import DockerAgent


def _truncate_terminal_output(output: str, max_chars: int = 12000) -> str:
    """Keep terminal logs readable while preserving the most relevant trailing output."""
    if len(output) <= max_chars:
        return output
    return "[...output truncated...]\n" + output[-max_chars:]


def _summarize_maven_output(output: str, exit_code: int, context: str) -> str:
    """Build a concise summary of Maven output for terminal logs."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return f"{context}: exit={exit_code}, no output"

    key_markers = (
        "BUILD SUCCESS",
        "BUILD FAILURE",
        "[ERROR]",
        "[WARNING]",
        "Made changes",
        "Results:",
        "Active recipe",
    )
    key_lines = [line for line in lines if any(marker in line for marker in key_markers)]
    key_lines = key_lines[:8]
    tail_lines = lines[-8:]

    summary_parts = [
        f"{context}: exit={exit_code}, total_lines={len(lines)}",
    ]

    if key_lines:
        summary_parts.append("Key lines:")
        summary_parts.extend(f"- {line}" for line in key_lines)

    summary_parts.append("Tail:")
    summary_parts.extend(f"- {line}" for line in tail_lines)

    return "\n".join(summary_parts)

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
        self.m2_cache_dir = self._resolve_m2_cache_dir()
        logger.info(f"[RecipeExecutor] Initialized with project at {self.project_path}, results dir: {self.results_dir}")
        logger.info(f"[RecipeExecutor] Initialized with project at {self.project_path}, results dir: {self.results_dir}")

    def _resolve_m2_cache_dir(self) -> str:
        configured = settings.MAVEN_DOCKER_CACHE_DIR
        cache_dir = Path(configured) if configured else Path.home() / ".aura" / "m2-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return str(cache_dir)

    def _maven_exec_env(self) -> dict[str, str]:
        return {"MAVEN_OPTS": settings.MAVEN_DOCKER_OPTS or "-Xmx2g"}

    def _maven_common_flags(self) -> str:
        threads = settings.MAVEN_DOCKER_THREADS or "1C"
        return "-B -ntp -nsu -Dmaven.repo.local=/mnt/m2/repository -T " + threads
    
    @contextmanager
    def start_container(self):
        """Context manager to handle container lifecycle."""
        try:
            logger.info(f"[RecipeExecutor] Starting Docker container with image {self.MAVEN_IMAGE}...")
            container, setup_stdout, setup_stderr = (
                self.docker_agent.execute_command_with_mounts(
                    mounts={
                        str(self.project_path): {"bind": "/mnt/repo", "mode": "rw"},
                        self.results_dir: {"bind": "/mnt/data", "mode": "rw"},
                        self.m2_cache_dir: {"bind": "/mnt/m2", "mode": "rw"},
                    },
                    setup_command="mkdir -p /app /mnt/m2/repository",
                )
            )
            self.container = container
            logger.info(f"[RecipeExecutor] Docker container started successfully")
            yield self.container
        finally:
            if self.container is not None:
                logger.info(f"[RecipeExecutor] Cleaning up Docker container...")
                self.docker_agent.clean_up(self.container)
            else:
                self.docker_agent.clean_up()
            
            if os.path.exists(self.results_dir):
                shutil.rmtree(self.results_dir)
            logger.info(f"[RecipeExecutor] Container cleanup complete")
            logger.info(f"[RecipeExecutor] Container cleanup complete")
    
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
        discover_cmd = (
            "cd /mnt/repo && mvn rewrite:discover "
            f"{self._maven_common_flags()} 2>&1 | tail -100"
        )
        logger.info(f"Discovering recipes: {discover_cmd}")
        
        try:
            exit_code, discover_output = self.container.exec_run(
                cmd=["sh", "-c", discover_cmd],
                workdir="/mnt/repo",
                environment=self._maven_exec_env()
            )
            discover_text = discover_output.decode('utf-8', errors='replace') if discover_output else ""
            logger.info(f"Recipe discovery result (exit={exit_code}):\n{discover_text[-1500:]}")
            logger.info(
                "[RecipeExecutor][Terminal] %s",
                _summarize_maven_output(discover_text, exit_code, "mvn rewrite:discover"),
            )
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
                f"{self._maven_common_flags()} 2>&1"
            )
        else:
            # For Java recipes, we need full compilation - but this won't work on broken projects
            # This is a known limitation - Java recipes require compilable code
            command = (
                "cd /mnt/repo && mvn org.openrewrite.maven:rewrite-maven-plugin:5.43.0:run "
                f"{self._maven_common_flags()} 2>&1"
            )
        
        logger.info(f"Executing: {command}")
        
        try:
            exit_code, output = self.container.exec_run(
                cmd=["sh", "-c", command],
                workdir="/mnt/repo",
                environment=self._maven_exec_env()
            )
            
            output_text = output.decode('utf-8', errors='replace') if output else ""
            
            success = exit_code == 0
            logger.info(
                "[RecipeExecutor][Terminal] %s",
                _summarize_maven_output(output_text, exit_code, "mvn rewrite:run"),
            )
            
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
                f"{self._maven_common_flags()}"
            )
        else:
            command = f"cd /mnt/repo && mvn rewrite:dryRun {self._maven_common_flags()}"
        
        logger.info(f"Executing dry run: {command}")
        
        try:
            exit_code, output = self.container.exec_run(
                cmd=["sh", "-c", command],
                workdir="/mnt/repo",
                environment=self._maven_exec_env()
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
        
        command = f"cd /mnt/repo && mvn compile {self._maven_common_flags()} -q"
        
        logger.info("Compiling project after rewrite...")
        
        try:
            exit_code, output = self.container.exec_run(
                cmd=["sh", "-c", command],
                workdir="/mnt/repo",
                environment=self._maven_exec_env()
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
        logger.info(f"[RecipeExecutorLocal] Initialized with project at {self.project_path}")
    
    def run_rewrite(self, timeout: int = 600) -> Tuple[bool, str, str]:
        """
        Execute 'mvn rewrite:run' locally.
        """
        import subprocess
        
        logger.info(f"[RecipeExecutorLocal] Running mvn rewrite:run in {self.project_path}...")
        try:
            result = subprocess.run(
                ["mvn", "rewrite:run","-Drewrite.skipMavenCompile=true", "-B"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            success = result.returncode == 0
            combined_output = (
                f"STDOUT:\n{result.stdout or ''}\n\n"
                f"STDERR:\n{result.stderr or ''}"
            )
            logger.info(
                "[RecipeExecutorLocal][Terminal] %s",
                _summarize_maven_output(combined_output, result.returncode, "mvn rewrite:run"),
            )
            if success:
                logger.info(f"[RecipeExecutorLocal] mvn rewrite:run completed successfully")
            else:
                logger.warning(f"[RecipeExecutorLocal] mvn rewrite:run failed with return code {result.returncode}")
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            logger.error(f"[RecipeExecutorLocal] mvn rewrite:run timed out after {timeout}s")
            return False, "", "Command timed out"
        except Exception as e:
            logger.error(f"[RecipeExecutorLocal] mvn rewrite:run error: {e}")
            return False, "", str(e)
    
    def compile_after_rewrite(self, timeout: int = 300) -> Tuple[bool, str]:
        """
        Compile the project after applying OpenRewrite recipes.
        """
        import subprocess
        
        logger.info(f"[RecipeExecutorLocal] Compiling project in {self.project_path}...")
        try:
            result = subprocess.run(
                ["mvn", "compile", "-B", "-q"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            success = result.returncode == 0
            if success:
                logger.info(f"[RecipeExecutorLocal] Compilation successful")
            else:
                logger.warning(f"[RecipeExecutorLocal] Compilation failed with return code {result.returncode}")
            return success, result.stdout + result.stderr
            
        except subprocess.TimeoutExpired:
            logger.error(f"[RecipeExecutorLocal] Compilation timed out after {timeout}s")
            return False, "Command timed out"
        except Exception as e:
            logger.error(f"[RecipeExecutorLocal] Compilation error: {e}")
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
