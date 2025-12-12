import os
import subprocess
import tempfile
import pytest
from pathlib import Path
from docker.errors import NotFound
from masterthesis.agent.DockerAgent import DockerAgent


@pytest.fixture(scope="module")
def docker_agent():
    # Create a DockerAgent instance with a test image and test project path
    agent = DockerAgent(
        image="python:3.11.9-alpine3.20", project_path="/tmp/test_project"
    )
    yield agent
    # Clean up the temporary directory after tests
    agent.tmpdir.cleanup()


@pytest.fixture
def setup_docker_environment(docker_agent):
    # Pull the base image and create a container
    docker_agent.pull_image()
    container = docker_agent.create_container_shell()
    yield container
    # Ensure container is cleaned up after tests
    try:
        container.kill()
        container.remove()
    except NotFound:
        pass


# def test_pull_image(docker_agent):
#     # Test pulling the image
#     docker_agent.pull_image()
#     image = docker_agent.client.images.get("alpine")
#     assert image is not None


# def test_create_container_shell(docker_agent, setup_docker_environment):
#     # Test creating a container shell
#     container = setup_docker_environment
#     assert container.status == "running" or container.status == "created"


# def test_get_archive_from_container(docker_agent, setup_docker_environment):
#     # Test getting an archive from the container
#     container = setup_docker_environment
#     container.exec_run(
#         "mkdir -p /tmp/test_project && touch /tmp/test_project/test_file"
#     )
#     tar_path = docker_agent.get_archive_from_container(container)
#     assert tar_path.exists()


# # def test_inject_patched_file(docker_agent, setup_docker_environment):
# #     # Test injecting a patched file into the container
# #     container = setup_docker_environment
# #     patched_file = docker_agent.tmpdirname / "patched_file.py"
# #     patched_file.write_text("print('Hello, World!')")
# #     docker_agent.inject_patched_file(container, patched_file)
# #     result = container.exec_run("cat /tmp/test_project/patched_file.py")
# #     assert "print('Hello, World!')" in result.output.decode()


# def test_inject_patched_file_via_stdin(docker_agent, setup_docker_environment):
#     # Test injecting a patched file into the container via stdin
#     container = setup_docker_environment
#     patched_file = docker_agent.tmpdirname / "patched_file_via_stdin.py"
#     patched_file.write_text("print('Hello from stdin!')")
#     docker_agent.inject_patched_file_via_stdin(container, patched_file)
#     result = container.exec_run("cat /tmp/test_project/patched_file_via_stdin.py")
#     assert "print('Hello from stdin!')" in result.output.decode()


def test_get_file_from_container_via_stdout(docker_agent, setup_docker_environment):
    # Test getting a file from the container via stdout
    container = setup_docker_environment

    expected_text = "Nice Delta test \n \n hi hi \n ho"

    patched_file = docker_agent.tmpdirname / "file.txt"
    patched_file.write_text(expected_text)
    docker_agent.inject_patched_file_via_stdin(container, patched_file)

    content = docker_agent.get_file_from_container_via_stdout(
        container, "/tmp/test_project/file.txt"
    )
    assert content == expected_text


# def test_execute_main_command(docker_agent, setup_docker_environment):
#     # Test executing the main command in the container
#     container = setup_docker_environment
#     docker_agent.execute_main_command(container, "echo 'Hello, Docker!'")
#     result = container.exec_run("echo 'Hello, Docker!'")
#     assert "Hello, Docker!" in result.output.decode()


# def test_clean_up(docker_agent, setup_docker_environment):
#     # Test cleaning up the container
#     container = setup_docker_environment
#     docker_agent.clean_up(container)
#     with pytest.raises(NotFound):
#         docker_agent.client.containers.get(container.id)


# def test_run_with_patch(docker_agent):
#     # Test the entire run_with_patch workflow
#     # recursive create docker_agent.tmpdir
#     os.makedirs(docker_agent.tmpdir.name, exist_ok=True)
#     patched_file = Path(docker_agent.tmpdir.name) / Path(
#         "patched_file_run_with_patch.py"
#     )
#     patched_file.write_text("print('Hello from run_with_patch!')")
#     command_output = docker_agent.run_with_patch(
#         patched_file_local_path=patched_file,
#         main_command="python /tmp/test_project/patched_file_run_with_patch.py",
#     )
#     assert command_output.strip() == "Hello from run_with_patch!"


def test_mount_running(docker_agent):
    with (
        tempfile.TemporaryDirectory() as repo_dir,
        tempfile.TemporaryDirectory() as temp_dir2,
        tempfile.TemporaryDirectory() as temp_dir3,
    ):
        agent = DockerAgent(
            image="ghcr.io/lukvonstrom/multilspy-java-docker:latest",
            project_path="/tmp/test_project",
        )
        commit_hash = "10d7545c5771b03dd9f6122bd5973a759eb2cd03"
        _ = subprocess.run(
            ["git", "clone", "https://github.com/wireapp/lithium.git", repo_dir],
            capture_output=True,
        )
        _ = subprocess.run(
            ["git", "fetch", "--depth", "2", "origin", commit_hash],
            cwd=repo_dir,
            capture_output=True,
        )
        _ = subprocess.run(
            ["git", "checkout", commit_hash], cwd=repo_dir, capture_output=True
        )
        container, stdout, stderr = agent.execute_command_with_mounts(
            mounts={
                repo_dir: {"bind": "/mnt/repo", "mode": "rw"},
                temp_dir2: {"bind": "/mnt/data", "mode": "rw"},
                temp_dir3: {"bind": "/mnt/input", "mode": "rw"},
            },
            setup_command="/bin/bash -c 'source .env/bin/activate && python setup.py'",
        )

        out = agent.execute_main_command(container, "echo 'Hello, Docker!'")
        print(out)

        container.stop()
