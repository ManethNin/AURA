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

from app.config.config import settings


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

    def generate_api_changes_with_raw(self, repo_path: str, pom_diff: str, compilation_errors: str = "") -> dict:
        """
        Generate API changes with BOTH raw and filtered outputs.
        Returns a dict with 'raw' and 'filtered' keys for explicit logging.
        
        Args:
            repo_path: Path to the repository
            pom_diff: Diff of pom.xml changes
            compilation_errors: Optional compilation errors to filter relevant API changes
            
        Returns:
            dict with:
                - raw: Full unfiltered API changes from the tool
                - filtered: Summarized/filtered API changes for LLM
                - tool_used: Which tool was used (revapi, japicmp, etc.)
        """
        changes = self._extract_dependency_changes(pom_diff)
        if not changes:
            return {"raw": "", "filtered": "", "tool_used": "none"}

        raw_results = []
        filtered_results = []
        tools_used = set()
        
        for change in changes:
            tool_used, output, error = self._run_tool(change, repo_path, compilation_errors)
            tools_used.add(tool_used)
            header = f"{change.group_id}:{change.artifact_id} {change.old_version} -> {change.new_version}"
            
            if output:
                raw_results.append(f"[{tool_used}] {header}\n{output}")
                filtered_results.append(f"[{tool_used}] {header}\n{output}")
            else:
                error_msg = error or "No output"
                raw_results.append(f"[{tool_used}] {header}\n{error_msg}")
                filtered_results.append(f"[{tool_used}] {header}\n{error_msg}")

        return {
            "raw": "\n\n".join(raw_results).strip(),
            "filtered": "\n\n".join(filtered_results).strip(),
            "tool_used": ", ".join(sorted(tools_used))
        }

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

    def _extract_maven_symbols(self, compilation_errors: str) -> tuple[set, set, set]:
        """
        Extract three distinct symbol sets from Maven compilation errors.
        Returns: (missing_classes, missing_packages, fully_qualified_refs)
        """
        missing_classes = set()
        missing_packages = set()
        fq_refs = set()  # e.g. "com.hazelcast.core.Member"

        # Pattern 1: "package com.hazelcast.monitor does not exist"
        for match in re.finditer(r'package\s+([\w.]+)\s+does not exist', compilation_errors):
            missing_packages.add(match.group(1))

        # Pattern 2: "[ERROR]   symbol:   class MaxSizeConfig"  (the indented symbol line)
        for match in re.finditer(r'symbol:\s+class\s+([A-Z]\w+)', compilation_errors):
            missing_classes.add(match.group(1))

        # Pattern 3: "[ERROR]   location: package com.hazelcast.config"
        # Pair these with the symbol line above them to build FQNs
        lines = compilation_errors.splitlines()
        last_class = None
        for line in lines:
            sym = re.search(r'symbol:\s+class\s+([A-Z]\w+)', line)
            if sym:
                last_class = sym.group(1)
            loc = re.search(r'location:\s+(?:class|package)\s+([\w.]+)', line)
            if loc and last_class:
                fq_refs.add(f"{loc.group(1)}.{last_class}")
                last_class = None  # consume it

        return missing_classes, missing_packages, fq_refs

    def _summarize_revapi_output(self, raw_output: str, compilation_errors: str = "") -> str:
        """
        Filter RevAPI output to only changes that explain the Maven compilation errors.
        """
        missing_classes, missing_packages, fq_refs = set(), set(), set()

        if compilation_errors:
            missing_classes, missing_packages, fq_refs = self._extract_maven_symbols(compilation_errors)

        use_strict_filter = bool(missing_classes or missing_packages)

        lines = raw_output.split('\n')
        filtered_changes = []
        current_change = []
        current_old_line = ""
        current_new_line = ""
        is_breaking = False

        for line in lines:
            if any(x in line for x in ['INFO', 'WARN', 'Analysis results', 'Old API:', 'New API:']):
                continue

            stripped = line.strip()

            if stripped.startswith('old:') or (stripped.startswith('new:') and not current_change):
                # Flush previous change
                if current_change and is_breaking:
                    if not use_strict_filter or self._is_relevant_change(current_old_line, current_new_line,
                             missing_packages, missing_classes,
                             fq_refs, use_strict_filter):
                        filtered_changes.append('\n'.join(current_change))

                current_change = [line]
                current_old_line = stripped if stripped.startswith('old:') else ""
                current_new_line = stripped if stripped.startswith('new:') else ""
                is_breaking = False
            elif current_change:
                current_change.append(line)
                if stripped.startswith('old:'):
                    current_old_line = stripped
                elif stripped.startswith('new:'):
                    current_new_line = stripped
                if 'BINARY: BREAKING' in line or 'SOURCE: BREAKING' in line:
                    is_breaking = True

        # Flush last change
        if current_change and is_breaking:
            if not use_strict_filter or self._is_relevant_change(
                current_old_line, current_new_line,
                missing_packages, missing_classes, fq_refs, use_strict_filter
            ):
                filtered_changes.append('\n'.join(current_change))

        if not filtered_changes:
            return (
                "No RevAPI changes matched the missing symbols.\n"
                f"Searched for classes: {sorted(missing_classes)}\n"
                f"Searched for packages: {sorted(missing_packages)}"
                if compilation_errors else
                "No breaking API changes detected"
            )

        result = ""
        if missing_packages:
            result += f"Missing packages: {', '.join(sorted(missing_packages))}\n"
        if missing_classes:
            result += f"Missing classes:  {', '.join(sorted(missing_classes))}\n"
        if fq_refs:
            result += f"Reconstructed FQNs: {', '.join(sorted(fq_refs))}\n"

        result += f"\nRelevant API changes ({len(filtered_changes)} found):\n\n"
        result += "\n\n".join(filtered_changes[:10])

        if len(filtered_changes) > 10:
            result += f"\n\n... and {len(filtered_changes) - 10} more related changes"

        return result
    
    def _is_relevant_change(
        self,
        old_line: str,
        new_line: str,
        missing_packages: set,
        missing_classes: set,
        fq_refs: set,        # replaces error_file_paths — reconstructed FQNs from maven
        strict: bool
    ) -> bool:
        """
        Check if a RevAPI change is relevant to the compilation errors.

        Matching priority (highest confidence first):
        1. Reconstructed FQN match — e.g. "com.hazelcast.core.Member"
        2. Package prefix match    — e.g. "com.hazelcast.monitor"
        3. Simple class name match — e.g. "Member" (word boundary, fallback only)

        Checks both old: and new: lines, because a moved class shows its
        original location in old: and its new location in new:.
        """
        if not old_line:
            return False

        if not strict:
            # Don't silently return nothing — caller should log a warning
            # if this path is hit unexpectedly
            return False

        old_content = old_line[4:].strip()   # strip "old:" prefix
        new_content = new_line[4:].strip() if new_line.startswith('new:') else ""

        # 1. FQN match — most precise, check both old and new
        for fqn in fq_refs:
            if fqn in old_content or fqn in new_content:
                return True

        # 2. Package prefix match — "com.hazelcast.monitor" in old FQN
        for pkg in missing_packages:
            pkg_prefix = f'{pkg}.'
            for content in (old_content, new_content):
                if (
                    pkg_prefix in content
                    or content.endswith(f' {pkg}')
                    or re.search(rf'\b{re.escape(pkg)}\.[A-Z]\w*', content)
                ):
                    return True

        # 3. Simple class name — word boundary on both sides to avoid
        #    "Member" matching "MembershipListener" or "TeamMember"
        for cls in missing_classes:
            pattern = rf'(?<![A-Za-z]){re.escape(cls)}(?![A-Za-z])'
            if re.search(pattern, old_content) or re.search(pattern, new_content):
                return True

        return False

    def _summarize_japicmp_output(self, raw_output: str, compilation_errors: str = "") -> str:
        """
        Summarize JApiCmp output to show only changes directly causing the compilation errors.
        
        Extracts specific missing symbols from Maven compilation errors and filters
        JApiCmp changes to only show API changes that affect those symbols.
        """
        missing_packages = set()
        missing_classes = set()
        
        if compilation_errors:
            # Extract missing packages from "package X does not exist" errors
            package_pattern = r'package\s+([\w.$]+)\s+does not exist'
            for match in re.finditer(package_pattern, compilation_errors):
                pkg = match.group(1)
                if '.' in pkg:
                    missing_packages.add(pkg)
            
            # Extract missing class names from "cannot find symbol" errors
            symbol_class_pattern = r'symbol:\s*(?:class|method|variable)\s+([A-Z]\w*)'
            for match in re.finditer(symbol_class_pattern, compilation_errors):
                cls = match.group(1)
                if cls not in ('class', 'method', 'variable', 'type', 'annotation'):
                    missing_classes.add(cls)
            
            # Extract class names from the line after "cannot find symbol"
            standalone_class_pattern = r'^\s*\[ERROR\]\s+class\s+([A-Z]\w*)'
            for match in re.finditer(standalone_class_pattern, compilation_errors, re.MULTILINE):
                missing_classes.add(match.group(1))
        
        use_strict_filter = bool(missing_packages or missing_classes)
        
        lines = raw_output.split('\n')
        filtered_changes = []
        current_class_section = []
        current_class_name = ""
        
        for line in lines:
            # Skip warning and header lines
            if any(x in line for x in ['Comparing source compatibility', 'WARNING:', 'using the option']):
                continue
            
            # Detect start of a class section (MODIFIED/REMOVED/NEW CLASS)
            if 'CLASS:' in line:
                # Save previous class section if it was relevant
                if current_class_section:
                    if self._is_relevant_japicmp_class(current_class_name, missing_packages, missing_classes, use_strict_filter):
                        filtered_section = self._filter_japicmp_class_section(current_class_section)
                        if filtered_section:
                            filtered_changes.append(filtered_section)
                
                # Start new class section
                current_class_section = [line]
                current_class_name = line
            elif current_class_section:
                current_class_section.append(line)
        
        # Don't forget the last class section
        if current_class_section:
            if self._is_relevant_japicmp_class(current_class_name, missing_packages, missing_classes, use_strict_filter):
                filtered_section = self._filter_japicmp_class_section(current_class_section)
                if filtered_section:
                    filtered_changes.append(filtered_section)
        
        if not filtered_changes:
            if compilation_errors:
                return "No breaking API changes detected for the missing packages/classes"
            return "No breaking API changes detected"
        
        # Format concisely
        result = ""
        if missing_packages:
            result = f"Missing package(s): {', '.join(sorted(missing_packages))}\n"
        if missing_classes:
            result += f"Missing class(es): {', '.join(sorted(missing_classes))}\n"
        
        result += f"\nRelevant class changes ({len(filtered_changes)} found):\n\n"
        result += "\n".join(filtered_changes[:10])
        
        if len(filtered_changes) > 10:
            result += f"\n\n... and {len(filtered_changes) - 10} more related changes"
        
        return result
    
    def _is_relevant_japicmp_class(self, class_line: str, missing_packages: set, missing_classes: set, strict: bool) -> bool:
        """Check if a JApiCmp class section is relevant to the compilation errors."""
        if not class_line:
            return False
        
        if not strict:
            return False
        
        # Extract the fully-qualified class name from the JApiCmp line
        # Format: "com.example.MyClass *** REMOVED CLASS"
        # Extract just the class name part before the markers
        class_name_part = class_line.split('***')[0].split('---')[0].strip()
        
        # Check for exact package match (package prefix match)
        for pkg in missing_packages:
            if re.search(rf'\b{re.escape(pkg)}\.[A-Z]\w*', class_name_part):
                return True
        
        # Check for exact class name match (must be part of a fully-qualified name)
        for cls in missing_classes:
            if re.search(rf'\b{re.escape(cls)}\b', class_name_part):
                return True
        
        return False

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
                timeout=600,
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

        maven_exec = shutil.which(self.maven_executable)
        if not maven_exec:
            return None

        # Try to download the artifact
        try:
            cmd = [
                maven_exec,
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
