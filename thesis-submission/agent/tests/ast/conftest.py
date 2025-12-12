import os
import pytest
from tree_sitter import Language, Parser
import tree_sitter_java as tsjava
from masterthesis.ast.collect_imports import collect_imports


@pytest.fixture(scope="module")
def test_project_directory() -> str:
    return "tests/ast/fixtures"


@pytest.fixture(scope="module")
def test_files(test_project_directory: str) -> dict[str, str]:
    # find all files by glob
    with os.scandir(test_project_directory) as entries:
        return {
            entry.name: entry.path
            for entry in entries
            if entry.is_file() and entry.name.endswith(".java")
        }


@pytest.fixture(scope="module")
def parser() -> Parser:
    parser = Parser()
    parser.language = Language(tsjava.language())
    return parser


@pytest.fixture(scope="module")
def all_imports(parser: Parser, test_files: dict[str, str]) -> dict[str, list[str]]:
    return {file: collect_imports(test_files[file], parser) for file in test_files}
