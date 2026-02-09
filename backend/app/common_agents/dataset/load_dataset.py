import hashlib
import json
from collections import defaultdict
from pathlib import Path
import shutil
import tempfile
from typing import Any, Dict, Optional

from app.common_agents.dataset.dataset_types import DatasetEntry

# {
#     "suspicious_files": [
#         "extensions/struts2/test/com/google/inject/struts2/Struts2FactoryTest.java"
#     ],
#     "extracted_compilation_errors": {
#         "extensions/struts2/test/com/google/inject/struts2/Struts2FactoryTest.java": [
#             [
#                 "19",
#                 "46"
#             ],
#             [
#                 "55",
#                 "19"
#             ],
#             [
#                 "57",
#                 "35"
#             ]
#         ]
#     },
#     "initial_error_lines": "[ERROR] Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:2.3.2:testCompile (default-testCompile) on project guice-struts2: Compilation failure: Compilation failure:\n[ERROR] extensions/struts2/test/com/google/inject/struts2/Struts2FactoryTest.java:[19,46] error: package org.apache.struts2.dispatcher.ng.filter does not exist\n[ERROR] extensions/struts2/test/com/google/inject/struts2/Struts2FactoryTest.java:[55,19] error: cannot find symbol\n[ERROR]  class StrutsPrepareAndExecuteFilter\n[ERROR] extensions/struts2/test/com/google/inject/struts2/Struts2FactoryTest.java:[57,35] error: cannot find symbol\n[ERROR] -> [Help 1]",
#     "super_minified_error_lines": "error: package org.apache.struts2.dispatcher.ng.filter does not exist\nerror: cannot find symbol\nclass StrutsPrepareAndExecuteFilter\nerror: cannot find symbol\n",
#     "api_changes": "[\"bind(java.lang.Class)\", \"filter(java.lang.String)\", \"in(java.lang.Class)\", \"through(java.lang.Class)\"]",
#     "minified_error_lines": "Failed to execute goal maven-compiler-plugin:2.3.2:testCompile (default-testCompile) on project guice-struts2: Compilation failure: Compilation failure:\nextensions/struts2/test/com/google/inject/struts2/Struts2FactoryTest.java error: package org.apache.struts2.dispatcher.ng.filter does not exist\nextensions/struts2/test/com/google/inject/struts2/Struts2FactoryTest.java error: cannot find symbol\nclass StrutsPrepareAndExecuteFilter\nextensions/struts2/test/com/google/inject/struts2/Struts2FactoryTest.java error: cannot find symbol\n",
#     "reproduction_log": ""
#     "minimized_with_comments": {
#         "extensions/struts2/test/com/google/inject/struts2/Struts2FactoryTest.java": "",
#     },
#     "minimized_no_comments": {
#         "extensions/struts2/test/com/google/inject/struts2/Struts2FactoryTest.java": "",
#     },
#     "updated_dependency_diff": "diff --git a/extensions/struts2/pom.xml b/extensions/struts2/pom.xml\nindex b5a897474f..93e097d6b6 100644\n--- a/extensions/struts2/pom.xml\n+++ b/extensions/struts2/pom.xml\n@@ -28,7 +28,7 @@\n     <dependency>\n       <groupId>org.apache.struts</groupId>\n       <artifactId>struts2-core</artifactId>\n-      <version>2.3.37</version>\n+      <version>2.5.22</version>\n       <scope>provided</scope>\n     </dependency>\n   </dependencies>\n",
#     "file_in_scope": "extensions/struts2/test/com/google/inject/struts2/Struts2FactoryTest.java",
#     "repo_path": "/Users/anonymous/Projects/common_agents/dataset/acc50dabec6796c091b84c1ada2ae4cbcab8b562/repo",
#     "version_upgrade_str": "org.apache.struts:struts2-core 2.3.37 -> 2.5.22",
#     "repo_slug": "google/guice",
#     "commit_hash": "12asc"
# }


def cleanup_dataset(dataset: Dict[str, DatasetEntry]) -> None:
    for _, values in dataset.items():
        if values.repo_path is not None:
            shutil.rmtree(values.repo_path, ignore_errors=True)


def load_dataset(
    dataset_path: Optional[str | Path],
    load_agent_only_files: Optional[bool] = False,
    filter: Optional[str] = None,
    filter_out: Optional[str] = None,
) -> Dict[str, DatasetEntry]:

    if dataset_path:
        dataset_path = Path(dataset_path)
    else:
        root_dir = Path(__file__).parent.parent.parent

        dataset_path = root_dir / "dataset"

    dataset: Dict[str, Dict[str, Any]] = {}
    hashed_dataset: Dict[str, Dict[str, Any]] = defaultdict(dict)

    def hashed_add(
        commit: str, key: str, value: Any, subdict: Optional[str] = None
    ) -> None:
        """Add a value to the dataset and hashed_dataset with a hashed key."""
        hash_value = hashlib.sha256(str(value).encode()).hexdigest()
        if subdict:
            if subdict not in hashed_dataset[commit] and subdict not in dataset[commit]:
                hashed_dataset[commit][subdict] = {}
                dataset[commit][subdict] = {}
            hashed_dataset[commit][subdict][key] = hash_value
            dataset[commit][subdict][key] = value
        else:
            hashed_dataset[commit][key] = hash_value
            dataset[commit][key] = value

    for directory in dataset_path.iterdir():
        if directory.is_dir():
            if filter and directory.name not in filter:
                continue

            if filter_out and directory.name in filter_out:
                continue

            dataset[directory.name] = {}
            hashed_add(directory.name, "commit_hash", directory.name)

            for file_or_dir in directory.iterdir():
                if file_or_dir.is_file() and ".DS_Store" not in file_or_dir.name:
                    if (
                        file_or_dir.name == "agent_only.txt"
                        and not load_agent_only_files
                    ):
                        dataset[directory.name] = {}
                        # delete the key directory.name
                        del hashed_dataset[directory.name]
                        continue
                    file = file_or_dir
                    file_text = file.read_text()
                    file_text = file_text.replace("\x00", "")
                    if file.name.endswith(".txt"):
                        hashed_add(
                            directory.name, file.name.replace(".txt", ""), file_text
                        )
                    elif file.name.endswith(".json"):
                        hashed_add(
                            directory.name,
                            file.name.replace(".json", ""),
                            json.loads(file_text),
                        )

                if file_or_dir.is_dir() and file_or_dir.name == "minimized_files":
                    minimized_files_path = file_or_dir.as_posix()
                    subfiles = [f for f in file_or_dir.rglob("*") if f.is_file()]
                    for subfile in subfiles:
                        if subfile.name.endswith(".txt"):
                            key = (
                                "minimized_with_comments"
                                if "minimized_with_comments" in subfile.name
                                else "minimized_no_comments"
                            )
                            minimized_key = (
                                subfile.as_posix()
                                .replace(minimized_files_path + "/", "")
                                .replace("_" + key + ".txt", "")
                            )

                            hashed_add(
                                directory.name,
                                minimized_key,
                                subfile.read_text(),
                                subdict=key,
                            )
                elif file_or_dir.is_dir() and file_or_dir.name == "repo":
                    data_path = directory.as_posix()
                    hashed_add(directory.name, "data_path", data_path)
                    dest_path = tempfile.mkdtemp()
                    shutil.copytree(
                        file_or_dir.as_posix(),
                        dest_path,
                        symlinks=True,
                        ignore=None,
                        dirs_exist_ok=True,
                    )
                    repo_path = dest_path
                    hashed_add(directory.name, "repo_path", repo_path)
                elif file_or_dir.is_dir() and file_or_dir.name == "out":
                    continue

    assert len(dataset) > 0, "No entries found in dataset"

    # Create a dictionary to store the hashed values

    # if not os.path.exists("hashed_dataset.json"):
    #     with open("hashed_dataset.json", "w", encoding="utf-8") as file:
    #         file.write(json.dumps(hashed_dataset, indent=4))

    # with open("hashed_dataset.json", "r", encoding="utf-8") as file:
    #     file_text = file.read()
    #     file_json = json.loads(file_text)
    #     for commit, values in hashed_dataset.items():
    #         for key, value in values.items():
    #             assert (
    #                 file_json[commit][key] == value
    #             ), f"Dataset hash mismatch! commit: {commit}, key: {key}, value: {value}"
    #         assert (
    #             file_json[commit] == values
    #         ), f"Dataset hash mismatch! commit: {commit}, values: {values}"

    transformed_dataset = {}
    for commit, values in dataset.items():
        #
        if (
            values.get("commit_hash") is None
            or values.get("commit_hash") == "nan"
            or values.get("commit_hash") == ""
            or not values.get("commit_hash")
            or values.get("commit_hash") == "None"
            or values.get("repo_slug") == "None"
            or not values.get("repo_slug")
            or not values.get("repo_path")
            or not values.get("version_upgrade_str")
        ):
            continue

        dataset_entry = DatasetEntry(
            suspicious_files=values.get("suspicious_files", []),
            extracted_compilation_errors=values.get("extracted_compilation_errors", {}),
            initial_error_lines=values.get("initial_error_lines", ""),
            super_minified_error_lines=values.get("super_minified_error_lines"),
            api_changes=values.get("api_changes", ""),
            minified_error_lines=values.get("minified_error_lines"),
            reproduction_log=values.get("reproduction_log"),
            minimized_with_comments=values.get("minimized_with_comments", {}),
            minimized_no_comments=values.get("minimized_no_comments", {}),
            updated_dependency_diff=values.get("updated_dependency_diff"),
            file_in_scope=values.get("file_in_scope", ""),
            repo_path=values.get("repo_path"),
            version_upgrade_str=values.get("version_upgrade_str"),
            repo_slug=values.get("repo_slug"),
            commit_hash=values.get("commit_hash"),
        )
        transformed_dataset[commit] = dataset_entry
    return transformed_dataset
