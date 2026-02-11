import hashlib
import json
from pathlib import Path
from typing import Any, Callable, List

import tiktoken
from opentelemetry import trace as trace_api

from app.common_agents.agent.aider.AdvancedDiffAgent import UnifiedDiffCoder
from app.common_agents.agent.GitAgent import GitAgent
from app.common_agents.agent.LSPAgent import LSPAgent
from app.common_agents.agent.MavenReproducerAgent import MavenReproducerAgent
from app.common_agents.dataset.dataset_types import DatasetEntry
from app.common_agents.dataset.feature_flags import (
    APIChangeType,
    CodeType,
    DependencyChangeType,
    ErrorType,
    FeatureFlags,
    OmissionsType,
)
from app.common_agents.llm.generate_signatures import FILE_EDITING_RULES
from app.common_agents.llm.types import DiffCallbackParams, DiffInfo, TokenizerType


def pipeline(
    invalid_diff_callback: Callable[[bool, Exception | str], None],
    diagnostic_callback: Callable[[List[str], str | None], None],
    compile_callback: Callable[[bool, str], None],
    test_callback: Callable[[bool, str], None],
    generate_diffs_callback: Callable[[DiffCallbackParams], list[str]],
    feature_flags: FeatureFlags,
    dataset_entry: DatasetEntry,
    tokenizer_type: TokenizerType,
) -> tuple[list[str], DiffInfo]:
    tracer = trace_api.get_tracer(__name__)

    tokenizer_name, token_threshold = tokenizer_type.value

    if tokenizer_type in (TokenizerType.GPT4O, TokenizerType.GPT3):
        tokenizer = tiktoken.get_encoding(tokenizer_name)
    # elif tokenizer_type in (TokenizerType.LLAMA3, TokenizerType.LLAMA3_1):
    # from transformers import AutoTokenizer
    # os.environ["TOKENIZERS_PARALLELISM"] = "false"
    # tokenizer = AutoTokenizer.from_pretrained(tokenizer_name, trust_remote_code=True)
    # os.environ["TOKENIZERS_PARALLELISM"] = "true"
    elif tokenizer_type == TokenizerType.MIXTRAL:
        from mistral_common.tokens.tokenizers.mistral import MistralTokenizer

        tokenizer = MistralTokenizer.v3()

    def multi_tokenizer_assert(llm_input: Any) -> None:
        if not isinstance(llm_input, str):
            llm_input = json.dumps(llm_input)

        if tokenizer_type in (TokenizerType.GPT4O, TokenizerType.GPT3):
            length = len(tokenizer.encode(llm_input))
        elif tokenizer_type in (TokenizerType.LLAMA3, TokenizerType.LLAMA3_1):
            # TODO: Fix this

            # os.environ["TOKENIZERS_PARALLELISM"] = "false"
            # length = len(tokenizer.tokenize(llm_input))
            # os.environ["TOKENIZERS_PARALLELISM"] = "true"
            return
        elif tokenizer_type == TokenizerType.MIXTRAL:
            from mistral_common.protocol.instruct.messages import AssistantMessage
            from mistral_common.protocol.instruct.request import ChatCompletionRequest

            tokenized = tokenizer.encode_chat_completion(
                ChatCompletionRequest(messages=[AssistantMessage(content=llm_input)])
            )
            length = len(tokenized.tokens)
        else:
            length = 0
        #     raise ValueError(f"Unsupported tokenizer type: {tokenizer_type}")

        assert (
            length <= token_threshold
        ), f"Total tokens for {tokenizer_type.name} exceed the threshold of {token_threshold}, was {length}"

    with tracer.start_as_current_span("pipeline") as main_span:

        git_agent = GitAgent(
            Path(dataset_entry.repo_path),
            dataset_entry.commit_hash,
            dataset_entry.repo_slug,
        )
        git_agent.discard_changes()

        for feature_flag in feature_flags.keys():
            main_span.set_attribute(
                f"feature_flag_{feature_flag}", feature_flags[feature_flag]
            )

        main_span.set_attribute("repo_dir", dataset_entry.repo_path)
        main_span.set_attribute("repo_slug", dataset_entry.repo_slug)

        file_to_be_loaded: str = dataset_entry.file_in_scope

        main_span.set_attribute("file_to_be_loaded", file_to_be_loaded)
        main_span.set_attribute("code_type", feature_flags["codeType"])

        source_code: str = ""
        # First Feature Flag - Which sourcecode to use
        if feature_flags["codeType"] == CodeType.MINIFIED.value:
            source_code = dataset_entry.minimized_with_comments.get(
                file_to_be_loaded, ""
            )
        elif feature_flags["codeType"] == CodeType.MINIFIED_NO_COMMENT.value:
            source_code = dataset_entry.minimized_no_comments.get(file_to_be_loaded, "")
        elif feature_flags["codeType"] == CodeType.ALL.value:
            full_filepath = Path(dataset_entry.repo_path) / file_to_be_loaded
            source_code = full_filepath.read_text()

        assert len(source_code) > 0, "Source code is empty"

        error_text: str = ""
        # Second Feature Flag: Which Errors to use
        # if feature_flags["errorType"] == ErrorType.FULL:
        # error_text = dataset_entry.initial_error_lines
        if feature_flags["errorType"] == ErrorType.MINIFIED.value:
            error_text = dataset_entry.minified_error_lines
        elif feature_flags["errorType"] == ErrorType.SUPER_MINIFIED.value:
            error_text = dataset_entry.super_minified_error_lines

        if feature_flags["errorType"] != ErrorType.OMIT.value:
            assert len(error_text) > 0, "Error text is empty"

        dependency_change_text: str = ""
        # Third Feature Flag: Which Dependency Changes to use
        if (
            feature_flags["dependencyChangeType"]
            == DependencyChangeType.MINIFIED_PARSED.value
        ):
            dependency_change_text = dataset_entry.version_upgrade_str
        elif feature_flags["dependencyChangeType"] == DependencyChangeType.DIFF.value:
            dependency_change_text = dataset_entry.updated_dependency_diff

        if feature_flags["dependencyChangeType"] != DependencyChangeType.OMIT.value:
            assert len(dependency_change_text) > 0, "Dependency change text is empty"

        # Fourth Feature Flag: Which API Changes to use
        api_changes_text: str = ""

        # if feature_flags["apiChangeType"] == APIChangeType.JAPI.value:
        #     api_changes = dataset_entry.api_changes
        if feature_flags["apiChangeType"] == APIChangeType.REVAPI.value:
            api_changes_text = dataset_entry.api_changes
        # elif feature_flags["apiChangeType"] == APIChangeType.MARACAS.value:
        #     pass

        if feature_flags["apiChangeType"] != APIChangeType.OMIT.value:
            assert len(api_changes_text) > 0, "API changes are empty"

        omissions: OmissionsType = {
            "api_changes": False,
            "error": False,
            "dependency_change": False,
        }
        # Handle omissions
        if feature_flags["apiChangeType"] == APIChangeType.OMIT:
            omissions["api_changes"] = True
        elif feature_flags["errorType"] == ErrorType.OMIT:
            omissions["error"] = True
        elif feature_flags["dependencyChangeType"] == DependencyChangeType.OMIT:
            omissions["dependency_change"] = True

        diff_params: DiffCallbackParams = DiffCallbackParams(
            code=source_code,
            relative_path=file_to_be_loaded,
            absolute_path=Path(dataset_entry.repo_path) / file_to_be_loaded,
            api_changes=api_changes_text,
            error_text=error_text,
            omissions=omissions,
            dependency_change=dependency_change_text,
        )

        total_input = (
            FILE_EDITING_RULES
            + """---
Follow the following format.
Updated Dependency Details: The details of the updated dependency version.
Api Changes: Changes in the API of the dependency.
Initial Error: The maven error that occurred during the build.
Code: The source code of the program.
Path: The path to the file that needs to be edited.
Previous Answer: past Answer: with errors
Instructions: Some instructions you must satisfy
Answer: A compliant diff to fix the changes in the API
---"""
        )
        for key, value in diff_params.items():
            if isinstance(value, list):
                value = json.dumps(value)
            if isinstance(value, Path):
                value = value.as_posix()
            if key == "omissions":
                continue

            if key == "api_changes" and diff_params["omissions"]["api_changes"]:
                continue
            if (
                key == "dependency_change"
                and diff_params["omissions"]["dependency_change"]
            ):
                continue
            if key == "error_text" and diff_params["omissions"]["error"]:
                continue

            total_input += str(value) + "\n"
        multi_tokenizer_assert(total_input)

        extracted_diffs: List[str] = generate_diffs_callback(diff_params)

        assert isinstance(extracted_diffs, List), "Diff generation failed, wrong type"
        assert len(extracted_diffs) > 0, "Diff generation failed, empty list"

        with tracer.start_as_current_span("diff") as diff_span:
            coder: UnifiedDiffCoder = UnifiedDiffCoder(repo_dir=dataset_entry.repo_path)
            for diff in extracted_diffs:
                try:
                    is_valid_diff, diff_remarks = coder.apply_edits(diff)
                    diff_span.set_attribute("is_valid_diff", is_valid_diff)
                    # diff_span.set_attribute("diff_remarks", diff_remarks)
                    invalid_diff_callback(is_valid_diff, diff_remarks)
                except Exception as e:
                    diff_span.set_attribute("is_valid_diff", False)
                    diff_span.set_attribute("diff_error", str(e))
                    invalid_diff_callback(False, str(e))

        def diagnostic_stringifier(diagnostic):
            message = (diagnostic.get("message", "")).replace("/mnt/repo/", "")
            start_line = diagnostic["range"]["start"].get("line", 0)
            start_character = diagnostic["range"]["start"].get("character", 0)
            end_line = diagnostic["range"]["end"].get("line", start_line)
            end_character = diagnostic["range"]["end"].get("character", start_character)
            return f"[JAVA] {start_line}:{start_character} to {end_line}:{end_character} - {message}"

        lsp_agent = LSPAgent(Path(dataset_entry.repo_path))
        maven_agent = MavenReproducerAgent(Path(dataset_entry.repo_path))

        if feature_flags["lspCheck"]:
            with (
                lsp_agent.start_container() as container,
                tracer.start_as_current_span("lsp_session") as lsp_span,
            ):

                try:
                    lsp_result_initial, lsp_result_post_patching = (
                        lsp_agent.validate_changes(
                            Path(dataset_entry.file_in_scope), extracted_diffs
                        )
                    )
                    lsp_span.set_attribute(
                        "lsp_initial", json.dumps(lsp_result_initial)
                    )
                    lsp_span.set_attribute(
                        "lsp_post_patching", json.dumps(lsp_result_post_patching)
                    )

                    post_patching_diagnostics = lsp_result_post_patching["diagnostics"]
                    initial_diagnostics_set: set = set(
                        diagnostic_stringifier(d)
                        for d in lsp_result_initial["diagnostics"]
                    )
                    post_patching_diagnostics_set: set = set(
                        diagnostic_stringifier(d) for d in post_patching_diagnostics
                    )
                    added_diagnostics_set: set = (
                        post_patching_diagnostics_set - initial_diagnostics_set
                    )
                    lsp_span.set_attribute(
                        "added_diagnostics_set_raw",
                        json.dumps(list(added_diagnostics_set)),
                    )
                    added_diagnostics: list[str] = [
                        diagnostic_stringifier(d)
                        for d in post_patching_diagnostics
                        if diagnostic_stringifier(d) in added_diagnostics_set
                    ]

                    lsp_span.set_attribute("added_diagnostics", added_diagnostics)

                    multi_tokenizer_assert(total_input + json.dumps(added_diagnostics))
                    if added_diagnostics:
                        diagnostic_callback(added_diagnostics, None)
                except Exception as e:
                    lsp_span.set_attribute("lsp_error", str(e))
                    diagnostic_callback([], str(e))
                finally:
                    git_agent.discard_changes()

        diff_info: DiffInfo = {
            "compilation_has_succeeded": False,
            "test_has_succeeded": False,
            "error_text": "",
        }
        with (
            maven_agent.start_container() as container,
            tracer.start_as_current_span("lsp_mvn_session") as mvn_span,
        ):
            try:
                (compilation_has_succeeded, test_has_succeeded), error_text = (
                    maven_agent.compile_maven(extracted_diffs, run_tests=True)
                )

                error_text = error_text.replace(dataset_entry.repo_path, "")
                mvn_span.set_attribute(
                    "mvn_compile_has_errors", compilation_has_succeeded
                )
                mvn_span.set_attribute("mvn_compile_error_text", error_text)

                pre_input = total_input + error_text
                if feature_flags["lspCheck"]:
                    pre_input += json.dumps(added_diagnostics)

                multi_tokenizer_assert(pre_input)
                compile_callback(compilation_has_succeeded, error_text)
                diff_info["compilation_has_succeeded"] = compilation_has_succeeded
                diff_info["error_text"] = error_text

                mvn_span.set_attribute("mvn_test_has_errors", test_has_succeeded)
                mvn_span.set_attribute("mvn_test_error_text", error_text)
                test_callback(test_has_succeeded, error_text)
                diff_info["test_has_succeeded"] = test_has_succeeded

            except AssertionError as e:
                raise e
            except Exception as e:
                mvn_span.set_attribute("mvn_error", str(e))
                compile_callback(False, str(e))
            finally:
                git_agent.discard_changes()

        return extracted_diffs, diff_info
