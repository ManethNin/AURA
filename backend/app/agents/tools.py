import json
import os
from pathlib import Path
from typing import Dict, Optional, TypedDict, List
from langchain.agents import tool
from app.masterthesis.agent.GitAgent import GitAgent
from app.masterthesis.agent.LSPAgent import LSPAgent
from app.masterthesis.agent.MavenReproducerAgent import MavenReproducerAgent
from app.masterthesis.agent.TreeAgent import get_directory_tree
from app.masterthesis.agent.aider.AdvancedDiffAgent import UnifiedDiffCoder
from app.masterthesis.dataset.find_compilation_errors import find_compilation_errors
from langchain_core.messages import BaseMessage

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    wait_random_exponential,
)
from collections import defaultdict
from opentelemetry import trace as trace_api


class ToolHistory(TypedDict):
    input: str
    output: str
    error: str
    span_id: str


class ExecutionDetails(TypedDict):
    validate_diffs: List[ToolHistory]
    compile_maven: List[ToolHistory]
    read_file: List[ToolHistory]
    get_directory_tree: List[ToolHistory]
    get_language_server_suggestions: List[ToolHistory]


execution_details: Dict[str, ExecutionDetails] = defaultdict(
    lambda: {
        "validate_diffs": [],
        "compile_maven": [],
        "read_file": [],
        "get_directory_tree": [],
        "get_language_server_suggestions": [],
        "reset_repo": [],
    }
)

tracer = trace_api.get_tracer(__name__)


def process_error_text(error_text: str, project_path: str) -> str:
    processed_lines = [
        " ".join(
            part[len(project_path) :] if part.startswith(project_path) else part
            for part in line.split()
        ).strip()
        for line in error_text.split("\n")
        if "Downloaded from" not in line and "Downloading from" not in line
    ]
    return "\n".join(line for line in processed_lines if line).replace("\x00", "")


def process_diagnostics(lsp_result_initial, lsp_result_post_patching):
    def diagnostic_stringifier(diagnostic):
        message = (diagnostic.get("message", "")).replace("/mnt/repo/", "")
        start_line = diagnostic["range"]["start"].get("line", 0)
        start_character = diagnostic["range"]["start"].get("character", 0)
        end_line = diagnostic["range"]["end"].get("line", start_line)
        end_character = diagnostic["range"]["end"].get("character", start_character)
        return f"[JAVA] {start_line}:{start_character} to {end_line}:{end_character} - {message}"

    initial_diagnostics_set = set(
        diagnostic_stringifier(d) for d in lsp_result_initial["diagnostics"]
    )
    post_patching_diagnostics_set = set(
        diagnostic_stringifier(d) for d in lsp_result_post_patching["diagnostics"]
    )
    added_diagnostics_set = post_patching_diagnostics_set - initial_diagnostics_set

    return [
        diagnostic_stringifier(d)
        for d in lsp_result_post_patching["diagnostics"]
        if diagnostic_stringifier(d) in added_diagnostics_set
    ]


def get_tools_for_repo(repo_path: Path, repo_slug: str, commit_hash: str = "HEAD") -> list:
    """
    Get tools for a cloned GitHub repository.
    
    Args:
        repo_path: Path to the cloned repository on disk
        repo_slug: Repository identifier (e.g., "owner/repo")
        commit_hash: Git commit hash to work with (defaults to HEAD)
    
    Returns:
        List of LangChain tools for the agent
    """
    def discard():
        git_agent = GitAgent(
            repo_path,
            commit_hash,
            repo_slug,
        )
        git_agent.discard_changes()

    discard()

    def log_tool_execution(
        tool_name: str, input_data: str, output: str, error: str = "", span_id: str = ""
    ):
        details: ToolHistory = {
            "input": input_data,
            "output": output,
            "error": error,
            "span_id": span_id,
        }
        execution_details[commit_hash][tool_name].append(details)

    @tool
    def reset_repo() -> str:
        """Resets the project repository to the initial state. Undoes all file changes."""
        with tracer.start_as_current_span("reset_repo") as span:
            print("[TOOL] Resetting repository")
            discard()
            span.set_attribute("reset_repo_success", True)
            log_tool_execution(
                tool_name="reset_repo",
                input_data="",
                output="Successful reset of repository",
                error="",
                span_id=span.get_span_context().span_id,
            )
            return "Successful reset of repository"

    @tool
    def validate_diffs(diff: str) -> str:
        """Tests whether the Diff is applicable. Run this before compiling. Returns either a Diff Error or the applied file. Diff has to be wrapped in a Markdown codeblock and has to follow the file edit rules. The Diff verified here will not persist to disk."""
        with tracer.start_as_current_span("validate_diffs") as span:
            try:
                print("[TOOL] Validating diff")
                coder = UnifiedDiffCoder(repo_path)
                success, result = coder.apply_edits(diff)
                span.set_attributes(
                    {
                        "validate_diffs_success": success,
                        "validate_diffs_result": str(result),
                    }
                )
                output = str(result) if success else f"Diff Error: {result}"
                log_tool_execution(
                    tool_name="validate_diffs",
                    input_data=diff,
                    output=output,
                    error="" if success else str(result),
                    span_id=span.get_span_context().span_id,
                )
            except Exception as e:
                error_text = str(e).replace(str(repo_path) + "/", "")
                span.set_attributes(
                    {
                        "validate_diffs_success": False,
                        "validate_diffs_error": error_text,
                    }
                )
                output = f"Error: {error_text}"
                log_tool_execution(
                    tool_name="validate_diffs",
                    input_data=diff,
                    output=output,
                    error=error_text,
                    span_id=span.get_span_context().span_id,
                )
            return output

    class LineInfo(TypedDict):
        line_no: int
        content: str

    class MavenReturn(TypedDict):
        updated_files: dict[str, str]
        compilation_has_succeeded: bool
        test_has_succeeded: bool
        error_text: str
        compile_error_details: Dict[str, Dict[int, List[LineInfo]]]

    @tool
    def compile_maven_stateful(diff: str) -> MavenReturn:
        """Compiles the project with the given diffs applied. Returns metadata for the run as well as the content of the changed files. The Diff applied here will persist to the disk, unless the repository is reset after. When the Diff has errors, nothing will be applied."""
        return _compile_maven(diff)

    @tool
    def compile_maven_stateless(diff: str) -> MavenReturn:
        """Compiles the project with the given diffs applied. Returns metadata for the run as well as the content of the changed files. The Diff applied wont persist to disk, subsequent file reads will show the old file."""
        return _compile_maven(diff)

    @tool
    def compile_maven_file_edit(new_file_content: str, file_path: str) -> MavenReturn:
        """Compiles the project, after replacing the file at file_path with the new_file_content. Returns metadata for the run as well as the content of the changed files. The File written here will persist to the disk, unless the repository is reset after."""
        print("[TOOL] Compiling Maven with full file edit", file_path, new_file_content)

        return _compile_maven(new_file_content, file_path)

    def _compile_maven(diff: str, file_path: Optional[str] = None) -> MavenReturn:
        with tracer.start_as_current_span("compile_maven") as span:
            print("[TOOL] Compiling Maven")
            
            # SAFETY CHECK: Block modifications to build files
            forbidden_files = ["pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle"]
            
            # Check in diff content
            if diff and "```diff" in diff:
                diff_lower = diff.lower()
                for forbidden_file in forbidden_files:
                    if f"--- a/{forbidden_file}" in diff_lower or f"+++ b/{forbidden_file}" in diff_lower:
                        error_msg = f"BLOCKED: Attempt to modify {forbidden_file}. Build files cannot be changed. Only Java source code modifications are allowed."
                        print(f"[TOOL] {error_msg}")
                        return {
                            "compilation_has_succeeded": False,
                            "test_has_succeeded": False,
                            "error_text": error_msg,
                            "compile_error_details": {}
                        }
            
            # Check in file_path for direct file edits
            if file_path:
                file_path_lower = file_path.lower()
                for forbidden_file in forbidden_files:
                    if forbidden_file in file_path_lower:
                        error_msg = f"BLOCKED: Attempt to modify {forbidden_file}. Build files cannot be changed. Only Java source code modifications are allowed."
                        print(f"[TOOL] {error_msg}")
                        return {
                            "compilation_has_succeeded": False,
                            "test_has_succeeded": False,
                            "error_text": error_msg,
                            "compile_error_details": {}
                        }
            
            maven_agent = MavenReproducerAgent(repo_path)
            discard()
            with maven_agent.start_container() as container:

                (
                    (compilation_has_succeeded, test_has_succeeded),
                    error_text,
                    updated_file_dict,
                ) = maven_agent.compile_maven([diff], run_tests=True)

                error_text = process_error_text(error_text, str(repo_path))

                span.set_attributes(
                    {
                        "compile_maven_compilation_has_succeeded": compilation_has_succeeded,
                        "compile_maven_test_has_succeeded": test_has_succeeded,
                        "compile_maven_error_text": error_text,
                        "attempted_diff": diff,
                    }
                )

            print(
                f"[TOOL] Compilation has succeeded: {compilation_has_succeeded}, Test has succeeded: {test_has_succeeded}"
            )
            discard()

            if compilation_has_succeeded:
                output_errors = {}
            else:
                error_text = error_text.replace("/mnt/repo/", "")
                output_errors = defaultdict(dict)
                
                # Try to parse structured errors
                try:
                    errors = find_compilation_errors(error_text)
                    
                    for filename, error_triple in errors.items():
                        try:
                            lines = _read_file(filename.replace("/mnt/repo", "")).split("\n")
                            
                            # Use a dictionary to store error texts per line
                            error_texts_per_line = defaultdict(set)

                            for line, col, error_msg in error_triple:
                                error_texts_per_line[line].add(f"[{line},{col}] " + error_msg)

                            for line in error_texts_per_line.keys():
                                # line is already 1-indexed, so we subtract 1 for 0-based list indexing
                                line_index = int(line) - 1

                                # Calculate the range of lines to include (error line + 1 context line before and after)
                                start = max(0, line_index - 1)
                                end = min(len(lines), line_index + 2)

                                output_errors[filename][line] = {
                                    "lines": [
                                        {
                                            "line_no": i + 1,  # line numbers in output remain 1-indexed
                                            "content": lines[i],
                                        }
                                        for i in range(start, end)
                                    ],
                                    "error_texts": list(error_texts_per_line[line]),
                                }
                        except Exception as e:
                            print(f"[WARN] Could not read file {filename}: {e}")
                            # Store error without file content
                            output_errors[filename]["error"] = {
                                "error_texts": [str(error_triple)]
                            }
                            
                except Exception as e:
                    print(f"[WARN] Error parsing compilation errors: {e}")
                
                output_errors = dict(output_errors)
                print("[TOOL] Maven Output errors", output_errors)
                
                # If structured parsing failed, ensure raw error_text is available
                if not output_errors and error_text:
                    print("[TOOL] Structured error parsing failed, using raw error text")

            if not compilation_has_succeeded or not test_has_succeeded:
                output = MavenReturn(
                    compilation_has_succeeded=compilation_has_succeeded,
                    test_has_succeeded=test_has_succeeded,
                    error_text=error_text,
                    updated_files=updated_file_dict,
                    compile_error_details=output_errors,
                )
            else:
                output = MavenReturn(
                    compilation_has_succeeded=compilation_has_succeeded,
                    test_has_succeeded=test_has_succeeded,
                    error_text="",
                    updated_files=updated_file_dict,
                    compile_error_details={},
                )

            log_tool_execution(
                tool_name="compile_maven",
                input_data=diff,
                output=output,
                error=error_text,
                span_id=span.get_span_context().span_id,
            )
            return output

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_random_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
    )
    def _read_file(file_path):
        with open(repo_path / file_path, "r", encoding="utf-8") as file:
            return file.read()

    @tool
    def read_file_lines(file_path: str, lines: list[int]) -> Dict[int, str]:
        """Reads the file lines (1-indexed) at the given path and returns it, or an error message if the file could not be read. Limit yourself to a reasonable amount of lines, otherwise do a full file read."""
        with tracer.start_as_current_span("read_file_lines") as span:
            print(f"[TOOL] Reading file lines {file_path}, {lines}")

            try:
                file_text = _read_file(file_path)
                span.set_attributes(
                    {
                        "read_file_file_path": file_path,
                        "read_file_success": True,
                        "read_file_text": file_text,
                    }
                )
                log_tool_execution(
                    tool_name="read_file",
                    input_data=file_path,
                    output=file_text,
                    error="",
                    span_id=span.get_span_context().span_id,
                )

                all_lines = file_text.split("\n")

                # Create a dictionary of all lines, with 1-indexed line numbers
                all_line_dict = {
                    line_no: line for line_no, line in enumerate(all_lines, start=1)
                }
                print("[TOOL] File read. Processing lines")

                # Filter the dictionary to include only the specified lines
                # Note: 'lines' are already 1-indexed, so we use them directly
                return {
                    line_no: all_line_dict[line_no]
                    for line_no in lines
                    if line_no in all_line_dict
                }

            except Exception as e:
                error_text = str(e).replace(str(repo_path), "")
                span.set_attributes(
                    {
                        "read_file_file_path": file_path,
                        "read_file_success": False,
                        "read_file_error": error_text,
                    }
                )
                output = f"Error: {error_text}"
                log_tool_execution(
                    tool_name="read_file",
                    input_data=file_path,
                    output=output,
                    error=error_text,
                    span_id=span.get_span_context().span_id,
                )
                return {-1: output}

    @tool
    def read_file(file_path: str) -> str:
        """Reads the file at the given path and returns it, or an error message if the file could not be read."""
        with tracer.start_as_current_span("read_file") as span:
            print(f"[TOOL] Reading file {file_path}")

            try:
                file_text = _read_file(file_path)

                span.set_attributes(
                    {
                        "read_file_file_path": file_path,
                        "read_file_success": True,
                        "read_file_text": file_text,
                    }
                )
                log_tool_execution(
                    tool_name="read_file",
                    input_data=file_path,
                    output=file_text,
                    error="",
                    span_id=span.get_span_context().span_id,
                )
                print("[TOOL] File read.")
                return file_text
            except Exception as e:
                error_text = str(e).replace(str(repo_path), "")
                span.set_attributes(
                    {
                        "read_file_file_path": file_path,
                        "read_file_success": False,
                        "read_file_error": error_text,
                    }
                )
                output = f"Error: {error_text}"
                log_tool_execution(
                    tool_name="read_file",
                    input_data=file_path,
                    output=output,
                    error=error_text,
                    span_id=span.get_span_context().span_id,
                )
                return output

    @tool
    def get_directory_tree_for_path(relative_directory_path: str) -> str:
        """Returns the directory tree of the given path. Make sure that the Path is a directory."""
        with tracer.start_as_current_span("get_directory_tree") as span:
            print("[TOOL] Getting directory tree")
            try:
                absolute_path = repo_path / relative_directory_path
                tree = get_directory_tree(absolute_path)
                tree_json = json.dumps(tree, indent=4)
                span.set_attributes(
                    {
                        "get_directory_tree_relative_path": relative_directory_path,
                        "get_directory_tree_absolute_path": str(absolute_path),
                        "get_directory_tree_tree": tree_json,
                    }
                )
                log_tool_execution(
                    # tool_name=,input_data=,output=,error=,span_id=
                    tool_name="get_directory_tree",
                    input_data=relative_directory_path,
                    output=tree_json,
                    error="",
                    span_id=span.get_span_context().span_id,
                )
                return tree_json
            except Exception as e:
                error_text = str(e).replace(str(repo_path), "")
                span.set_attributes(
                    {
                        "get_directory_tree_relative_path": relative_directory_path,
                        "get_directory_tree_error": error_text,
                    }
                )
                output = f"Error: {error_text}"
                log_tool_execution(
                    tool_name="get_directory_tree",
                    input_data=relative_directory_path,
                    output=output,
                    error=error_text,
                    span_id=span.get_span_context().span_id,
                )
                return output

    @tool
    def get_language_server_suggestions(file_path: str, diff: str) -> List[str]:
        """Returns the Java language server suggestions for the given diff and file."""
        with tracer.start_as_current_span("get_language_server_suggestions") as span:
            print("[TOOL] Getting language server suggestions")
            try:
                lsp_agent = LSPAgent(repo_path)
                discard()
                lsp_result_initial, lsp_result_post_patching = (
                    lsp_agent.validate_changes(Path(file_path), [diff])
                )

                stringified_diagnostics = process_diagnostics(
                    lsp_result_initial, lsp_result_post_patching
                )

                span.set_attribute(
                    "get_language_server_suggestions_stringified_diagnostics",
                    stringified_diagnostics,
                )
                log_tool_execution(
                    tool_name="get_language_server_suggestions",
                    input_data=f"{file_path}|{diff}",
                    output=json.dumps(stringified_diagnostics),
                    error="",
                    span_id=span.get_span_context().span_id,
                )
                discard()
                return stringified_diagnostics
            except Exception as e:
                error_text = str(e).replace(str(repo_path), "")
                span.set_attribute("get_language_server_suggestions_error", error_text)
                output = f"Error: {error_text}"
                log_tool_execution(
                    tool_name="get_language_server_suggestions",
                    input_data=f"{file_path}|{diff}",
                    output=output,
                    error=error_text,
                    span_id=span.get_span_context().span_id,
                )
                return [output]

    # Return all tools for the agent
    tooling = [
        read_file,
        read_file_lines,
        get_directory_tree_for_path,
        validate_diffs,
        reset_repo,
        compile_maven_stateful,
        get_language_server_suggestions,
    ]

    return tooling