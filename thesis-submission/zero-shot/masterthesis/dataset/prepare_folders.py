import json
import os
import re
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

import pandas as pd
import requests

from masterthesis.agent.aider.AdvancedDiffAgent import UnifiedDiffCoder
from masterthesis.agent.GitAgent import GitAgent
from masterthesis.agent.LSPAgent import extract_error_lines
from masterthesis.agent.SpoonAgent import SpoonAgent

df = pd.read_parquet("upgrades/research_data.parquet")


root_dir = Path(__file__).parent.parent.parent

input_data_dir = root_dir / "dataset"


revapi_path = root_dir / Path("bump/RQData/japicmp-revapi-analysis-results.json")

with revapi_path.open("r", encoding="utf-8") as f:
    revapi_dict = json.load(f)

# sample 5 keys
sampled_keys = [
    revapi_item
    for revapi_item in revapi_dict.keys()
    if revapi_dict[revapi_item]["japicmpResult"] != {}
    or revapi_dict[revapi_item]["revapiResult"] != {}
    or revapi_dict[revapi_item]["elementLines"] != {}
]

candidates = sampled_keys
# candidates = ["ea03f6488449fcfe8cd0a678b4c64891e1427a32"]

initial_candidates = len(candidates)

successful_entries = 0
valid_json_data = 0
with_suspicious_files = 0
version_compatible = 0
diff_available = 0
ast_transformed = 0

log_regex = r"(WARNING|ERROR)\] (.+\.java):\["


def get_files_with_errors(element_lines):
    files = []
    for line in element_lines:
        match = re.search(log_regex, line)
        if match:
            path = match.group(2)
            # split off the first folder of the path
            path = path.split("/")[2:]
            files.append("/".join(path))
    return files


input_params = defaultdict()


def cautious_checks(key: str) -> None:
    if key not in input_params:
        raise ValueError(f"Expected {key} to be present")
    value = input_params[key]
    if isinstance(value, str):
        assert len(value.strip()) > 0, f"Expected {key} to be non-empty"
    if isinstance(value, list):
        assert len(value) > 0, f"Expected {key} to be non-empty"
    if isinstance(value, dict):
        assert len(value) > 0, f"Expected {key} to be non-empty"


for commit_hash in candidates:

    commit_dir = input_data_dir / commit_hash
    os.makedirs(commit_dir, exist_ok=True)

    print(f"Processing {commit_hash}")
    test_candidate = df[df["breakingCommit"] == commit_hash]

    if len(test_candidate) == 0:
        shutil.rmtree(commit_dir)
        continue
    valid_json_data += 1

    project_name = test_candidate["project"].values[0]

    if len(test_candidate) == 0:
        print(f"No test candidate found for {commit_hash}")
        continue

    repository_name = test_candidate["project"].values[0]
    repo_slug = test_candidate["projectOrganisation"].values[0] + "/" + repository_name
    input_params["repo_slug"] = repo_slug

    revapi = revapi_dict.get(
        commit_hash, {"elementLines": {}, "allPotentialBreakingElements": {}}
    )
    suspicious_files = list(set(get_files_with_errors(revapi["elementLines"].values())))

    if len(suspicious_files) > 1 or len(suspicious_files) == 0:
        print(f"More than one suspicious file found for {commit_hash}")
        shutil.rmtree(commit_dir)
        continue

    input_params["suspicious_files"] = suspicious_files
    cautious_checks("suspicious_files")

    # assert len(suspicious_files) <2, f"Expected one file, got {len(suspicious_files)}"

    api_changes = json.dumps(revapi)

    input_params["api_changes"] = api_changes
    cautious_checks("api_changes")

    file_in_scope = suspicious_files[0]

    reproduction_log_path = (
        root_dir
        / Path("bump/reproductionLogs/successfulReproductionLogs")
        / (commit_hash + ".log")
    )
    if not reproduction_log_path.exists():
        raise ValueError(f"Reproduction log for {commit_hash} does not exist")

    with open(reproduction_log_path, "r", encoding="utf-8") as f:
        reproduction_log = f.read()
        reproduction_log = "\n".join(reproduction_log.split("\n")[1:])
        input_params["reproduction_log"] = reproduction_log
        cautious_checks("reproduction_log")
        project_path = "/" + project_name + "/"

        def process_line(line: str):
            if project_path not in line:
                return line

            parts = line.split()
            return " ".join(
                part[len(project_path) :] if part.startswith(project_path) else part
                for part in parts
            )

        initial_error_lines = "\n".join(
            [process_line(line) for line in extract_error_lines(reproduction_log)]
        )

        input_params["initial_error_lines"] = initial_error_lines
        cautious_checks("initial_error_lines")

    if "class file has wrong version" in reproduction_log:
        print(f"Skipping {commit_hash} because of class file version error")
        shutil.rmtree(commit_dir)
        continue
    version_compatible += 1

    response = requests.get(test_candidate["url"].values[0] + ".diff", timeout=10)

    assert response.status_code == 200, f"Could not download diff for {commit_hash}"
    updated_dependency_diff = response.text

    input_params["updated_dependency_diff"] = updated_dependency_diff
    cautious_checks("updated_dependency_diff")
    diff_available += 1

    non_git_diff = [
        edit_line
        for edit_line in updated_dependency_diff.split("\n")
        if not edit_line.startswith("diff --git") and not edit_line.startswith("index")
    ]
    non_git_diff = "\n".join(non_git_diff)
    edits = UnifiedDiffCoder("").get_edits(
        f"""```diff
{non_git_diff}
```"""
    )

    groupId_regex = re.compile(r"<groupId>(.*?)<\/groupId>")
    artifactId_regex = re.compile(r"<artifactId>(.*?)<\/artifactId>")

    edits = [edit[1] for edit in edits if "pom.xml" in edit[0]]

    version_upgrade_list = []

    for edit in edits:

        stringified = "\n".join(edit)

        group_id = groupId_regex.findall(stringified)[0]
        artifact_id = artifactId_regex.findall(stringified)[0]

        version_regex = re.compile(r"<version>(.*?)<\/version>")
        for edit_line in edit:
            if edit_line.startswith("-"):
                initial_version = version_regex.findall(edit_line)
            if edit_line.startswith("+"):
                final_version = version_regex.findall(edit_line)
        assert (
            len(initial_version) == 1
        ), f"Expected one initial version, got {initial_version}"
        assert (
            len(final_version) == 1
        ), f"Expected one final version, got {final_version}"
        version_upgrade_str = (
            f"{group_id}:{artifact_id} {initial_version[0]} -> {final_version[0]}"
        )
        version_upgrade_list.append(version_upgrade_str)

    input_params["version_upgrade_str"] = "\n".join(version_upgrade_list)

    cautious_checks("version_upgrade_str")

    def replace_java_error_pattern(log):
        error_pattern = re.compile(r"(.*?\.java):\[\d+,\d+\]")
        replaced_log = error_pattern.sub(r"\1", log)
        return replaced_log

    java_error_pattern = re.compile(
        r"(?:\[(?:ERROR|WARN|INFO)\]\s+)?([^:\[]+\.java):?\[?(\d+)(?:,(\d+))?\]?"
    )
    errors = defaultdict(tuple)
    for filename, line, col in java_error_pattern.findall(initial_error_lines):
        # [(10, 5), (20, 8)],
        if not errors[filename]:
            errors[filename] = []
        errors[filename].append((line, col))

    def remove_maven_clutter(replacement_string: str) -> str:
        replacement_string = replacement_string.replace("[ERROR]", "")
        replacement_string = replacement_string.replace("-> [Help 1]", "")
        replacement_string = replacement_string.replace(
            "org.apache.maven.plugins:maven-compiler-plugin", "maven-compiler-plugin"
        )
        replacement_string = [line.strip() for line in replacement_string.split("\n")]
        replacement_string = "\n".join(replacement_string)
        return replacement_string

    input_params["extracted_compilation_errors"] = errors
    cautious_checks("extracted_compilation_errors")
    minified_error_lines = replace_java_error_pattern(initial_error_lines)

    minified_error_lines = remove_maven_clutter(minified_error_lines)

    input_params["minified_error_lines"] = minified_error_lines
    cautious_checks("minified_error_lines")

    super_minified_error_lines = remove_maven_clutter(initial_error_lines)
    super_minified_error_lines = super_minified_error_lines.split("\n")
    for i, line in enumerate(super_minified_error_lines):
        if (
            line.startswith("Failed to execute goal maven-compiler-plugin")
            and "Compilation failure" in line
        ):
            super_minified_error_lines.remove(line)
        # if '.java' in line.split(' ')[0]:
        #     super_minified_error_lines[i] = ' '.join(line.split(' ')[:1])
        # if java_error_pattern.match(line):
        super_minified_error_lines[i] = re.sub(
            java_error_pattern, "", super_minified_error_lines[i]
        ).strip()

    super_minified_error_lines = "\n".join(super_minified_error_lines)

    input_params["super_minified_error_lines"] = super_minified_error_lines

    input_params["file_in_scope"] = file_in_scope

    cautious_checks("super_minified_error_lines")
    cautious_checks("file_in_scope")

    repo_dir = commit_dir / "repo"

    git_agent = GitAgent(repo_dir, commit_hash, repo_slug)
    git_agent.discard_changes()

    # if True:
    #     try:
    #         shutil.rmtree(commit_dir / "out")
    #     except FileNotFoundError:
    #         pass

    error_paths = [repo_dir / file_path for file_path in errors.keys()]
    path_problems = False
    for path in error_paths:
        if not path.exists():
            print(f"File {path} does not exist")
            print(f"Errors: {errors.keys()}")
            shutil.rmtree(commit_dir)
            path_problems = True
            break
    if path_problems:
        continue

    try:
        minimized_files = SpoonAgent.invoke_ast_transformation(
            repo_dir, errors, include_comments=True
        )

        minimized_files_without_comments = SpoonAgent.invoke_ast_transformation(
            repo_dir, errors, include_comments=False
        )

        assert minimized_files is not None
        assert minimized_files_without_comments is not None
    except Exception as e:
        print(f"Spoon screwed up {commit_dir}")
        print(e)
        shutil.rmtree(commit_dir)
        continue

    ast_transformed += 1

    minimized_directory = commit_dir / "minimized_files"
    os.makedirs(minimized_directory, exist_ok=True)
    assert len(minimized_files) == len(
        errors
    ), f"Expected {len(errors)} files, got {len(minimized_files)}"
    for filename, transformed_code in minimized_files.items():
        cleaned_file_path = filename.replace(repo_dir.as_posix() + "/", "")
        target_path = (
            minimized_directory / f"{cleaned_file_path}_minimized_with_comments.txt"
        )
        os.makedirs(target_path.parent, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(transformed_code)

    for filename, transformed_code in minimized_files_without_comments.items():
        cleaned_file_path = filename.replace(repo_dir.as_posix() + "/", "")
        target_path = (
            minimized_directory / f"{cleaned_file_path}_minimized_no_comments.txt"
        )
        os.makedirs(target_path.parent, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(transformed_code)

    for key, value in input_params.items():
        fileending = "txt"
        if isinstance(value, dict) or isinstance(value, list):
            value = json.dumps(value)
            fileending = "json"
        with open(commit_dir / f"{key}.{fileending}", "w", encoding="utf-8") as f:
            f.write(value)

    successful_entries += 1

    # SpoonAgent().invoke_ast_transformation()

print("\nDataset Preparation Summary:")
print(f"Initial candidates: {initial_candidates}")
print(f"Valid JSON data: {valid_json_data}")
print(f"Version compatible: {version_compatible}")
print(f"Diff available: {diff_available}")
print(f"With suspicious files: {valid_json_data - successful_entries}")
print(f"AST transformed: {ast_transformed}")
print(f"Successfully processed: {successful_entries}")

print(f"\nElimination rate: {(initial_candidates - successful_entries) / initial_candidates:.2%}")