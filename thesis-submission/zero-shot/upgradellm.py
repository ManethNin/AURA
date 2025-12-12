# %%
import logging
import os

# %%
import re

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# %%
import json
from pathlib import Path


# commit = "0305beafdecb0b28f7c94264ed20cdc4e41ff067"
# candidates = [commit]

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


import dspy
from dotenv import load_dotenv

# %%
from dspy import InputField, OpenAI,AzureOpenAI, OutputField, settings

from masterthesis.llm.types import DiffCallbackParams, DiffInfo, TokenizerType

load_dotenv(".env")  # load OpenAI API key from .env file

# language_model = "claude-3-5-sonnet@20240620"
language_model = "gemini-1.5-pro-001"
# language_model = "meta/llama-3.1-405b-instruct"
# language_model = "gpt-4o"
# language_model = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
# language_model = "claude-3-haiku@20240307"

# tokenizer_type = TokenizerType.LLAMA3_1

# language_model = "open-mistral-nemo"
# tokenizer_type = TokenizerType.NEMO


# language_model = "gpt-4o-mini"
tokenizer_type = TokenizerType.GPT4O

study_type = "dspy-baseline" 
# study_type = "full"
# study_type = "full-supplement"

# mistralai/Mixtral-8x22B
# open-mistral-nemo-2407


# gpt35 = OpenAI(model="gpt-3.5-turbo", max_tokens=4000)
# gpt35 = AzureOpenAI(model=language_model, max_tokens=4096, temperature=0, api_base=os.getenv("AZURE_OPENAI_ENDPOINT"), api_version="2024-06-01", api_key=os.getenv("AZURE_OPENAI_API_KEY"))

# gpt4o_done_candidates = ['489aad6060454d0b7b34a144e0b345c5a3a199f5',
#  'c7c9590a206d4fb77dd05b9df391d888e6181667',
#  '8502e85f9ee2ff90ce96b47b5904f011e81e8bb8',
#  '90ffd2cd31edecf778d14d0015da9ceab7e53081',
#  '3ff575ae202cdf76ddfa8a4228a1711a6fa1e921',
#  'f26cd85b97b24c07a2e446f43ac8793619fa0724',
#  '5fcd0c3ad7727850c47602b17530dc355e5bd097',
#  'ea33b5101edffc0242967cbf21c1016378b18483',
#  'a80dac86d1caa3958c45c036d93a7d9231d88fbf',
#  '1d43bce1de6a81ac017c233d72f348d3c850299e',
#  '0a11c04038eae517540051dbf51f7f26b7221f20',
#  'a2b0fc53611f8705640773f18c8dd6a47eed3b7f',
#  '1ef97ea6c5b6e34151fe6167001b69e003449f95',
#  'd3af06df4613be146bb9f8034e1a8a3098050c82',
#  'c0f6ab75784dbc13ae8ff47298704c0756cf3a2c',
#  'dcc95f410847ab308db2f2a31ab13e32dc65c670',
#  'ae16b526695fe275ab5e6a1992916875d26da860',
#  '65200df71d5f6ab1c5502f74a5dc7bcbda459563',
#  'cbcafe129e143ef09401470e9d11de9758f298d0',
#  '36859167815292f279e570d39dd2ddbcf1622dc6',
#  '0abf7148300f40a1da0538ab060552bca4a2f1d8',
#  '874ed893a4e46ea5182be2be054715967e58f08f',
#  'b6a48a6e557fad1ceda680618e0a34c7b8c5c087',
#  '1820a966ae02ad8df44d0a0106cba65ceaf3aa95',
#  '1fc5281e0688c44025fe2b390a7d6e3e3088f385',
#  '2dfaa41bfb97674d11f09a5885011f19808548a3',
#  'd54b56b91c11f21b97d4903143b04b7c1f10c255',
#  '165381d26b2c3d2278fde88c16f95807506451fe',
#  'c32185c43be158d32c7d13c5b816991954eb45fa',
#  'a4c360001134c2e3a9f7fbde88a07a9fd767e78e',
#  '28be199c825d419957bc753a9519e8e9ecc6a08e',
#  'af6e5d1cc94f031f29b4838e7a8b56704c8c5de4',
#  '8fbb6deb112102ef7507a8e68c5215e5f481d03b',
#  '067f5d2c81ff87c90755f4ed48f62eb5faa8ecf9']



# gpt35 = dspy.OllamaLocal(model=language_model, max_tokens=1024)

# gpt35 = dspy.Together(model=language_model, max_tokens=4096, temperature=0, backoff_time=120, use_chat_api=True)

# gpt35 = dspy.Mistral(model=language_model, max_tokens=4096, temperature=0.0)

# gpt35 = dspy.Claude(model=language_model, max_tokens=4096)

path_to_sa_file = "/root/thesis/masterthesis-implementation/red-plate-428917-h5-0b222b1d079f.json"

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path_to_sa_file
from dsp.modules import ClaudeVertex
from google.oauth2 import service_account

credentials_sa = service_account.Credentials.from_service_account_file(path_to_sa_file)
# gpt35 = ClaudeVertex(
#     model=language_model,
#     project="stone-ward-432615-i3",
#     location="europe-west1",
#     # credentials=credentials_sa,
#     temperature=0,
# )

from dsp.modules import GoogleVertexAI
gpt35 = GoogleVertexAI(
    model=language_model,
    project="red-plate-428917-h5",
    location="europe-west1",
    credentials=credentials_sa,
    temperature=0
)

# litellm
# lm = OpenAI(model="gpt-3.5-turbo",
#     api_key="anything",
#     api_base="http://0.0.0.0:8000")

# gpt35 = OpenAI(model=language_model,
#     api_key=os.getenv("NVIDIA_API_KEY"),
#     temperature=0,
#     api_base="https://integrate.api.nvidia.com/v1")
settings.configure(lm=gpt35)


language_model = language_model.replace("/", "_")

# assert that /var/run/docker.sock exists
assert Path("/var/run/docker.sock").exists()


from masterthesis.llm.signatures import (
    CodeDiffGenerator,
    CodeDiffGeneratorWithAll,
    CodeDiffGeneratorWithApiChanges,
    CodeDiffGeneratorWithApiChangesAndInitialError,
    CodeDiffGeneratorWithInitialError,
    CodeDiffGeneratorWithUpdatedDependencyDetails,
    CodeDiffGeneratorWithUpdatedDependencyDetailsAndApiChanges,
    CodeDiffGeneratorWithUpdatedDependencyDetailsAndInitialError,
)


def create_code_diff_generator(
    include_updated_dependency_details=False,
    include_api_changes=False,
    include_initial_error=False,
):
    print("include_updated_dependency_details", include_updated_dependency_details)
    print("include_api_changes", include_api_changes)
    print("include_initial_error", include_initial_error)

    if (
        include_updated_dependency_details
        and include_api_changes
        and include_initial_error
    ):
        print("all")
        return CodeDiffGeneratorWithAll
    elif include_updated_dependency_details and include_api_changes:
        print("updated and api")
        return CodeDiffGeneratorWithUpdatedDependencyDetailsAndApiChanges
    elif include_updated_dependency_details and include_initial_error:
        print("updated and initial")
        return CodeDiffGeneratorWithUpdatedDependencyDetailsAndInitialError
    elif include_api_changes and include_initial_error:
        print("api and initial")
        return CodeDiffGeneratorWithApiChangesAndInitialError
    elif include_updated_dependency_details:
        print("updated")
        return CodeDiffGeneratorWithUpdatedDependencyDetails
    elif include_api_changes:
        print("api")
        return CodeDiffGeneratorWithApiChanges
    elif include_initial_error:
        print("initial")
        return CodeDiffGeneratorWithInitialError
    else:
        print("base")
        return CodeDiffGenerator()


import os
import tempfile

# %%
from collections import defaultdict
from typing import DefaultDict, List, Union

from dspy.predict import Retry
from dspy.primitives.assertions import assert_transform_module, backtrack_handler

from masterthesis.agent.aider.AdvancedDiffAgent import UnifiedDiffCoder
from masterthesis.agent.DiffAgent import DiffAgent
from masterthesis.agent.DockerAgent import DockerAgent
from masterthesis.agent.LSPAgent import LSPAgent
from masterthesis.agent.MarkdownAgent import MarkdownAgent
from masterthesis.dataset.dataset_types import DatasetEntry
from masterthesis.dataset.feature_flags import (
    APIChangeType,
    CodeType,
    DependencyChangeType,
    ErrorType,
    FeatureFlags,
)
from masterthesis.llm.pipeline import pipeline
from masterthesis.llm.types import DiffCallbackParams, DiffInfo, TokenizerType

import tempfile
import platform

if "macOS" in platform.platform():
    os.environ["TMPDIR"] = "/tmp/colima"
    tempfile.tempdir = "/tmp/colima"


candidate_results: DefaultDict[str, dict] = defaultdict(dict)

dspy.configure(trace=[])


class FixCode(dspy.Module):
    def __init__(self, feature_flags: FeatureFlags, max_hops: int):
        super().__init__()

        include_updated_dependency_details: bool = True
        include_api_changes: bool = True
        include_initial_error: bool = True

        self.feature_flags = feature_flags

        if feature_flags["apiChangeType"] == APIChangeType.OMIT.value:
            print("Omitting API changes")
            include_api_changes = False
        elif feature_flags["dependencyChangeType"] == DependencyChangeType.OMIT.value:
            print("Omitting updated dependency details")
            include_updated_dependency_details = False
        elif feature_flags["errorType"] == ErrorType.OMIT.value:
            print("Omitting initial error")
            include_initial_error = False

        print("Enabling LSP check", feature_flags["lspCheck"])

        code_diff_generator = create_code_diff_generator(
            include_updated_dependency_details=include_updated_dependency_details,
            include_api_changes=include_api_changes,
            include_initial_error=include_initial_error,
        )

        self.generate_diff = dspy.Predict(code_diff_generator)
        self.max_hops = max_hops

    def forward(
        self,
        dataset_entry: DatasetEntry,
    ) -> Union[None, tuple[list[str], DiffInfo]]:
        commit_hash = dataset_entry.commit_hash

        for hop in range(self.max_hops):
            candidate_results[commit_hash]["hop"] = hop
            candidate_results[commit_hash]["max_hops"] = self.max_hops

            def invalid_diff_callback(
                is_valid_diff: bool, diff_remarks: Union[Exception, str]
            ) -> None:
                dspy.Assert(is_valid_diff, f"Invalid diff: {diff_remarks}")

            def diagnostic_callback(
                diagnostics: List[str], error: Union[str, None] = None
            ) -> None:
                if not error:
                    print(f"Diagnostics {len(diagnostics)}", flush=True)
                    dspy.Suggest(
                        len(diagnostics) > 0,
                        f"Java LSP produced Suggestions: {diagnostics}",
                    )
                    if len(diagnostics) == 0:
                        print("Linting passed", flush=True)
                    else:
                        print("Suggested", diagnostics, flush=True)
                else:
                    print("LSP Error, going to compile instead", error, flush=True)

            def compile_callback(has_succeeded: bool, error_text: str) -> None:
                print("Compilation", has_succeeded, error_text)
                was_successful = has_succeeded == True


                if "compiled_protocol" not in candidate_results[commit_hash]:
                    candidate_results[commit_hash]["compiled_protocol"] = []
                if was_successful:
                    candidate_results[commit_hash]["compiled"] = True
                    candidate_results[commit_hash]["compiled_protocol"].append(True)
                    print("Compiled successfully", flush=True)
                else:
                    candidate_results[commit_hash]["compiled"] = False
                    candidate_results[commit_hash]["compiled_protocol"].append(False)
                    print(f"Error during compilation: {error_text}", flush=True)

                dspy.Assert(was_successful, f"Error during compilation: {error_text}")

            def test_callback(has_succeeded: bool, error_text: str) -> None:
                print("Test", has_succeeded, error_text)
                was_successful = has_succeeded == True

                assert (
                    "Source option 6 is no longer supported. Use 7 or later."
                    not in error_text
                ), "Unfixable JVM Error"

                dspy.Assert(was_successful, f"Error during test: {error_text}")
                if was_successful:
                    candidate_results[commit_hash]["tests"] = True
                else:
                    candidate_results[commit_hash]["tests"] = False
                    print(f"Error during test: {error_text}", flush=True)

            def generate_diff_callback(params: DiffCallbackParams) -> List[str]:
                candidate_results[commit_hash]["input"]["prepared_file"] = params[
                    "code"
                ]

                # code, path, initial_error, api_changes, updated_dependency_details
                diff_params = {
                    "code": params["code"],
                    "path": params["relative_path"],
                }

                if not params["omissions"]["api_changes"]:
                    diff_params["api_changes"] = params["api_changes"]
                if not params["omissions"]["dependency_change"]:
                    diff_params["updated_dependency_details"] = params[
                        "dependency_change"
                    ]
                if not params["omissions"]["error"]:
                    diff_params["initial_error"] = params["error_text"]

                # extracted_diff = self.generate_diff(code=code, path=path, api_changes=api_changes, initial_error=initial_error, updated_dependency_diff=updated_dependency_diff).answer
                extracted_diff = self.generate_diff(**diff_params).answer

                candidate_results[commit_hash]["diff_attempts"].append(extracted_diff)

                candidate_results[commit_hash]["raw_output"] = extracted_diff
                return [extracted_diff]

            return pipeline(
                invalid_diff_callback,
                diagnostic_callback,
                compile_callback,
                test_callback,
                generate_diff_callback,
                feature_flags=self.feature_flags,
                dataset_entry=dataset_entry,
                tokenizer_type=tokenizer_type,
            )


# %%
# import phoenix as px

# import shutil

# phoenix_session = px.launch_app()


from openinference.instrumentation.dspy import DSPyInstrumentor
from opentelemetry import trace as trace_api
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)


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


endpoint = "http://127.0.0.1:6006/v1/traces"
resource = Resource(attributes={})
tracer_provider = trace_sdk.TracerProvider(resource=resource)
# span_otlp_exporter = OTLPSpanExporter(endpoint=endpoint)

export_path = Path(os.path.abspath("")) / (
    f"trace_{study_type}_{language_model}.json"
)
tracer_provider.add_span_processor(
    BatchSpanProcessor(FileSpanExporter(export_path.as_posix()))
)

# tracer_provider.add_span_processor(
#     SimpleSpanProcessor(span_exporter=span_otlp_exporter)
# )

trace_api.set_tracer_provider(tracer_provider=tracer_provider)
DSPyInstrumentor().instrument()

import logging

# %%
import traceback
from typing import Dict

from masterthesis.dataset.load_dataset import load_dataset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from opentelemetry import trace as trace_api

tracer = trace_api.get_tracer(__name__)

print("Loading Dataset")


# incomplete_gemini = {'28be199c825d419957bc753a9519e8e9ecc6a08e', 'dbdc7d2c4a28a8d65edcd0cdece91c0bc357b869', '8fbb6deb112102ef7507a8e68c5215e5f481d03b', '7f7de81d28b68b091bef2e6f6ffd1836167be6ea', 'dc9a40fde9a9fee5aaec3f60695385ba539406d4', '14fc5fa696f499cac48401b3a86882b3bf7d9b82', '3572a1ecc0154c61e05505aed56055b9c5e539a6', '88a20ece4db960e35fbfa39fcb40e61daceb15b1', 'f6659d758a437f8b676481fe70671a68a6ee1cde', 'cbcafe129e143ef09401470e9d11de9758f298d0', '5287fc631fa78e7f11d39983824cdd4215b9a03b', '9461431622cf39efe60cf1eb03a94083780c5720', 'c32185c43be158d32c7d13c5b816991954eb45fa', '0305beafdecb0b28f7c94264ed20cdc4e41ff067', 'ae16b526695fe275ab5e6a1992916875d26da860', 'c0f6ab75784dbc13ae8ff47298704c0756cf3a2c', 'f714a41f0ffe9720939d4980da5119d1f45bd770', 'af6e5d1cc94f031f29b4838e7a8b56704c8c5de4', 'acc50dabec6796c091b84c1ada2ae4cbcab8b562', '65200df71d5f6ab1c5502f74a5dc7bcbda459563', '2d733a58045b4bf3669aa00d875e77f9db48c29b', '067f5d2c81ff87c90755f4ed48f62eb5faa8ecf9', 'a26797cdeeecaa3b900ea1e0d5ec0cec66bf03ff', 'd401e189fb6435110e3dc4ca1a94838f167e7ddf', '6c53cd904bd66fc79af8687571e607c259226b81', '4b4c08d502d98d240855013ab76008f5e0243435', 'a4c360001134c2e3a9f7fbde88a07a9fd767e78e', '0e8625f492854a78c0e1ceff67b2abd7e081d42b', '7fb959ccb8c9b32bd6cbc9fc95ed70c4d9c85575', '10d7545c5771b03dd9f6122bd5973a759eb2cd03', '5adde4f1309a1078b39d013a30dc392c97ca7543', '979d6237a50840cd925cc1a33c415ffbbbc42846', '3d29f9a6823fa68763d3148bc0353ac557f2a815', '6ad104c4fb9263ad1bb29e6b33618b8225efd92d', '250cafc7d6ae47d5d4803b5a5e58186eb81fa3b5', 'dcc95f410847ab308db2f2a31ab13e32dc65c670', 'dc9f7910968cd0aa2090e390045ae053693e839a'}


candidates: Dict[str, DatasetEntry] = load_dataset(
    Path(os.path.abspath("")) / "dataset",
    # filter_out=gpt4o_done_candidates,
)

print("Loaded Dataset")

import optuna

from masterthesis.evaluation.output_success_criterion import output_success_criterion


def optuna_objective(trial: optuna.Trial):
    feature_flags = FeatureFlags(
        codeType=trial.suggest_categorical("codeType", [e.value for e in CodeType]),
        errorType=trial.suggest_categorical("errorType", [e.value for e in ErrorType]),
        dependencyChangeType=trial.suggest_categorical(
            "dependencyChangeType", [e.value for e in DependencyChangeType]
        ),
        apiChangeType=trial.suggest_categorical(
            "apiChangeType", [e.value for e in APIChangeType]
        ),
        lspCheck=trial.suggest_categorical("lspCheck", [True, False]),
        max_hops=trial.suggest_categorical("max_hops", [5, 10, 15, 20, 25, 30, 40]),
    )

    total_candidates = len(candidates)

    for idx, (commit_hash, dataset_entry) in enumerate(candidates.items()):
        with tracer.start_as_current_span("Processing commit") as processing_span:
            processing_span.set_attribute("commit_hash", commit_hash)
            processing_span.set_attribute("language_model", language_model)
            processing_span.set_attribute("study_type", study_type)
            processing_span.set_attribute("max_hops", feature_flags["max_hops"])
            print(f"Processing {commit_hash}")

            candidate_results[commit_hash] = {
                "patch": None,
                "error": None,
                "input": dataset_entry.model_dump(),
                "diff_attempts": [],
            }

            max_hops = feature_flags["max_hops"]

            def get_metric():

                # "output": [
                #     null,
                #     {}
                # ],
                return sum(
                    1
                    for result in candidate_results.values()
                    if result["error"] is None
                    and output_success_criterion(result["output"])
                )

            test_backtrack_handler = lambda func: backtrack_handler(
                func, True, max_hops
            )

            fix_code_with_assertions = assert_transform_module(
                FixCode(
                    feature_flags=feature_flags, max_hops=max_hops
                ).map_named_predictors(Retry),
                test_backtrack_handler,
            )

            try:
                patches, diff_info = fix_code_with_assertions(
                    dataset_entry=dataset_entry,
                )
                candidate_results[commit_hash]["output"] = patches
                candidate_results[commit_hash]["diff_info"] = diff_info
                print("Yippie we found a winner!")
                processing_span.set_attribute("patch_success", True)
            except dspy.primitives.DSPyAssertionError as e:
                print(50 * "-")
                print(f"Error processing {commit_hash}: {e}")
                candidate_results[commit_hash]["error"] = str(e)
            except Exception as e:
                print(traceback.format_exc())
                print(f"Error processing {commit_hash}: {e}")
                candidate_results[commit_hash]["error"] = str(e)
            finally:
                data_path = dataset_entry.data_path
                if not data_path:
                    data_path = Path(os.path.abspath("")) / "dataset" / commit_hash
                else:
                    data_path = Path(data_path)

                dataset_out = data_path / "out"
                os.makedirs(dataset_out, exist_ok=True)
                if trial.number != 0:
                    filename = f"{study_type}-{language_model}-execution-errors-{trial.number}.json"
                else:
                    filename = f"{study_type}-{language_model}-execution-errors.json"
                print("Writing to", dataset_out / filename)
                with open(dataset_out / filename, "w", encoding="utf-8") as f:
                    json.dump(
                        candidate_results.get(commit_hash, {}),
                        f,
                        ensure_ascii=True,
                        indent=4,
                    )
                if trial:
                    current_metric = get_metric()

                    print(f"Progress: {idx} / {total_candidates}")
                    trial.report(current_metric, step=idx)

                    # Optionally, you can use a combined metric that considers both progress and success
                    # progress = idx / total_candidates
                    # combined_metric = (current_metric / total_candidates) + (0.5 * progress)
                    # trial.report(combined_metric, step=idx)

                    # if trial.should_prune():
                    #     raise optuna.TrialPruned()
    success_abs = get_metric()

    # with open("errors.json", "w", encoding="utf-8") as f:
    #     f.write(json.dumps(candidate_results))
    return success_abs


# %%


def main():
    print("-"*50)
    print("Running study", study_type)
    print("For LLM", language_model)
    print("-"*50)

    # optuna.logging.get_logger("optuna").addHandler(logging.StreamHandler(sys.stdout))
    study_name = f"pipeline_{language_model}"
    storage_name = "sqlite:///{}.db".format(study_name)
    study = optuna.create_study(
        direction="maximize", storage=storage_name, study_name=study_name+"_"+study_type
    )

    baseline_params = {
        "codeType": CodeType.ALL.value,
        "errorType": ErrorType.MINIFIED.value,
        "dependencyChangeType": DependencyChangeType.MINIFIED_PARSED.value,
        "apiChangeType": APIChangeType.REVAPI.value,
        "lspCheck": False,
        "max_hops": 30,
    }

    if study_type == "dspy-baseline":
        study.enqueue_trial(baseline_params)
        n_trials = 1
    elif study_type == "full":
        n_trials = 3
        # With LSP Check
        study.enqueue_trial(
            {
                **baseline_params,
                "lspCheck": True,
            }
        )

        # With better error type
        study.enqueue_trial({**baseline_params, "errorType": ErrorType.SUPER_MINIFIED.value})

        # With minified code
        study.enqueue_trial({**baseline_params, "codeType": CodeType.MINIFIED.value})

    elif study_type == "full-supplement":
        n_trials = 6

        studies= ["pipeline_claude-3-haiku@20240307_dspy-baseline","pipeline_claude-3-haiku@20240307_full_supplement"]
        
        
        for study_name in studies:

            source_study = optuna.load_study(study_name=study_name, storage=storage_name)
        

            # Iterate over all trials from the source study
            for trial in source_study.trials:
                # Only transfer completed trials to the target study
                if trial.state == optuna.trial.TrialState.COMPLETE:
                    # Create a new FrozenTrial for the target study

                    trial.distributions['max_hops'] = optuna.distributions.CategoricalDistribution([5, 10, 15, 20, 25, 30, 40])

                    new_trial = optuna.trial.FrozenTrial(
                        number=trial.number,
                        value=trial.value,
                        datetime_start=trial.datetime_start,
                        datetime_complete=trial.datetime_complete,
                        params=trial.params,
                        distributions=trial.distributions,
                        user_attrs=trial.user_attrs,
                        system_attrs=trial.system_attrs,
                        state=trial.state,
                        intermediate_values=trial.intermediate_values,
                        trial_id=trial._trial_id,
                    )
                    
                    # Add the trial to the target study
                    study.add_trial(new_trial)
                    n_trials += 1
        # With 40 hops
        study.enqueue_trial(
            {
                **baseline_params,
                "max_hops": 40,
            }
        )
        # RevAPI disabled
        study.enqueue_trial(
            {
                **baseline_params,
                "apiChangeType": APIChangeType.OMIT.value,
            }
        )

        # Dependency Change
        study.enqueue_trial(
            {
                **baseline_params,
                "dependencyChangeType": DependencyChangeType.DIFF.value,
            }
        )


        

    study.optimize(optuna_objective, n_trials=n_trials, show_progress_bar=True)

    print("Best trial:")
    trial = study.best_trial

    print("  Value: ", trial.value)
    print("  Params: ")
    for key, value in trial.params.items():
        print("    {}: {}".format(key, value))

    best_feature_flags = FeatureFlags(
        codeType=CodeType(trial.params["codeType"]),
        errorType=ErrorType(trial.params["errorType"]),
        dependencyChangeType=DependencyChangeType(trial.params["dependencyChangeType"]),
        apiChangeType=APIChangeType(trial.params["apiChangeType"]),
        lspCheck=trial.params["lspCheck"],
    )

    print("Best config", best_feature_flags)


main()
