import logging
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Tuple

from masterthesis.agent.aider.AdvancedDiffAgent import UnifiedDiffCoder
from masterthesis.agent.DockerAgent import DockerAgent
from masterthesis.agent.LSPAgent import extract_error_lines


class MavenReproducerAgent:
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

    def prepare_diffs(self, diffs: list[str]):
        coder = UnifiedDiffCoder(repo_dir=self.repo_dir)
        for diff_text in diffs:
            paths = coder.get_paths(diff_text)
            for path in paths:

                output_location = Path(self.input_dir) / os.path.basename(path)
                is_valid_diff, patched_file = coder.apply_edits(diff_text)
                assert is_valid_diff, f"Diff for {path} is not valid"

                with open(output_location, "w", encoding="utf-8") as out_file_wrapper:
                    out_file_wrapper.write(patched_file)

    def compile_maven(
        self, diffs: list[str], run_tests: bool, timeout: int = 1800
    ) -> Tuple[Tuple[bool, bool], str]:

        assert self.container is not None, "Container is not initialized"

        assert isinstance(diffs, list), "Diffs are not a list"

        try:
            self.prepare_diffs(diffs)
        except Exception as e:
            return (False, False), f"Failed to prepare diffs: {e}"

        commands = []
        coder = UnifiedDiffCoder(repo_dir=self.repo_dir)

        for diff in diffs:
            paths = coder.get_paths(diff)
            for path in paths:
                print("path", path)
                path_in_repo = Path("/mnt/repo") / path

                # backup_command = f"mv {path_in_repo} {path_in_repo}.bak"
                # commands.append(backup_command)

                copy_command = f"cp /mnt/input/{os.path.basename(path)} {path_in_repo}"
                commands.append(copy_command)

                check_for_existence_command = f"test -f {path_in_repo}"
                commands.append(check_for_existence_command)

        chained_commands = " && ".join(commands)
        logging.debug("Running commands: %s", chained_commands)
        print("Running commands: ", chained_commands)

        if len(chained_commands.strip()) == 0:
            return (
                (False, False),
                "No commands to run to apply the diff. Are you sure the paths are correct in the diff?",
            )
        bashified_command = f"/bin/bash -c '{chained_commands}'"
        logging.info("executing file manipulation %s", bashified_command)
        copy_output_code, copy_output_results = self.dockerAgent.execute_command(
            self.container, bashified_command, "/mnt/repo"
        )
        print(copy_output_results)
        if int(copy_output_code) != 0:
            return (
                (False, False),
                f"Failed to copy files, was trying to run {chained_commands}. Are you sure the paths are correct in the diff?",
            )

        try:
            reproduction_command = "mvn clean test -Dsurefire.printSummary=true -Dsurefire.redirectTestOutputToFile=false"

            if self.force_upgrade_compiler_version:
                reproduction_command += " -Dmaven.compiler.source=8 -Dmaven.compiler.target=8 -Dmaven.compiler.release=8 -Dmaven.compiler.testSource=8 -Dmaven.compiler.testTarget=8"

            reproduction_command += " -B"

            if not run_tests:
                reproduction_command = "mvn clean compile -DskipTests -B"

            timeout_command = f"timeout -k 10s {timeout}s {reproduction_command}"

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
                return self.compile_maven(diffs, run_tests, timeout)

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
                    return (has_succeeded, has_succeeded), docker_output.replace(
                        "/mnt/repo/", ""
                    )
            else:
                # Better isolator for test results
                lines = docker_output.split("\n")
                test_index = -1
                compilation_index = -1
                compilation_failed = False
                for i, line in enumerate(lines):
                    if "[INFO] Results:" in line:
                        test_index = i
                        break
                for i, line in enumerate(lines):
                    if "COMPILATION ERROR" in line:
                        compilation_failed = True
                        compilation_index = i
                        break

                if compilation_failed:
                    test_output = "\n".join(lines[(compilation_index - 1) :])
                    return (False, False), test_output

                if test_index == -1:
                    lines_without_downloads = [
                        line
                        for line in lines
                        if "Downloading" not in line and "Downloaded" not in line
                    ]
                    return (True, int(output_code) == 0), "\n".join(
                        lines_without_downloads
                    )

                test_output = "\n".join(lines[(test_index - 1) :])
                succeeded_both = int(output_code) == 0
                return (True, succeeded_both), test_output
        except Exception as e:
            return False, f"An error occurred: {str(e)}"
