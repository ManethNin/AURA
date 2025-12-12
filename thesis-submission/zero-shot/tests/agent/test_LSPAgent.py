import os
import pytest
from pathlib import Path
from masterthesis.agent.LSPAgent import LSPAgent
import tempfile
import subprocess


@pytest.fixture
def repo_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "my_project"
        yield project_path


@pytest.fixture
def lsp_agent(repo_dir):
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
    return LSPAgent(repo_dir)


def test_validate_changes(lsp_agent, repo_dir, snapshot):
    with lsp_agent.start_container() as container:
        original_file_path = (
            "src/main/java/com/wire/lithium/models/NewBotResponseModel.java"
        )
        diff_path = Path(__file__).parent / "diff.txt"
        diff_text = diff_path.read_text()
        print(os.path.exists(repo_dir))
        result1, result2 = lsp_agent.validate_changes(original_file_path, diff_text)
        assert isinstance(result1, dict)
        assert isinstance(result2, dict)

        assert result1 == snapshot
        assert result2 == snapshot


# def test_validate_file(lsp_agent):
#   original_file_path = "/path/to/original_file.txt"
#   result = lsp_agent.validate_file(original_file_path)
#   assert isinstance(result, dict)
#   # Add more assertions based on the expected behavior of validate_file()

# def test__validate_lsp(lsp_agent):
#   original_file_path = "/path/to/original_file.txt"
#   diff_text = "some diff text"
#   result1, result2 = lsp_agent._validate_lsp(original_file_path, diff_text)
#   assert isinstance(result1, dict)
#   assert isinstance(result2, dict)
#   # Add more assertions based on the expected behavior of _validate_lsp()
