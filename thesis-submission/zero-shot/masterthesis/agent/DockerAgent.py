import base64
import subprocess
import tarfile
import tempfile
import unicodedata
from pathlib import Path
from typing import Optional

import docker
import docker.models
import docker.models.containers
import docker.types


class DockerError(Exception):
    pass


class DockerAgent:
    """
    A class representing a Docker agent.

    Attributes:
    - image (str): The name of the Docker image.
    - project_path (str): The path to the project directory.

    Methods:
    - __init__(self, image, project_path): Initializes a DockerAgent object.
    - pull_image(self): Pulls the Docker image.
    - create_container_shell(self): Creates and starts a container with a shell.
    - get_archive_from_container(self, container): Retrieves the project archive from the container.
    - inject_patched_file(self, container, patched_file_local_path): Injects a patched file into the container.
    - inject_patched_file_via_stdin(self, container, patched_file_local_path): Injects a patched file into the container using stdin.
    - get_file_from_container_via_stdout(self, container, container_file_path): Retrieves a file from the container using stdout.
    - execute_main_command(self, container, command): Executes a main command in the container.
    - clean_up(self, container): Cleans up the container and temporary directory.
    - run_with_patch(self, patched_file_local_path, main_command): Runs the container with a patched file and main command.
    """

    def __init__(self, image, project_path):
        self.client = docker.from_env()
        self.image = image
        self.project_path = Path(project_path)
        self.tmpdir = tempfile.TemporaryDirectory(delete=False)
        self.tmpdirname = Path(self.tmpdir.name)

    def pull_image(self) -> docker.models.images.Image:
        print(f"Pulling image {self.image}...")
        return self.client.images.pull(self.image)

    def create_container_shell(self) -> docker.models.containers.Container:
        container = self.client.containers.create(
            self.image, command="/bin/sh", tty=True
        )
        container.start()
        return container

    def get_archive_from_container(
        self, container: docker.models.containers.Container
    ) -> Path:
        try:
            bits, _ = container.get_archive(str(self.project_path))
            tar_path = self.tmpdirname / "archive.tar"
            with tar_path.open("wb") as f:
                for chunk in bits:
                    f.write(chunk)
            with tarfile.open(tar_path) as tar:
                tar.extractall(path=self.tmpdirname)
            return tar_path
        except docker.errors.NotFound as e:
            return None

    def inject_patched_file(
        self,
        container: docker.models.containers.Container,
        patched_file_local_path: str,
    ) -> None:
        tar_path = self.tmpdirname / "patched_archive.tar"
        patched_file_local_path = Path(patched_file_local_path)
        with tarfile.open(tar_path, "w") as tar:
            tar.add(
                patched_file_local_path,
                arcname=self.project_path / patched_file_local_path.name,
            )
        with tar_path.open("rb") as f:
            container.put_archive(str(self.project_path), f.read())
        print(
            f"Injected patched file into the container at {self.project_path}/{patched_file_local_path.name}"
        )

    def inject_patched_file_via_stdin(
        self,
        container: docker.models.containers.Container,
        patched_file_local_path: str,
    ) -> bool:
        """
        Injects a patched file into the container using stdin.

        Args:
        - container: The Docker container.
        - patched_file_local_path (str): The path to the patched file on the local machine.
        """
        patched_file_local_path = Path(patched_file_local_path)

        # Read the file content
        with patched_file_local_path.open("r", encoding="utf-8") as f:
            file_content = f.read()

        # Encode the file content in base64
        file_content_base64 = base64.b64encode(file_content.encode("utf-8")).decode(
            "utf-8"
        )

        # Run mkdir command to create the directory if it doesn't exist
        mkdir_result = subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                container.id,
                "mkdir",
                "-p",
                str(self.project_path),
            ],
            check=True,
        )

        # Use base64 and tee to write the file content to the desired path inside the container
        create_file_result = subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                container.id,
                "sh",
                "-c",
                f"echo {file_content_base64} | base64 -d | tee {str(self.project_path / patched_file_local_path.name)} > /dev/null",
            ],
            check=True,
        )

        return create_file_result.returncode == 0 and mkdir_result.returncode == 0

    def get_file_from_container_via_stdout(
        self, container: docker.models.containers.Container, container_file_path: str
    ) -> str:
        """
        Retrieves a file from the container using stdout.

        Args:
        - container: The Docker container.
        - container_file_path (str): The path to the file inside the container.

        Returns:
        - str: The content of the file.
        """
        exists = container.exec_run(f"test -f {container_file_path}")
        if exists.exit_code != 0:
            raise Exception(
                f"File {container_file_path} does not exist in the container."
            )

        # Use base64 encoding to safely transfer the file content
        exec_log = container.exec_run(f"base64 {container_file_path}", stdout=True)

        # Decode the base64 output
        file_content_base64 = exec_log.output.decode("utf-8")
        file_content = base64.b64decode(file_content_base64).decode("utf-8")

        # Normalize the content to NFC
        normalized_content = unicodedata.normalize("NFC", file_content)

        return normalized_content

    def execute_main_command(
        self, container: docker.models.containers.Container, command: str
    ) -> str:
        """
        Executes a main command in the container.

        Args:
        - container: The Docker container.
        - command (str): The main command to execute.

        Returns:
        - str: The output of the command.
        """
        print("Executing command", command)
        exec_log = container.exec_run(cmd=command)
        # assert exec_log.exit_code == 0, f"Command failed: {exec_log.output}"
        if exec_log.exit_code == 124:
            raise DockerError(f"Command timed out: {exec_log.output.decode('utf-8')}")
        if exec_log.exit_code != 0:
            log = exec_log.output.decode("utf-8")
            print(log, flush=True)
            raise DockerError(f"Command failed: {log}")

        return exec_log.output.decode("utf-8")

    def execute_command(
        self, container: docker.models.containers.Container, command: str, workdir: str
    ) -> str:
        """
        Executes a command in the container.

        Args:
        - container: The Docker container.
        - command (str): The command to execute.

        Returns:
        - str: The output of the command.
        """
        exec_status = container.exec_run(cmd=command, workdir=workdir)
        return exec_status.exit_code, exec_status.output.decode("utf-8")

    def execute_command_demux(self, container, command):
        setup_result_exit_code, setup_result_out = container.exec_run(
            cmd=command, demux=True
        )

        # print(setup_result_exit_code, setup_result_out)
        setup_result_stdout, setup_result_stderr = setup_result_out
        if setup_result_stdout is not None:
            setup_result_stdout = setup_result_stdout.decode("utf-8")
        if setup_result_stderr is not None:
            setup_result_stderr = setup_result_stderr.decode("utf-8")
        return setup_result_exit_code, setup_result_stdout, setup_result_stderr

    def execute_command_with_mounts(
        self, mounts, setup_command
    ) -> tuple[docker.models.containers.Container, str, str]:
        """
        This method should spin up the container, mount the volumes, execute setup.py within the container,
        and then leave the container running and return the container ID.

        Args:
        - mounts (list[docker.types.Mount]): A list of mounts.

        Returns:
        - str: The container ID.
        """
        # Start the container with mounts
        self.pull_image()
        container = self.client.containers.create(
            image=self.image,
            # command="/bin/bash",  # Keeps the container running
            volumes=mounts,
            entrypoint="/bin/bash",  # Keeps the container running
            tty=True,
        )
        container.start()
        print("Started container")
        # container.exec_run("/bin/bash", tty=True)

        # Execute the setup.py inside the container
        setup_result_exit_code, setup_result_out = container.exec_run(
            cmd=setup_command, demux=True
        )

        # print(setup_result_exit_code, setup_result_out)
        setup_result_stdout, setup_result_stderr = setup_result_out
        if setup_result_stdout is not None:
            setup_result_stdout = setup_result_stdout.decode("utf-8")
        if setup_result_stderr is not None:
            setup_result_stderr = setup_result_stderr.decode("utf-8")

        # assert "maven" in setup_result_stdout, f"Setup failed: stdout:{setup_result_out} stderr:{setup_result_out}"

        assert (
            setup_result_exit_code == 0
        ), f"Setup failed: stdout:{setup_result_out} stderr:{setup_result_out}"

        # Return the container ID and leave the container running
        return container, setup_result_stdout, setup_result_stderr

    def run_with_mounts(
        self,
        command: str,
        mounts: list[docker.types.Mount],
    ) -> str:
        """
        Executes a command in the container with specified mounts.

        Args:
        - container: The Docker container.
        - command (str): The command to execute.
        - mounts (dict): A list of mounts

        Returns:
        - str: The output of the command.
        """
        return self.client.containers.run(
            image=self.image,
            command=command,
            volumes=mounts,
            stdout=True,
            stderr=True,
        )
        # return output
        # return exec_log.output.decode("utf-8")

    def clean_up(
        self, container: Optional[docker.models.containers.Container] = None
    ) -> None:
        """
        Cleans up the container and temporary directory.

        Args:
        - container: The Docker container.
        """
        if container is not None:
            container.kill()
            container.remove()
        self.tmpdir.cleanup()

    def run_with_patch(self, patched_file_local_path: str, main_command: str) -> str:
        """
        Runs the container with a patched file and main command.

        Args:
        - patched_file_local_path (str): The path to the patched file on the local machine.
        - main_command (str): The main command to execute in the container.

        Returns:
        - str: The output of the main command.
        """
        container_project_path = self.project_path
        try:
            self.pull_image()
            container = self.create_container_shell()
            self.get_archive_from_container(container)
            print(
                "Pulled the image, created the container, and got the archive from the container."
            )
            self.inject_patched_file_via_stdin(container, patched_file_local_path)
            print(
                f"Injected the patched file {patched_file_local_path} into the container."
            )
            print(
                f"Looking for {container_project_path}/{Path(patched_file_local_path).name} in the container..."
            )
            return self.execute_main_command(container, main_command)
        except docker.errors.NotFound as e:
            print(e)
            print(
                f"Could not find the project path {container_project_path} in the container."
            )
        finally:
            self.clean_up(container)
