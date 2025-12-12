# %%
# language_model="claude-3-5-sonnet-20240620"
from enum import Enum
import os
import traceback

from masterthesis.dataset.find_compilation_errors import find_compilation_errors


# language_model = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"

# language_model = "mistral-large-2407"
# language_model = "open-mistral-nemo"
# language_model = "gpt-4o-mini"
# language_model = "claude-3-5-sonnet@20240620"
# language_model = "codellama-7b-instruct"  # Local CodeLlama model running on localhost:8080
# language_model = "qwen2.5-coder-7b-instruct"  # Alternative local model
# language_model = "claude-3-haiku@20240307"
# language_model = "gemini-2.0-flash-exp"  # Experimental - has stricter rate limits
language_model = "gemini-2.0-flash"  # Stable Gemini model with better free tier limits
# language_model = "gpt-4o"
# language_model = "meta/llama-3.1-70b-instruct"
# language_model = "mistralai/mistral-large-2-instruct"
# language_model = "ft:gpt-4o-mini-2024-07-18:personal:agent-5:9zY4dyXP"


class TrialType(Enum):
    BASELINE = ""
    BASELINE_AUGMENTED_PROMPT = "augmented_prompt"
    BASELINE_LSP = "lsp"
    STATELESS = "stateless"
    FULL_FILE_EDIT = "full_file_edit"
    FEW_SHOT_EXAMPLE = "few_shot_example"


from dotenv import load_dotenv

load_dotenv(".env")

trial_type = TrialType.BASELINE_AUGMENTED_PROMPT


import atexit
import signal
from masterthesis.dataset.load_dataset import cleanup_dataset

# Global variable to track candidates
candidates = None

def cleanup_handler():
    print("Cleaning up before exit...")
    if candidates is not None:
        cleanup_dataset(candidates)


# Register the cleanup function to be called on normal program termination
atexit.register(cleanup_handler)


# Define a signal handler for SIGTERM (termination signal)
def sigterm_handler(signum, frame):
    print("Received SIGTERM. Cleaning up...")
    cleanup_handler()
    exit(0)


# Register the SIGTERM handler
signal.signal(signal.SIGTERM, sigterm_handler)


from collections import defaultdict
from langchain_openai import ChatOpenAI
from langchain_together import ChatTogether
from langchain_mistralai import ChatMistralAI
from langchain_google_genai import ChatGoogleGenerativeAI

# llm = ChatTogether(together_api_key=os.getenv("TOGETHER_API_KEY"), model=language_model, temperature=0, max_retries=3)
# llm = ChatMistralAI(model=language_model, temperature=0, timeout=240)

# Google Gemini configuration
llm = ChatGoogleGenerativeAI(
    model=language_model,
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

# from langchain_google_vertexai import ChatVertexAI

# llm = ChatVertexAI(model=language_model, temperature=0)


# from langchain_core.outputs import LLMResult
# from langchain_google_vertexai.model_garden import ChatAnthropicVertex

# project = "calm-collective-431221-e9"
# location = "europe-west1"

# # # Initialise the Model
# llm = ChatAnthropicVertex(
#     model_name=language_model,
#     project=project,
#     location=location,
#     temperature=0
# )

# from langchain_openai import AzureChatOpenAI

#

# llm = ChatOpenAI(
#     model="codellama-7b-instruct",  # CodeLlama model name
#     temperature=0.1,  # Match your server's --temp 0.1
#     max_tokens=16384,  # Match your server's -c 16384 context size
#     timeout=None,
#     base_url="http://127.0.0.1:8080/v1",  # Your local llama.cpp server
#     api_key="not-needed"  # Local server doesn't require authentication
# )

# Local model configurations (commented out)
# llm = ChatOpenAI(
#     model="qwen2.5-coder-7b-instruct",
#     temperature=0.1,
#     max_tokens=16384,
#     timeout=None,
#     base_url="http://127.0.0.1:8080/v1",
#     api_key="not-needed"
# )

# llm = AzureChatOpenAI(
#     # AZURE
#     azure_deployment=language_model,
#     api_version="2024-06-01",
#     # END AZURE

#     # model=language_model,
#     temperature=0,
#     max_tokens=None,
#     timeout=None,
#     max_retries=3,
# )

# from langchain_nvidia_ai_endpoints import ChatNVIDIA


# llm = ChatNVIDIA(
#   model=language_model,
#   api_key=os.getenv("NVIDIA_API_KEY"),
#   temperature=0,
# )


# from langchain_anthropic import ChatAnthropic

# llm = ChatAnthropic(
#     model=language_model,
#     temperature=0,
#     max_tokens=1024,
#     timeout=None,
#     max_retries=2,
#     api_key=os.getenv("ANTHROPIC_API_KEY")
# )

language_model = language_model.replace("/", "_")

# %%
# from langchain.chains import LLMChain  # Deprecated and unused
# from langchain_core.prompts import PromptTemplate  # Unused
# from langchain_openai import OpenAI  # Unused
from openinference.instrumentation.langchain import LangChainInstrumentor
from opentelemetry import trace as trace_api
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.sdk.trace import ReadableSpan

from pathlib import Path
import os


class FileSpanExporter(SpanExporter):
    def __init__(self, file_name: str):
        self.file_name = file_name

    def export(self, spans: list[ReadableSpan]) -> SpanExportResult:
        with open(self.file_name, "a") as f:
            for span in spans:
                f.write(span.to_json().replace("\n", "") + "\n")
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


# endpoint = "http://127.0.0.1:6006/v1/traces"
tracer_provider = trace_sdk.TracerProvider()
trace_api.set_tracer_provider(tracer_provider)
# tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint)))
tracer_provider.add_span_processor(
    BatchSpanProcessor(
        FileSpanExporter(
            Path(os.path.abspath(""))
            / f"trace_langchain_{language_model}{"_"+trial_type.value if trial_type.value else ""}.json"
        )
    )
)

LangChainInstrumentor().instrument()


# %%
import json
import os
from pathlib import Path
from typing import Dict, Optional, TypedDict
from langchain_core.tools import tool
from masterthesis.agent.GitAgent import GitAgent
from masterthesis.agent.LSPAgent import LSPAgent
from masterthesis.agent.MavenReproducerAgent import MavenReproducerAgent
from masterthesis.agent.TreeAgent import get_directory_tree
from masterthesis.agent.aider.AdvancedDiffAgent import UnifiedDiffCoder
from masterthesis.dataset.dataset_types import DatasetEntry
from masterthesis.dataset.load_dataset import load_dataset
from langchain_core.messages import BaseMessage

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    wait_random_exponential,
)
from typing import TypedDict, List, Dict
from collections import defaultdict
from pathlib import Path
import json
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


# Update the global candidates variable
candidates = load_dataset(
    os.path.abspath("dataset"),
    load_agent_only_files=True,
    filter=[
        # "067f5d2c81ff87c90755f4ed48f62eb5faa8ecf9"
        "24d4a90ec1b375751e71f33d18949405c9529d77"
        # "6c53cd904bd66fc79af8687571e607c259226b81"  # Run only on this specific project
        #   "d401e189fb6435110e3dc4ca1a94838f167e7ddf"
        #   "41ec14e7e0ccf28476905eb28b2155b11d8a55f5",
        #   "923a6b2027e3ca1762deb6a60fc0a768c284122b",
        #   "cb541fd65c7b9bbc3424ea927f1dab223261d156",
        #   "54857351e0b0a655970d7e2ccdb67f175cc5d688",
        #   "24d4a90ec1b375751e71f33d18949405c9529d77",
        #   "2dfaa41bfb97674d11f09a5885011f19808548a3",
        #   "5769bdad76925da568294cb8a40e7d4469699ac3",
        #   "867e69e208ff59d1f8baae7ed41d3e163a51bc65"
    ],
)

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


def get_tools_for_dataset_entry(dataset_entry: DatasetEntry) -> list:
    def discard():
        git_agent = GitAgent(
            Path(dataset_entry.repo_path),
            dataset_entry.commit_hash,
            dataset_entry.repo_slug,
        )
        git_agent.discard_changes()

    discard()
    repo_path = Path(dataset_entry.repo_path)
    commit_hash = dataset_entry.commit_hash

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
            maven_agent = MavenReproducerAgent(repo_path)
            if trial_type == TrialType.STATELESS:
                discard()
            with maven_agent.start_container() as container:

                if trial_type == TrialType.FULL_FILE_EDIT:
                    (
                        (compilation_has_succeeded, test_has_succeeded),
                        error_text,
                        updated_file_dict,
                    ) = maven_agent.compile_maven_with_full_file_replace(
                        file_content=diff, file_path=file_path, run_tests=True
                    )
                else:
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
            if trial_type == TrialType.STATELESS:
                discard()

            if compilation_has_succeeded:
                output_errors = {}
            else:
                error_text = error_text.replace("/mnt/repo/", "")
                output_errors = defaultdict(dict)
                errors = find_compilation_errors(error_text)

                try:
                    output_errors = defaultdict(dict)
                    for filename, error_triple in errors.items():
                        lines = _read_file(filename.replace("/mnt/repo", "")).split(
                            "\n"
                        )

                        # Use a dictionary to store error texts per line
                        error_texts_per_line = defaultdict(set)

                        for line, col, error_text in error_triple:
                            error_texts_per_line[line].add(
                                f"[{line},{col}] " + error_text
                            )

                        for line in error_texts_per_line.keys():
                            # line is already 1-indexed, so we subtract 1 for 0-based list indexing
                            line_index = int(line) - 1

                            # Calculate the range of lines to include (error line + 1 context line before and after)
                            start = max(0, line_index - 1)
                            end = min(len(lines), line_index + 2)

                            output_errors[filename][line] = {
                                "lines": [
                                    {
                                        "line_no": i
                                        + 1,  # line numbers in output remain 1-indexed
                                        "content": lines[i],
                                    }
                                    for i in range(start, end)
                                ],
                                "error_texts": list(error_texts_per_line[line]),
                            }
                except Exception as e:
                    print("Compilation errors were", errors)
                    print("Error processing compilation errors", e)

                output_errors = dict(output_errors)
                print("[TOOL] Maven Output errors", output_errors)

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
                if trial_type == TrialType.STATELESS:
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
                if trial_type == TrialType.STATELESS:
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

    base_tooling = [
        read_file,
        read_file_lines,
        get_directory_tree_for_path,
    ]
    if trial_type == TrialType.FULL_FILE_EDIT:
        tooling = base_tooling + [reset_repo, compile_maven_file_edit]
    elif trial_type == TrialType.STATELESS:
        tooling = base_tooling + [validate_diffs, compile_maven_stateless]
    else:
        if trial_type == TrialType.BASELINE_LSP:
            base_tooling = base_tooling + [get_language_server_suggestions]
        # Baseline
        tooling = base_tooling + [validate_diffs, reset_repo, compile_maven_stateful]

    return tooling


# %%
def format_input(dataset_entry: DatasetEntry) -> str:
    initial_input = f"""
Updated Dependency Details: {dataset_entry.version_upgrade_str}

Initial Error: {dataset_entry.initial_error_lines}
"""

    if not trial_type == TrialType.BASELINE_AUGMENTED_PROMPT:
        return initial_input
    initial_input += f"""
Revapi/japicmp API Changes, which describe changes in the APIs used by this project: {dataset_entry.api_changes}
"""
    return initial_input


# %%
# from langchain.agents.format_scratchpad.openai_tools import (
#     format_to_openai_tool_messages,
# )
# from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain_anthropic.output_parsers import ToolsOutputParser
from typing import Annotated, Literal, TypedDict
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
# from langgraph.pregel import RetryPolicy  # Commented out - not available in current langgraph version


system_prompt = SystemMessage(
    """Act as an expert Java software developer.
The program has issues after a version upgrade of a dependency.
Try using minimal changes to the code to fix the issues. 
Do not explain your actions or ask questions, just provide diffs that always adhere to the rules.
When you think you are done, reply with the diff that fixes the issues, after that a final verification step will happen and the conversation will be ended if it was successful. If not you get the error back.

# File editing rules:
Return edits similar to unified diffs that `diff -U0` would produce.
The diff has to be in a markdown code block, like this: ```diff ```.

Make sure you include the first 2 lines with the file paths.
Don't include timestamps with the file paths.

Start each hunk of changes with a `@@ ... @@` line.
Don't include line numbers like `diff -U0` does.
The user's patch tool doesn't need them.

The user's patch tool needs CORRECT patches that apply cleanly against the current contents of the file!
Think carefully and make sure you include and mark all lines that need to be removed or changed as `-` lines.
Make sure you mark all new or modified lines with `+`.
Don't leave out any lines or the diff patch won't apply correctly.
Dont add in new comments or change existing comments.
Make sure the diff is minimal and only includes the changes needed to fix the issue plus at least one context line so the tool can apply the diff correctly.

Indentation matters in the diffs!

Start a new hunk for each section of the file that needs changes.
Dont include unnescessary context, but include at least one line of it.
If no context is included, the tool will try to apply the changes at the end of the line.

Only output hunks that specify changes with `+` or `-` lines.
Skip any hunks that are entirely unchanging ` ` lines.

Output hunks in whatever order makes the most sense.
Hunks don't need to be in any particular order.

When editing a function, method, loop, etc use a hunk to replace the *entire* code block.
Delete the entire existing version with `-` lines and then add a new, updated version with `+` lines.
This will help you generate correct code and correct diffs.

To make a new file, show a diff from `--- /dev/null` to `+++ path/to/new/file.ext`.
"""
    # if trial_type != TrialType.FULL_FILE_EDIT else "Always give back the full file wrapped in a code block. Always signify the full filepath with a `Path:` line one line before the codeblock. Include nothing else.",
)

# %%
# parser=ToolsOutputParser()
# chain = llm_with_tools | parser
# ai_msg = chain.invoke(prompt.invoke({"input": format_input(dataset_entry)}))

# Use the Runnable
# from langgraph.checkpoint.sqlite import SqliteSaver  # Not available in current version
from langchain_core.messages.tool import (
    ToolCall,
)
import random
import string

# print(f"{language_model}{"_"+trial_type.value if trial_type.value else ""}.db")

# For newer langgraph versions, SqliteSaver.from_conn_string() returns a context manager
# We'll initialize it properly when needed
# checkpointer = SqliteSaver.from_conn_string(
#     f"{language_model}{"_"+trial_type.value if trial_type.value else ""}.db"
# )
# Use MemorySaver instead which is simpler and doesn't require context manager
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()

from langchain_core.agents import AgentActionMessageLog
from langchain_core.load import dumps


def should_continue(state: MessagesState) -> Literal["tools", "compile_agent"]:
    messages = state["messages"]
    last_message = messages[-1]
    # If the LLM makes a tool call, then we route to the "tools" node

    with open(os.path.join(out_path, "chat_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join([m.pretty_repr() for m in messages]))

    with open(os.path.join(out_path, "chat_log.jsonl"), "w", encoding="utf-8") as f:
        f.write("\n".join([dumps(m) for m in messages]))

    if last_message.tool_calls:
        print("[AGENT] Routing to tools")
        return "tools"
    print("[AGENT] Routing to compile agent")
    return "compile_agent"


def should_improve_non_test_diff(state: MessagesState) -> Literal["agent", END]:
    messages = state["messages"]
    last_message = messages[-1]
    with open(os.path.join(out_path, "chat_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join([m.pretty_repr() for m in messages]))

    with open(os.path.join(out_path, "chat_log.jsonl"), "w", encoding="utf-8") as f:
        f.write("\n".join([dumps(m) for m in messages]))

    if "Compilation and Testing successful:" in last_message.content:
        print("[AGENT] Compilation and Testing successful")
        return END
    try:
        parsed = json.loads(last_message.content)
        if parsed["compilation_has_succeeded"] and parsed["test_has_succeeded"]:
            print("[AGENT] Compilation and Testing successful")
            return END
        if (
            parsed["compilation_has_succeeded"]
            and "Could not initialize class org.mockito.internal.creation.cglib.ClassImposterizer"
            in parsed["error_text"]
        ):
            print("[AGENT] Compilation successful, hitting mockito issue")
            return END
    except:
        pass

    print("[AGENT] Back to Agent")
    return "agent"


for commit_hash, dataset_entry in candidates.items():
    state_language_model = language_model + (
        "_" + trial_type.value if trial_type.value else ""
    )
    out_path = os.path.join(
        os.path.abspath(""), f"dataset/{commit_hash}/out", state_language_model
    )
    if os.path.exists(os.path.join(out_path, "solution.json")):
        print("Skipping", commit_hash, "current setting already has a solution.")
        continue

    print("-" * 25)
    print(commit_hash)
    print("-" * 25)
    tools = get_tools_for_dataset_entry(dataset_entry)

    def compile_agent(state: MessagesState):
        print("[AGENT] Compiling")
        messages = state["messages"]
        last_message = messages[-1]
        tool_name = "compile_maven_stateful"
        if trial_type == TrialType.STATELESS:
            tool_name = "compile_maven_stateless"
        if trial_type == TrialType.FULL_FILE_EDIT:
            tool_name = "compile_maven_file_edit"
        if trial_type == TrialType.FULL_FILE_EDIT:
            lines = last_message.content.split("\n")
            # find the line with Path: in it and extract the path
            file_path = lines[lines.index("Path:") + 1].replace("Path:", "").strip()

            # find the lines where the codeblock starts and ends and slice lines so it only contains the content within the codeblock
            codeblock_start = lines.index("```") + 1
            codeblock_end = lines.index("```", codeblock_start)
            code_content = "\n".join(lines[codeblock_start:codeblock_end])

            print("path", file_path)
            # print("code_content", code_content)

            tool_call = ToolCall(
                name=tool_name,
                args={"new_file_content": code_content, "file_path": file_path},
                id="".join(random.choices(string.ascii_uppercase + string.digits, k=9)),
            )
        else:
            tool_call = ToolCall(
                name=tool_name,
                args={"diff": last_message.content},
                id="".join(random.choices(string.ascii_uppercase + string.digits, k=9)),
            )
        last_message.tool_calls = [tool_call]
        tools_by_name = {tool.name: tool for tool in tools}
        tool = tools_by_name[tool_name]
        try:
            tool_result = tool.invoke(tool_call["args"])
            messages.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        except Exception as e:
            tool_content = f"Error during compilation: {str(e)}"
            messages.append(
                ToolMessage(
                    content="",
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                    additional_kwargs={"error": e},
                )
            )
        return {"messages": messages}

    llm_with_tools = llm.bind_tools(tools)

    def call_model(state: MessagesState):
        messages = state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    workflow = StateGraph(MessagesState)

    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("compile_agent", compile_agent)
    workflow.set_entry_point("agent")

    # We now add a conditional edge
    workflow.add_conditional_edges(
        "agent",
        should_continue,
    )

    workflow.add_conditional_edges(
        "compile_agent",
        should_improve_non_test_diff,
    )

    workflow.add_conditional_edges("tools", should_improve_non_test_diff)

    app = workflow.compile(checkpointer=checkpointer)
    # app = workflow.compile()
    with tracer.start_as_current_span("Process Commit") as span:
        span.set_attribute("commit_hash", commit_hash)
        span.set_attribute("trial_type", trial_type.value)

        os.makedirs(out_path, exist_ok=True)
        first_shot_state = None
        try:
            # remove os.path.join(out_path, "error.txt") if it exists
            if os.path.exists(os.path.join(out_path, "error.txt")):
                os.remove(os.path.join(out_path, "error.txt"))

            all_initial_messages = [
                system_prompt,
                HumanMessage(content=format_input(dataset_entry)),
            ]

            with open(
                os.path.join(out_path, "initial_prompt.txt"), "w", encoding="utf-8"
            ) as f:
                f.write("\n\n".join([m.pretty_repr() for m in all_initial_messages]))

            langchain_config = {
                "run_name": dataset_entry.commit_hash,
                "recursion_limit": 15,  # Reduced to prevent context overflow
                "configurable": {"thread_id": dataset_entry.commit_hash},
            }
            first_shot_state = app.invoke(
                {"messages": all_initial_messages},
                config=langchain_config,
                # debug=True
            )
            # diff = first_shot_state["messages"][-1].content
            if first_shot_state:

                first_shot_state["messages"][-1].pretty_print()

                with open(os.path.join(out_path, "solution.json"), "w") as f:
                    f.write(first_shot_state["messages"][-1].content)

        except Exception as e:
            print("-" * 50)
            print("Main Exception handler")
            with open(os.path.join(out_path, "error.txt"), "w") as f:
                f.write(str(traceback.format_exc()))
            traceback.print_exc()
            continue
        finally:
            try:
                with open(
                    os.path.join(out_path, "final_state.diff"), "w", encoding="utf-8"
                ) as f:
                    git_agent = GitAgent(
                        Path(dataset_entry.repo_path),
                        dataset_entry.commit_hash,
                        dataset_entry.repo_slug,
                    )
                    f.write(git_agent.get_full_diff())
                with open(
                    os.path.join(out_path, "agent_protocol.json"), "w", encoding="utf-8"
                ) as f:
                    json.dump(execution_details[commit_hash], f, indent=4)
                if first_shot_state:
                    with open(
                        os.path.join(out_path, "first_shot_state"),
                        "w",
                        encoding="utf-8",
                    ) as f:
                        f.write(str(first_shot_state))
            except Exception as e:
                print(e)


cleanup_dataset(candidates)
