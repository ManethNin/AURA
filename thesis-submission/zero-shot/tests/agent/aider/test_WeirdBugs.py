import difflib
import pytest
from pathlib import Path
import tempfile
import os

from masterthesis.agent.aider.AdvancedDiffAgent import UnifiedDiffCoder


@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname


@pytest.fixture
def temp_file(temp_repo):
    file_path = Path(temp_repo) / "test_file.py"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("line1\nline2\nline3\n")
    return str(file_path)


def get_proper_file_by_hash(commit_hash):
    with open(
        Path(__file__).parent / ("unittest/" + commit_hash + ".java"),
        "r",
        encoding="utf-8",
    ) as java_file_raw:
        java_file = java_file_raw.read()
    with open(
        Path(__file__).parent / ("unittest/" + commit_hash + ".diff"),
        "r",
        encoding="utf-8",
    ) as diff_file_raw:
        diff_file = diff_file_raw.read()
        if not commit_hash in diff_file:
            split_diff_file = diff_file.split("\n")
            found_idx = next(
                (i for i, line in enumerate(split_diff_file) if "Path:" in line), None
            )
            assert found_idx is not None
            print(found_idx, split_diff_file[found_idx])
            diff_file = split_diff_file[found_idx] = "Path: " + commit_hash + ".java"
            print(found_idx, split_diff_file[found_idx])

            diff_file = "\n".join(split_diff_file)

    return java_file, diff_file


# def test_abs_root_path(temp_repo):
#     coder = UnifiedDiffCoder(repo_dir=temp_repo)
#     relative_path = "test_file.py"
#     expected_path = str(Path(temp_repo).resolve() / relative_path)
#     assert coder.abs_root_path(relative_path) == expected_path

# def test_get_edits():
#     with open(Path(__file__).parent /"patch.txt", "r", encoding="utf-8") as file:
#         diff_content = file.read()

#     coder = UnifiedDiffCoder(repo_dir="")
#     edits = coder.get_edits(diff_content)
#     assert len(edits) == 1
#     assert edits[0][0] == "src/main/java/de/gwdg/metadataqa/marc/dao/MarcRecord.java"
#     assert edits[0][1] == [
#         "-} catch (JsonProcessingException e) {\n",
#         "+} catch (JacksonException e) {\n",
#     ]


def generic_test(snapshot, commit_hash):
    print("Investigating", commit_hash)
    java_file, diff_file = get_proper_file_by_hash(commit_hash)
    coder = UnifiedDiffCoder(repo_dir=Path(__file__).parent / "unittest")
    edits = coder.get_edits(diff_file)
    assert len(edits) > 0
    # assert edits == snapshot

    succeeded, changed_diff = coder.apply_edits(diff_file)

    if not succeeded:
        print(changed_diff)

    assert succeeded == True

    # assert changed_diff == snapshot

    # d = difflib.Differ()
    assert (
        "\n".join(
            list(
                difflib.unified_diff(
                    java_file.splitlines(),
                    changed_diff.splitlines(),
                    # fromfile=fromfile,
                    # tofile=tofile,
                    lineterm="",
                )
            )
        )
        == snapshot
    )


def test_1ef97ea6c5b6e34151fe6167001b69e003449f95(snapshot):
    generic_test(snapshot, "1ef97ea6c5b6e34151fe6167001b69e003449f95")

def test_a1ff30e0bc6a9b48e024a8ab27cefda3ad85b530(snapshot):
    generic_test(snapshot, "a1ff30e0bc6a9b48e024a8ab27cefda3ad85b530")

def test_14fc5fa696f499cac48401b3a86882b3bf7d9b82(snapshot):
    generic_test(snapshot, "14fc5fa696f499cac48401b3a86882b3bf7d9b82")

def test_874ed893a4e46ea5182be2be054715967e58f08f(snapshot):
    generic_test(snapshot, "874ed893a4e46ea5182be2be054715967e58f08f")


# def test_ee0827d4c9bf80982241e8c3559dceb8b39063e4(snapshot):
#     generic_test(snapshot, "ee0827d4c9bf80982241e8c3559dceb8b39063e4")
