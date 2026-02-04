"""
JapiCmpAgent / REVAPI Agent
Generates API change summaries between old and new dependency versions.
Supports REVAPI (preferred) and JApiCmp via configurable tools.
"""

import os
import re
import json
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from app.core.config import settings


@dataclass
class DependencyChange:
    group_id: str
    artifact_id: str
    old_version: str
    new_version: str

    @property
    def old_coordinate(self) -> str:
        return f"{self.group_id}:{self.artifact_id}:{self.old_version}"

    @property
    def new_coordinate(self) -> str:
        return f"{self.group_id}:{self.artifact_id}:{self.new_version}"


class JapiCmpAgent:
    """Generate API change summaries for dependency upgrades using REVAPI or JApiCmp."""

    def __init__(self, tool_preference: Optional[str] = None, pipeline_logger=None):
        self.tool_preference = (tool_preference or settings.API_CHANGE_TOOL or "none").lower()
        self.revapi_home = settings.REVAPI_HOME
        self.revapi_executable = settings.REVAPI_EXECUTABLE or "revapi"
        self.revapi_args_template = settings.REVAPI_ARGS_TEMPLATE
        self.japicmp_jar_path = settings.JAPICMP_JAR_PATH
        self.japicmp_args_template = settings.JAPICMP_ARGS_TEMPLATE
        self.maven_executable = settings.MAVEN_EXECUTABLE or "mvn"
        self.pipeline_logger = pipeline_logger

    def generate_api_changes(self, repo_path: str, pom_diff: str, compilation_errors: str = "") -> str:
        """
        Generate API changes text based on pom.xml diff.
        Returns a human-readable string that can be injected into LLM prompt.
        
        Args:
            repo_path: Path to the repository
            pom_diff: Diff of pom.xml changes
            compilation_errors: Optional compilation errors to filter relevant API changes
        """
        changes = self._extract_dependency_changes(pom_diff)
        if not changes:
            return ""

        results = []
        for change in changes:
            tool_used, output, error = self._run_tool(change, repo_path, compilation_errors)
            header = f"{change.group_id}:{change.artifact_id} {change.old_version} -> {change.new_version}"
            if output:
                results.append(f"[{tool_used}] {header}\n{output}")
            else:
                error_msg = error or "No output"
                results.append(f"[{tool_used}] {header}\n{error_msg}")

        return "\n\n".join(results).strip()

    def _run_tool(self, change: DependencyChange, repo_path: str, compilation_errors: str = "") -> Tuple[str, str, str]:
        """
        Try preferred tool (REVAPI, JApiCmp). Returns (tool_used, output, error).
        Preference: revapi > japicmp
        """
        if self.tool_preference == "revapi":
            output, error = self._run_revapi(change, repo_path, compilation_errors)
            # Debug logging
            print(f"[DEBUG] REVAPI output length: {len(output)}, error: {repr(error)}")
            
            # Run JApiCmp as well (not as fallback, but for comparison)
            japicmp_output, japicmp_error = self._run_japicmp(change, repo_path, compilation_errors)
            print(f"[DEBUG] JApiCmp output length: {len(japicmp_output)}, error: {repr(japicmp_error)}")
            
            # Combine outputs if both succeeded
            combined_output = ""
            if output and not error:
                combined_output += f"=== REVAPI Analysis (Filtered) ===\n{output}\n\n"
            if japicmp_output and not japicmp_error:
                combined_output += f"=== JApiCmp Analysis (Filtered) ===\n{japicmp_output}"
            
            # If both failed, return error
            if not combined_output:
                return "none", "", f"REVAPI: {error}, JApiCmp: {japicmp_error}"
            
            # Determine which tool(s) were used
            if output and japicmp_output:
                tool_used = "revapi+japicmp"
            elif output:
                tool_used = "revapi"
            else:
                tool_used = "japicmp"
            
            # Log the combined filtered output that will be used in next stage
            self._log_api_changes(change, combined_output.strip(), tool_used)
            
            return tool_used, combined_output.strip(), ""

        if self.tool_preference == "japicmp":
            output, error = self._run_japicmp(change, repo_path, compilation_errors)
            # Successfully ran JApiCmp (even if no changes found)
            if not error or error == "":
                return "japicmp", output, error
            # JApiCmp failed, try REVAPI as fallback
            output, error = self._run_revapi(change, repo_path, compilation_errors)
            return "revapi", output, error

        # tool_preference == "none" or unknown
        return "none", "", "API change tool not configured"

    def _run_revapi(self, change: DependencyChange, repo_path: str, compilation_errors: str = "") -> Tuple[str, str]:
        """Run REVAPI to analyze API changes between old and new versions"""
        if not self.revapi_home:
            return "", "REVAPI_HOME not configured"

        # Check if revapi executable exists
        revapi_filename = "revapi.bat" if os.name == "nt" else "revapi"
        revapi_path = Path(self.revapi_home) / revapi_filename
        
        # If not in root, try bin subdirectory
        if not revapi_path.exists():
            revapi_path = Path(self.revapi_home) / "bin" / revapi_filename
        
        if not revapi_path.exists():
            return "", f"REVAPI executable not found at {self.revapi_home} or {self.revapi_home}/bin"

        # Use GAV coordinates instead of resolving JARs
        old_gav = change.old_coordinate
        new_gav = change.new_coordinate

        try:
            # Run revapi with GAVs
            # -e is REQUIRED: specifies the revapi extensions to use for analysis
            cmd = [
                str(revapi_path),
                "-e", "org.revapi:revapi-java:0.28.1,org.revapi:revapi-reporter-text:0.15.0",
                "-a", old_gav,
                "-b", new_gav,
                "-r", "https://repo.maven.apache.org/maven2/"
            ]
            output, error = self._run_command(cmd, repo_path)

            # Log raw REVAPI output before filtering
            if output:
                self._log_raw_output("revapi", change, output)
            
            # Filter and summarize REVAPI output to reduce token usage
            if output:
                summarized = self._summarize_revapi_output(output, compilation_errors)
                return summarized, ""
            
            return output, error
        except Exception as e:
            return "", str(e)

    def _summarize_revapi_output(self, raw_output: str, compilation_errors: str = "") -> str:
        """
        Summarize REVAPI output to only show truly BREAKING changes.
        If compilation_errors is provided, only show changes relevant to classes/methods in errors.
        Filters out EQUIVALENT and many POTENTIALLY_BREAKING changes to reduce token usage.
        """
        # Extract class/method names from compilation errors
        relevant_symbols = set()
        if compilation_errors:
            # STRICT filtering: only exact class and method names, no parent packages
            # Full qualified class names: com.package.ClassName
            fqcn_pattern = r'\b(com\.[\w.]+\.([A-Z][\w]+))\b'
            # Class names only (last part after dot)
            class_pattern = r'\b([A-Z][\w]{2,}(?:Exception|Response|Request|Client|Service|Builder|Model|Record|Traits|Error|Handler))\b'
            # Method names (must be followed by parentheses)
            method_pattern = r'\b([a-z][\w]+)\s*\('
            
            # Extract fully qualified class names
            for match in re.finditer(fqcn_pattern, compilation_errors):
                relevant_symbols.add(match.group(1))  # Full: com.package.ClassName
                relevant_symbols.add(match.group(2))  # Short: ClassName
            
            # Extract class names
            for match in re.finditer(class_pattern, compilation_errors):
                relevant_symbols.add(match.group(1))
            
            # Extract method names (only if they look like method calls)
            for match in re.finditer(method_pattern, compilation_errors):
                method_name = match.group(1)
                # Filter out common keywords that aren't actual methods
                if method_name not in {'if', 'for', 'while', 'switch', 'return', 'new', 'throw'}:
                    relevant_symbols.add(method_name)
        
        lines = raw_output.split('\n')
        filtered_breaking_changes = []
        current_change = []
        is_breaking = False
        is_relevant = not compilation_errors  # If no errors provided, all changes are relevant
        
        for line in lines:
            # Skip log lines and headers
            if any(x in line for x in ['INFO', 'WARN', 'Analysis results', 'Old API:', 'New API:', '---']):
                continue
            
            # Detect breaking severity
            if 'BINARY: BREAKING' in line or 'SOURCE: BREAKING' in line:
                is_breaking = True
            
            # Check if this change is relevant to our codebase
            if compilation_errors and relevant_symbols:
                for symbol in relevant_symbols:
                    if symbol in line:
                        is_relevant = True
                        break
            
            # Check if this is a new change entry (starts with 'old:' or 'new:')
            if line.strip().startswith('old:') or (line.strip().startswith('new:') and not current_change):
                # Save previous change if it was breaking and relevant
                if current_change and is_breaking and is_relevant:
                    filtered_breaking_changes.append('\n'.join(current_change))
                # Start new change
                current_change = [line]
                is_breaking = False
                is_relevant = not compilation_errors
            elif current_change:
                current_change.append(line)
        
        # Don't forget the last change
        if current_change and is_breaking and is_relevant:
            filtered_breaking_changes.append('\n'.join(current_change))
        
        if not filtered_breaking_changes:
            if compilation_errors:
                return "No breaking API changes detected for classes/methods used in your code"
            return "No breaking API changes detected"
        
        # Format concisely
        result = f"Breaking API changes affecting your code ({len(filtered_breaking_changes)} changes):\n\n"
        # Limit to 15 changes to save tokens
        result += "\n\n".join(filtered_breaking_changes[:15])
        
        if len(filtered_breaking_changes) > 15:
            result += f"\n\n... and {len(filtered_breaking_changes) - 15} more breaking changes"
        
        return result

    def _summarize_japicmp_output(self, raw_output: str, compilation_errors: str = "") -> str:
        """
        Summarize JApiCmp output to only show changes relevant to user's code.
        If compilation_errors is provided, only show changes relevant to classes/methods in errors.
        Filters out irrelevant changes to reduce token usage.
        """
        # Extract class/method names from compilation errors
        relevant_symbols = set()
        if compilation_errors:
            # STRICT filtering: only exact class and method names, no parent packages
            # Full qualified class names: com.package.ClassName
            fqcn_pattern = r'\b(com\.[\w.]+\.([A-Z][\w]+))\b'
            # Class names only (last part after dot)
            class_pattern = r'\b([A-Z][\w]{2,}(?:Exception|Response|Request|Client|Service|Builder|Model|Record|Traits|Error|Handler))\b'
            # Method names (must be followed by parentheses)
            method_pattern = r'\b([a-z][\w]+)\s*\('
            
            # Extract fully qualified class names
            for match in re.finditer(fqcn_pattern, compilation_errors):
                relevant_symbols.add(match.group(1))  # Full: com.package.ClassName
                relevant_symbols.add(match.group(2))  # Short: ClassName
            
            # Extract class names
            for match in re.finditer(class_pattern, compilation_errors):
                relevant_symbols.add(match.group(1))
            
            # Extract method names (only if they look like method calls)
            for match in re.finditer(method_pattern, compilation_errors):
                method_name = match.group(1)
                # Filter out common keywords that aren't actual methods
                if method_name not in {'if', 'for', 'while', 'switch', 'return', 'new', 'throw'}:
                    relevant_symbols.add(method_name)
        
        lines = raw_output.split('\n')
        filtered_changes = []
        current_class_section = []
        is_relevant_class = not compilation_errors  # If no errors provided, all changes are relevant
        
        for line in lines:
            # Skip warning and header lines
            if any(x in line for x in ['Comparing source compatibility', 'WARNING:', 'using the option']):
                continue
            
            # Detect start of a class section (MODIFIED/REMOVED/NEW CLASS)
            if 'CLASS:' in line:
                # Save previous class section if it was relevant
                if current_class_section and is_relevant_class:
                    # Filter out non-breaking changes within this class
                    filtered_section = self._filter_japicmp_class_section(current_class_section)
                    if filtered_section:
                        filtered_changes.append(filtered_section)
                
                # Start new class section
                current_class_section = [line]
                is_relevant_class = not compilation_errors
                
                # Check if this class is relevant to our codebase
                if compilation_errors and relevant_symbols:
                    for symbol in relevant_symbols:
                        if symbol in line:
                            is_relevant_class = True
                            break
            elif current_class_section:
                # Add line to current class section
                current_class_section.append(line)
                
                # Also check if individual methods/fields are relevant
                if compilation_errors and relevant_symbols and not is_relevant_class:
                    for symbol in relevant_symbols:
                        if symbol in line:
                            is_relevant_class = True
                            break
        
        # Don't forget the last class section
        if current_class_section and is_relevant_class:
            filtered_section = self._filter_japicmp_class_section(current_class_section)
            if filtered_section:
                filtered_changes.append(filtered_section)
        
        if not filtered_changes:
            if compilation_errors:
                return "No breaking API changes detected for classes/methods used in your code"
            return "No breaking API changes detected"
        
        # Format concisely
        result = f"Breaking API changes affecting your code ({len(filtered_changes)} classes):\n\n"
        result += "\n".join(filtered_changes)
        
        return result

    def _filter_japicmp_class_section(self, section_lines: List[str]) -> str:
        """
        Filter a JApiCmp class section to only show breaking changes.
        Removes: CLASS FILE FORMAT VERSION changes, UNCHANGED items, non-breaking additions
        Keeps: REMOVED constructors/methods, MODIFIED methods with signature changes, breaking annotations
        """
        filtered = []
        for line in section_lines:
            # Keep the class header
            if 'CLASS:' in line:
                # Only keep if it has breaking markers
                if any(marker in line for marker in ['***!', '---!']):
                    filtered.append(line)
                elif '***' in line and 'MODIFIED CLASS:' in line:
                    # Keep MODIFIED CLASS even without !, we'll see what's inside
                    filtered.append(line)
                continue
            
            # Skip CLASS FILE FORMAT VERSION changes (not API breaking)
            if 'CLASS FILE FORMAT VERSION:' in line:
                continue
            
            # Skip serializable changes (usually not API breaking)
            if '(not serializable)' in line:
                continue
            
            # Skip UNCHANGED items
            if '===' in line and 'UNCHANGED' in line:
                continue
            
            # Keep REMOVED items (---! prefix)
            if '---!' in line:
                filtered.append(line)
                continue
            
            # Keep MODIFIED items (***! prefix)
            if '***!' in line:
                filtered.append(line)
                continue
            
            # Keep NEW items only if they're replacing old ones or are deprecations
            if '+++' in line:
                if 'NEW ANNOTATION: java.lang.Deprecated' in line:
                    filtered.append(line)
                # Skip other new additions as they're not breaking
                continue
            
            # Keep indented lines that follow REMOVED/MODIFIED items
            if line.strip().startswith('---'):
                # Removed annotation
                filtered.append(line)
        
        # Only return the section if it has actual breaking changes (not just the header)
        if len(filtered) <= 1:
            return ""
        
        return "\n".join(filtered)

    def _format_revapi_output(self, revapi_data: dict) -> str:
        """Format REVAPI JSON output into human-readable text"""
        if not revapi_data:
            return ""

        lines = []
        
        # Handle errors array if present
        errors = revapi_data.get("errors", [])
        if errors:
            for error in errors:
                code = error.get("code", "")
                message = error.get("message", "")
                severity = error.get("severity", "info")
                old = error.get("old", {})
                new = error.get("new", {})

                old_name = old.get("name", "") if isinstance(old, dict) else str(old)
                new_name = new.get("name", "") if isinstance(new, dict) else str(new)

                if code:
                    lines.append(f"[{severity.upper()}] {code}")
                if message:
                    lines.append(f"  Message: {message}")
                if old_name:
                    lines.append(f"  Old: {old_name}")
                if new_name:
                    lines.append(f"  New: {new_name}")
                lines.append("")

        if lines:
            return "\n".join(lines).strip()
        
        return "No breaking API changes detected"

    def _run_japicmp(self, change: DependencyChange, repo_path: str, compilation_errors: str = "") -> Tuple[str, str]:
        """Run JApiCmp to compare JAR files"""
        if not self.japicmp_jar_path:
            return "", "JApiCmp jar path not configured"

        old_jar = self._resolve_jar(change.group_id, change.artifact_id, change.old_version, repo_path)
        new_jar = self._resolve_jar(change.group_id, change.artifact_id, change.new_version, repo_path)

        if not old_jar or not new_jar:
            return "", "Could not resolve old/new jar files"

        args_template = self.japicmp_args_template or "--old {old_jar} --new {new_jar} --only-modified --ignore-missing-classes"
        args = args_template.format(
            old_jar=str(old_jar),
            new_jar=str(new_jar),
            group_id=change.group_id,
            artifact_id=change.artifact_id,
            old_version=change.old_version,
            new_version=change.new_version,
        )
        cmd = ["java", "-jar", self.japicmp_jar_path] + shlex.split(args, posix=os.name != "nt")

        output, error = self._run_command(cmd, repo_path)
        
        # Log raw JApiCmp output before filtering
        if output:
            self._log_raw_output("japicmp", change, output)
        
        # Filter and summarize JApiCmp output to reduce token usage
        if output:
            summarized = self._summarize_japicmp_output(output, compilation_errors)
            return summarized, ""
        
        return output, error

    def _run_command(self, cmd: List[str], repo_path: str) -> Tuple[str, str]:
        """Execute a command and return stdout/stderr"""
        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=180,
            )
            if result.returncode != 0:
                stderr = (result.stderr or "").strip()
                return "", stderr or f"Command failed with exit code {result.returncode}"

            stdout = (result.stdout or "").strip()
            return stdout, ""
        except Exception as e:
            return "", str(e)

    def _resolve_jar(self, group_id: str, artifact_id: str, version: str, repo_path: str) -> Optional[Path]:
        """Resolve JAR file from Maven local repository, downloading if necessary"""
        m2_repo = Path.home() / ".m2" / "repository"
        jar_path = (
            m2_repo
            / Path(group_id.replace(".", "/"))
            / artifact_id
            / version
            / f"{artifact_id}-{version}.jar"
        )

        if jar_path.exists():
            return jar_path

        if not shutil.which(self.maven_executable):
            return None

        # Try to download the artifact
        try:
            cmd = [
                self.maven_executable,
                "-q",
                "dependency:get",
                f"-Dartifact={group_id}:{artifact_id}:{version}",
                "-Dtransitive=false",
            ]
            subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=120)
        except Exception:
            return None

        return jar_path if jar_path.exists() else None

    def _extract_dependency_changes(self, pom_diff: str) -> List[DependencyChange]:
        """Extract dependency version changes from pom.xml diff"""
        if not pom_diff:
            return []

        group_id = None
        artifact_id = None
        old_version = None
        new_version = None
        in_dependency = False

        changes: List[DependencyChange] = []

        for raw_line in pom_diff.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # Remove diff markers
            if line and line[0] in {"+", "-", " "}:
                content = line[1:].strip()
            else:
                content = line

            if "<dependency>" in content:
                in_dependency = True

            if in_dependency:
                group_match = re.search(r"<groupId>(.*?)</groupId>", content)
                if group_match:
                    group_id = group_match.group(1)

                artifact_match = re.search(r"<artifactId>(.*?)</artifactId>", content)
                if artifact_match:
                    artifact_id = artifact_match.group(1)

                if line.startswith("-") and "<version>" in content:
                    old_match = re.search(r"<version>(.*?)</version>", content)
                    if old_match:
                        old_version = old_match.group(1)

                if line.startswith("+") and "<version>" in content:
                    new_match = re.search(r"<version>(.*?)</version>", content)
                    if new_match:
                        new_version = new_match.group(1)

            if "</dependency>" in content:
                if group_id and artifact_id and old_version and new_version:
                    changes.append(
                        DependencyChange(
                            group_id=group_id,
                            artifact_id=artifact_id,
                            old_version=old_version,
                            new_version=new_version,
                        )
                    )
                group_id = None
                artifact_id = None
                old_version = None
                new_version = None
                in_dependency = False

        # Handle diffs without closing tag in context
        if group_id and artifact_id and old_version and new_version:
            changes.append(
                DependencyChange(
                    group_id=group_id,
                    artifact_id=artifact_id,
                    old_version=old_version,
                    new_version=new_version,
                )
            )

        return changes

    def _log_raw_output(self, tool_name: str, change: DependencyChange, output: str) -> None:
        """Log raw tool output to a file for debugging"""
        if not self.pipeline_logger:
            return
        
        try:
            artifact_name = f"{change.group_id}:{change.artifact_id}"
            version_change = f"{change.old_version} -> {change.new_version}"
            
            self.pipeline_logger.log_api_tool_raw(
                tool_name=tool_name,
                artifact=artifact_name,
                version_change=version_change,
                output=output
            )
        except Exception as e:
            print(f"[WARNING] Failed to log {tool_name} raw output: {e}")

    def _log_api_changes(self, change: DependencyChange, filtered_output: str, tool_used: str) -> None:
        """Log the filtered API changes that will be used in the next stage"""
        if not self.pipeline_logger:
            return
        
        try:
            artifact_name = f"{change.group_id}:{change.artifact_id}"
            version_change = f"{change.old_version} -> {change.new_version}"
            
            self.pipeline_logger.log_api_changes_filtered(
                tool_used=tool_used,
                artifact=artifact_name,
                version_change=version_change,
                filtered_output=filtered_output
            )
        except Exception as e:
            print(f"[WARNING] Failed to log API changes: {e}")
