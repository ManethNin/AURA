import json
import os
import re
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

import pandas as pd
import requests

from app.common_agents.agent.aider.AdvancedDiffAgent import UnifiedDiffCoder
from app.common_agents.agent.GitAgent import GitAgent
from app.common_agents.agent.LSPAgent import extract_error_lines
from app.common_agents.agent.SpoonAgent import SpoonAgent
from app.common_agents.dataset.find_compilation_errors import (
    find_compilation_errors,
    java_error_pattern,
)


root_dir = Path(__file__).parent.parent.parent

input_data_dir = root_dir / "dataset"

revapi_path = root_dir / Path("bump/RQData/japicmp-revapi-analysis-results.json")

with revapi_path.open("r", encoding="utf-8") as f:
    revapi_dict = json.load(f)


reproduction_log_path = root_dir / Path(
    "bump/reproductionLogs/successfulReproductionLogs"
)

candidates = []
for root, dirs, files in os.walk(reproduction_log_path):
    for file in files:
        if file.endswith(".log"):
            with open(os.path.join(root, file), "r") as f:
                text = f.read()
                if (
                    "Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin"
                    in text
                ):
                    candidates.append(os.path.basename(file).replace(".log", ""))


# Counter for initial candidates
initial_candidates = len(candidates)

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


successful_entries = 0
valid_json_data = 0
with_suspicious_files = 0
version_compatible = 0
diff_available = 0
path_verified = 0
ast_transformed = 0


for index, commit_hash in enumerate(candidates):

    commit_dir = input_data_dir / commit_hash
    os.makedirs(commit_dir, exist_ok=True)

    print(f"Processing {commit_hash}")

    candidate_path = Path("bump/data/benchmark") / (commit_hash + ".json")

    with open(candidate_path, "r", encoding="utf-8") as f:
        test_candidate = json.load(f)

    if test_candidate is None:
        shutil.rmtree(commit_dir)
        continue

    valid_json_data += 1

    project_name = test_candidate["project"]

    repository_name = test_candidate["project"]
    repo_slug = test_candidate["projectOrganisation"] + "/" + repository_name
    input_params["repo_slug"] = repo_slug

    revapi = revapi_dict.get(
        commit_hash, {"elementLines": {}, "allPotentialBreakingElements": {}}
    )
    suspicious_files = list(set(get_files_with_errors(revapi["elementLines"].values())))
    # if len(suspicious_files) == 0:
    #     print(f"No revapi log found for {commit_hash}")
    #     continue

    # assert len(suspicious_files) <2, f"Expected one file, got {len(suspicious_files)}"

    api_changes = json.dumps(revapi)

    input_params["api_changes"] = api_changes
    cautious_checks("api_changes")

    reproduction_log_path = (
        root_dir
        / Path("bump/reproductionLogs/successfulReproductionLogs")
        / (commit_hash + ".log")
    )
    if not reproduction_log_path.exists():
        raise ValueError(f"Reproduction log for {commit_hash} does not exist")

    with open(reproduction_log_path, "r", encoding="utf-8") as f:
        reproduction_log = f.read()
        reproduction_log = reproduction_log.split("\n")[1:]

        project_path = "/" + project_name + "/"

        def process_line(line: str):
            if "Downloaded from" in line or "Downloading from" in line:
                return ""

            if project_path not in line:
                return line.strip()

            parts = line.split()
            return " ".join(
                part[len(project_path) :] if part.startswith(project_path) else part
                for part in parts
            ).strip()

        processed_lines = [process_line(line) for line in reproduction_log]

        reproduction_log = "\n".join(
            [line.strip() for line in processed_lines if len(line.strip()) > 0]
        )
        reproduction_log = reproduction_log.replace("\x00", "")
        input_params["reproduction_log"] = reproduction_log
        cautious_checks("reproduction_log")

        lines = [process_line(line) for line in extract_error_lines(reproduction_log)]
        initial_error_lines = "\n".join(
            [line for line in lines if len(line.strip()) > 0]
        )

        input_params["initial_error_lines"] = initial_error_lines
        cautious_checks("initial_error_lines")

    if "class file has wrong version" in reproduction_log:
        print(f"Skipping {commit_hash} because of class file version error")
        shutil.rmtree(commit_dir)
        continue

    version_compatible += 1

    response = requests.get(test_candidate["url"] + ".diff", timeout=10)

    if response.status_code != 200:
        print(f"Could not download diff for {commit_hash}")
        shutil.rmtree(commit_dir)
        continue

    diff_available += 1

    def transform_diff_to_custom(diff: str) -> str:
        # diff --git a/pom.xml b/pom.xml
        # index d201481..56d051d 100644
        # --- a/pom.xml
        # +++ b/pom.xml
        # @@ -90,7 +90,7 @@
        #          <dependency>
        #              <groupId>org.yaml</groupId>
        #              <artifactId>snakeyaml</artifactId>
        # -            <version>1.24</version>
        # +            <version>2.0</version>
        #          </dependency>
        #          <dependency>
        #              <groupId>commons-io</groupId>
        fixed_lines = ""
        diff_lines = diff.split("\n")
        for diff_line in diff_lines:
            if diff_line.startswith("diff --git"):
                continue
            if diff_line.startswith("index"):
                continue
            if diff_line.startswith("@@") and diff_line.count("@@") == 2:
                # replace everything between @@ and @@ with ...
                diff_line = "@@ ... @@"
            fixed_lines += diff_line + "\n"
        return fixed_lines

    raw_response_text = response.text
    updated_dependency_diff = transform_diff_to_custom(raw_response_text)

    input_params["updated_dependency_diff"] = updated_dependency_diff
    cautious_checks("updated_dependency_diff")

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

        if len(initial_version) == 0 or len(final_version) == 0:
            continue
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

    if len(version_upgrade_list) == 0:
        version_upgrade_list = [updated_dependency_diff]

    input_params["version_upgrade_str"] = "\n".join(version_upgrade_list)

    cautious_checks("version_upgrade_str")

    def replace_java_error_pattern(log):
        error_pattern = re.compile(r"(.*?\.java):\[\d+,\d+\]")
        replaced_log = error_pattern.sub(r"\1", log)
        return replaced_log

    errors = find_compilation_errors(initial_error_lines)

    if len(suspicious_files) == 0:
        suspicious_files = list(errors.keys())
    input_params["suspicious_files"] = suspicious_files

    # if len(suspicious_files) > 1:
    #     print(f"More than one suspicious file found for {commit_hash}, removing")
    #     shutil.rmtree(commit_dir)
    #     continue
    if len(suspicious_files) > 1:
        input_params["agent_only"] = True
    elif len(suspicious_files) == 0:
        print(f"No suspicious file found for {commit_hash}, removing")
        shutil.rmtree(commit_dir)
        continue

    with_suspicious_files += 1

    cautious_checks("suspicious_files")
    file_in_scope = suspicious_files[0]
    input_params["file_in_scope"] = file_in_scope
    cautious_checks("file_in_scope")

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

    cautious_checks("super_minified_error_lines")

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
            path_problems = True
            break
    if path_problems:
        input_params["agent_only"] = True
    else:
        path_verified += 1

    try:
        minimized_files = SpoonAgent.invoke_ast_transformation(
            repo_dir, errors, include_comments=True
        )

        minimized_files_without_comments = SpoonAgent.invoke_ast_transformation(
            repo_dir, errors, include_comments=False
        )

        assert minimized_files is not None
        assert minimized_files_without_comments is not None
        ast_transformed += 1
    except Exception as e:
        print(f"Spoon screwed up {commit_dir}, removing")
        print(e)
        shutil.rmtree(commit_dir)
        continue

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
        if isinstance(value, bool) or isinstance(value, int):
            value = str(value)
        with open(commit_dir / f"{key}.{fileending}", "w", encoding="utf-8") as f:
            f.write(value)

    print(f"Completed {commit_hash} ({index + 1}/{len(candidates)})")
    successful_entries += 1

print("\nDataset Preparation Summary:")
print(f"Initial candidates: {initial_candidates}")
print(f"Valid JSON data: {valid_json_data}")
print(f"Version compatible: {version_compatible}")
print(f"Diff available: {diff_available}")
print(f"With suspicious files: {with_suspicious_files}")
print(f"Path verified: {path_verified}")
print(f"AST transformed: {ast_transformed}")
print(f"Successfully processed: {successful_entries}")

print(
    f"\nElimination rate: {(initial_candidates - successful_entries) / initial_candidates:.2%}"
)

# SpoonAgent().invoke_ast_transformation()
