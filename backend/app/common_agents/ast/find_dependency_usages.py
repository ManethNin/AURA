from typing import List

from tree_sitter import Parser

from app.common_agents.ast.collect_imports import collect_imports
from app.common_agents.ast.extract_usages import extract_usages
from app.common_agents.ast.read_java_files import read_java_files


def find_dependency_usages(
    project_directory: str, dependency_classes: List[str], parser: Parser
) -> List[str]:
    """
    Find usages of dependency classes in Java files within a project directory.

    Args:
        project_directory (str): The path to the project directory.
        dependency_classes (List[str]): A list of dependency classes to search for.
        parser (Parser): An instance of the Parser class used for parsing Java files.

    Returns:
        List[str]: A list of all usages of the dependency classes found in the Java files.
    """
    java_files = read_java_files(project_directory)
    all_usages = []

    for java_file in java_files:
        imports = collect_imports(java_file, parser)
        imported_classes = set()

        for imp in imports:
            if imp.endswith(".*"):
                # Wildcard import, add all dependency classes for now
                imported_classes.update(dependency_classes)
            else:
                imported_classes.add(imp.split(".")[-1])

        usages = extract_usages(java_file, dependency_classes, imported_classes, parser)
        all_usages.extend(usages)

    return all_usages
