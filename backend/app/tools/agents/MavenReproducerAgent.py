import logging
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Tuple

from app.tools.agents.aider.AdvancedDiffAgent import UnifiedDiffCoder
from app.tools.agents.DockerAgent import DockerAgent
from app.tools.agents.LSPAgent import extract_error_lines


class MavenReproducerAgent:
    INITIAL_ERROR_SCAN_FLAGS = (
        " -Dcheckstyle.skip=true"
        " -Dmaven.remote.resources.skip=true"
        " -Dpmd.skip=true"
        " -Dspotbugs.skip=true"
        " -Dfindbugs.skip=true"
    )
    NORMALIZE_JAVA_LINE_ENDINGS_CMD = (
        "if [ -d /mnt/repo/src ]; then "
        "find /mnt/repo/src -name \"*.java\" -exec sed -i 's/\\r//' {} +; "
        "fi"
    )

    def __init__(self, project_path: Path) -> None:

        self.dockerAgent = DockerAgent("maven:3.9.8-amazoncorretto-17", project_path)

        self.project_path = project_path

        self.container = None

        self.force_upgrade_compiler_version = False
        self.compiler_upgrade_attempted = False

        self.repo_dir = project_path
        self.results_dir = tempfile.mkdtemp()
        self.input_dir = tempfile.mkdtemp()

    @contextmanager
    def start_container(self):
        # self.dockerAgent.pull_image()
        try:
            container, setup_stdout, setup_stderr = (
                self.dockerAgent.execute_command_with_mounts(
                    mounts={
                        self.repo_dir: {"bind": "/mnt/repo", "mode": "rw"},
                        self.results_dir: {
                            "bind": "/mnt/data",
                            "mode": "rw",
                        },
                        self.input_dir: {"bind": "/mnt/input", "mode": "rw"},
                    },
                    setup_command="mkdir -p /app",
                )
            )
            print("repo at", self.repo_dir)
            # Todo: validate setup_stdout and setup_stderr
            self.container = container
            yield self.container
        finally:
            if self.container is not None:
                self.dockerAgent.clean_up(self.container)
            else:
                self.dockerAgent.clean_up()

            if os.path.exists(self.results_dir):
                shutil.rmtree(self.results_dir)
            if os.path.exists(self.input_dir):
                shutil.rmtree(self.input_dir)
            # print("Skipped cleanup!")

    def compile_maven_with_full_file_replace(
        self,
        file_content: str,
        file_path: str,
        run_tests: bool = True,
        timeout: int = 1800,
        collect_all_errors: bool = False,
        errors_only: bool = False,
        initial_error_scan: bool = False,
    ) -> Tuple[Tuple[bool, bool], str, dict]:
        with open(file_path, "w", encoding="utf-8") as out_file_wrapper:
            out_file_wrapper.write(file_content)

        (compile, test), error_text = self._compile_maven(
            run_tests,
            timeout,
            collect_all_errors=collect_all_errors,
            errors_only=errors_only,
            initial_error_scan=initial_error_scan,
        )

        return (compile, test), error_text, {file_path: file_content}

    def compile_maven(
        self,
        diffs: list[str],
        run_tests: bool,
        timeout: int = 1800,
        collect_all_errors: bool = False,
        errors_only: bool = False,
        initial_error_scan: bool = False,
    ) -> Tuple[Tuple[bool, bool], str, dict]:

        assert self.container is not None, "Container is not initialized"

        assert isinstance(diffs, list), "Diffs are not a list"

        updated_files = {}
        try:
            coder = UnifiedDiffCoder(repo_dir=self.repo_dir)
            for diff_text in diffs:
                is_valid_diff, patched_files = coder.apply_edits(diff_text)

                assert is_valid_diff, f"Diff is not valid, {patched_files}"

                for path, patched_file in patched_files.items():

                    output_location = Path(self.repo_dir) / path

                    updated_files[path] = patched_file

                    with open(
                        output_location, "w", encoding="utf-8"
                    ) as out_file_wrapper:
                        out_file_wrapper.write(patched_file)
        except Exception as e:
            return (False, False), f"Failed to prepare diffs: {e}", {}

        (compile, test), error_text = self._compile_maven(
            run_tests,
            timeout,
            collect_all_errors=collect_all_errors,
            errors_only=errors_only,
            initial_error_scan=initial_error_scan,
        )

        return (compile, test), error_text, updated_files

    def _compile_maven(
        self,
        run_tests: bool,
        timeout: int = 1800,
        collect_all_errors: bool = False,
        errors_only: bool = False,
        initial_error_scan: bool = False,
    ) -> Tuple[Tuple[bool, bool], str]:
        try:
            reproduction_command = "mvn clean test -Dsurefire.printSummary=true -Dsurefire.redirectTestOutputToFile=false"

            if self.force_upgrade_compiler_version:
                reproduction_command += " -Dmaven.compiler.source=8 -Dmaven.compiler.target=8 -Dmaven.compiler.release=8 -Dmaven.compiler.testSource=8 -Dmaven.compiler.testTarget=8"

            reproduction_command += " -B"

            if collect_all_errors:
                reproduction_command += " -fn"

            if not run_tests:
                reproduction_command = "mvn clean compile -DskipTests -B"
                if collect_all_errors:
                    reproduction_command += " -fn"

            if initial_error_scan:
                reproduction_command += self.INITIAL_ERROR_SCAN_FLAGS

            wrapped_command = (
                f"{self.NORMALIZE_JAVA_LINE_ENDINGS_CMD} && {reproduction_command}"
            )
            timeout_command = f"timeout -k 10s {timeout}s sh -c \"{wrapped_command}\""

            print(f"Running maven command {timeout_command}")
            output_code, docker_output = self.dockerAgent.execute_command(
                self.container, timeout_command, "/mnt/repo"
            )
            print("maven output_code", output_code)
            # logging.info("docker_output %s", docker_output)
            # print("docker_output", output_code, docker_output)

            if (
                "Source option 6 is no longer supported. Use 7 or later."
                in docker_output
                and not self.compiler_upgrade_attempted
            ):
                self.force_upgrade_compiler_version = True
                self.compiler_upgrade_attempted = True
                return self._compile_maven(
                    run_tests,
                    timeout,
                    collect_all_errors=collect_all_errors,
                    errors_only=errors_only,
                    initial_error_scan=initial_error_scan,
                )

            self.compiler_upgrade_attempted = False

            if (
                int(output_code) == 124
                or int(output_code) == 137
                or "timeout: sending signal TERM to command" in docker_output
            ):
                return (
                    False,
                    False,
                ), f"Maven timed out after {timeout} seconds see: {docker_output}"

            if not run_tests:
                error_lines = extract_error_lines(docker_output)

                print(
                    "has_failed output code is",
                    output_code,
                    "error line length was",
                    len(error_lines),
                )
                has_succeeded = int(output_code) == 0 and len(error_lines) < 1
                print("has_succeeded", has_succeeded, error_lines)

                if len(error_lines) > 0:
                    error_text = "\n".join(error_lines)
                    return (has_succeeded, has_succeeded), error_text.replace(
                        "/mnt/repo/", ""
                    )
                else:
                    if errors_only:
                        return (has_succeeded, has_succeeded), ""
                    return (has_succeeded, has_succeeded), docker_output.replace(
                        "/mnt/repo/", ""
                    )
            else:
                if collect_all_errors:
                    error_lines = extract_error_lines(docker_output)
                    has_errors = len(error_lines) > 0
                    if has_errors:
                        return (False, False), "\n".join(error_lines).replace(
                            "/mnt/repo/", ""
                        )
                    if errors_only:
                        return (True, True), ""

                # Better isolator for compile vs test failures
                lines = docker_output.split("\n")
                test_index = -1
                compilation_index = -1
                compilation_failed = False
                output_code_int = int(output_code)

                for i, line in enumerate(lines):
                    if "[INFO] Results:" in line:
                        test_index = i
                        break
                for i, line in enumerate(lines):
                    if "COMPILATION ERROR" in line:
                        compilation_failed = True
                        compilation_index = i
                        break

                if not compilation_failed:
                    compilation_error_markers = [
                        "Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin",
                        "Compilation failure",
                        "[ERROR] COMPILATION ERROR",
                    ]
                    for i, line in enumerate(lines):
                        if any(marker in line for marker in compilation_error_markers):
                            compilation_failed = True
                            compilation_index = i
                            break

                if compilation_failed:
                    test_output = "\n".join(lines[(compilation_index - 1) :])
                    return (False, False), test_output

                explicit_test_failure = (
                    "There are test failures." in docker_output
                    or "Failed to execute goal org.apache.maven.plugins:maven-surefire-plugin" in docker_output
                    or "Failed to execute goal org.apache.maven.plugins:maven-failsafe-plugin" in docker_output
                )

                if output_code_int != 0 and explicit_test_failure:
                    if test_index == -1:
                        lines_without_downloads = [
                            line
                            for line in lines
                            if "Downloading" not in line and "Downloaded" not in line
                        ]
                        return (True, False), "\n".join(lines_without_downloads)

                    test_output = "\n".join(lines[(test_index - 1) :])
                    return (True, False), test_output

                if output_code_int != 0:
                    lines_without_downloads = [
                        line
                        for line in lines
                        if "Downloading" not in line and "Downloaded" not in line
                    ]
                    return (False, False), "\n".join(lines_without_downloads)

                if test_index == -1:
                    lines_without_downloads = [
                        line
                        for line in lines
                        if "Downloading" not in line and "Downloaded" not in line
                    ]
                    return (True, True), "\n".join(
                        lines_without_downloads
                    )

                test_output = "\n".join(lines[(test_index - 1) :])
                return (True, True), test_output
        except Exception as e:
            return (False, False), f"An error occurred: {str(e)}"
