import json
import logging
import os
import shutil
import signal
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from masterthesis.agent.aider.AdvancedDiffAgent import UnifiedDiffCoder
from masterthesis.agent.DockerAgent import DockerAgent


def extract_error_lines(docker_output: str) -> list[str]:
    error_lines = []
    RECORDING_ERRORS = False

    for line in docker_output.split("\n"):

        # if "T E S T S" in line:
        #     RECORDING_ERRORS = True
        if "BUILD FAILURE" in line:
            RECORDING_ERRORS = True

        if line.startswith("[ERROR]") and RECORDING_ERRORS:
            RECORDING_ERRORS = True
        if (
            "To see the full stack trace of the errors, re-run Maven with the -e switch."
            in line
        ):
            RECORDING_ERRORS = False
            break

        if (
            "Failed to execute goal org.apache.maven.plugins:maven-surefire-plugin"
            in line
        ):
            error_lines.append(line.strip())
            RECORDING_ERRORS = False
            break

        if line.strip() == "[ERROR]":
            # line is empty
            continue

        if RECORDING_ERRORS and "[ERROR]" in line:
            error_lines.append(line.strip())

    if "[INFO] BUILD SUCCESS" in docker_output:
        print("BUILD SUCCESS")
        return []
    return error_lines


class LSPAgent:
    def __init__(self, project_path: Path) -> None:
        """
        Initializes the LSPAgent with the provided project path.

        :param project_path: Path to the project directory.
        """
        self.dockerAgent = DockerAgent(
            "ghcr.io/lukvonstrom/multilspy-java-docker:latest", project_path
        )

        # self.dockerAgent = DockerAgent(
        #     "multilspy-java-docker:latest", project_path
        # )
        self.project_path = project_path

        self.container = None

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
                    setup_command="/bin/bash -c 'source .env/bin/activate && python setup.py'",
                )
            )
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

    def validate_changes(
        self, original_file_path: Path, diff_texts: list[str]
    ) -> tuple[dict[Any, Any], dict[Any, Any]]:
        """
        Validates changes in the specified file based on the provided diff text.

        :param original_file_path: Path to the original file.
        :param diff_text: Text representing the differences.
        :return: Tuple of dictionaries with initial and edit LSP results.
        """
        return self._validate_lsp(original_file_path, diff_texts)

    def validate_file(self, original_file_path: Path) -> Dict:
        """
        Validates the specified file without any changes.

        :param original_file_path: Path to the original file.
        :return: Dictionary with initial LSP results.
        """
        return self._validate_lsp(original_file_path)

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

    def _validate_lsp(
        self, original_file_path: Path, diffs: Optional[list[str]] = None
    ) -> Tuple[Dict, Optional[Dict]]:
        """
        Internal method to validate a file, optionally with changes.

        :param original_file_path: Path to the original file.
        :param diff_text: Optional text representing the differences.
        :return: Tuple of dictionaries with initial and optionally edit LSP results.
        """
        # `docker run -v "$(pwd)/lithium:/mnt/repo" -v "$(pwd)/mnt/data:/mnt/data" -v "$(pwd)/edit:/mnt/input" multilspy-java-docker -e yes -f src/main/java/com/wire/lithium/models/NewBotResponseModel.java`

        assert self.container is not None, "Container is not initialized"
        change_mode = len(diffs) > 0
        logging.debug(
            "Validating file %s in %s mode",
            original_file_path,
            "change" if change_mode else "normal",
        )

        try:

            if change_mode:
                # code_file = self.project_path / original_file_path
                self.prepare_diffs(diffs)

            parameter_text = "-e yes -f " if change_mode else "-f "

            docker_output = self.dockerAgent.execute_main_command(
                self.container,
                f"/bin/bash -c '/app/init.sh {parameter_text}{original_file_path.as_posix()}'",
            )
            # logging.info("docker_output %s", docker_output)

            if "Language Server timeout" in docker_output:
                self.dockerAgent.clean_up()
                raise Exception("Language Server timeout")

            with open(
                Path(self.results_dir) / "initial.json", "r", encoding="utf-8"
            ) as initial_file:
                initial_lsp_results = json.loads(initial_file.read())

            if change_mode:
                with open(
                    Path(self.results_dir) / "edit.json", "r", encoding="utf-8"
                ) as edit_file:
                    edit_lsp_results = json.loads(edit_file.read())
                    self.dockerAgent.clean_up()
                    return initial_lsp_results, edit_lsp_results
        finally:
            self.dockerAgent.clean_up()
        return initial_lsp_results
