# Alternative approach: Use mvn dependency:list command with some tricks


import re
import subprocess
import tempfile


def get_maven_dependencies_via_cli(
    exclude_transitive_dependencies=True,
) -> list[dict[str, str]]:
    """
    Retrieves the direct dependencies of a Maven project using the Maven CLI command 'mvn dependency:list'.

    Args:
      exclude_transitive_dependencies (bool, optional): Flag to exclude transitive dependencies.
        Defaults to True.

    Returns:
      list[dict[str, str]]: A list of dictionaries representing the parsed dependencies. Each dictionary
        contains the following keys: 'group_id', 'artifact_id', 'dependency_type', 'version', 'scope',
        and 'module'.
    """
    try:
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file_name = temp_file.name
            # Call the Maven command and capture the output
            exclude_transitive_dependencies = (
                "true" if exclude_transitive_dependencies else "false"
            )
            result = subprocess.run(
                # excluding transitive dependencies here
                [
                    "mvn",
                    "dependency:list",
                    "-DoutputType=json",
                    f"-DexcludeTransitive={exclude_transitive_dependencies}",
                    f"-DoutputFile={temp_file_name}",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )

            # Check if the build was successful
            if "BUILD SUCCESS" not in result.stdout:
                print("Maven build failed.")
                return

            with open(temp_file_name, "r", encoding="utf-8") as file:
                content = file.read()
            ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
            clean_content = ansi_escape.sub("", content)

            # Extract and print dependencies
            dependencies = clean_content.strip().split("\n")
            # for dependency in dependencies:
            #     if dependency.strip().startswith('The following files have been resolved:'):
            #         continue
            #     print(dependency.strip())

            dependency_pattern = re.compile(
                r"(?P<group_id>[^:]+):(?P<artifact_id>[^:]+):(?P<type>[^:]+):(?P<version>[^:]+):(?P<scope>[^\s]+).*module (?P<module>[^\s]+)"
            )

            parsed_dependencies_from_list = []

            # Extract and print dependencies
            dependencies = clean_content.strip().split("\n")
            for dependency in dependencies:
                match = dependency_pattern.match(dependency.strip())
                if match:
                    group_id = match.group("group_id")
                    artifact_id = match.group("artifact_id")
                    dep_type = match.group("type")
                    version = match.group("version")
                    scope = match.group("scope")
                    module = match.group("module")
                    parsed_dependencies_from_list.append(
                        {
                            "group_id": group_id,
                            "artifact_id": artifact_id,
                            "dependency_type": dep_type,
                            "version": version,
                            "scope": scope,
                            "module": module,
                        }
                    )
            return parsed_dependencies_from_list

    except Exception as e:
        print(f"Error: {e}")
