from enum import Enum
from pathlib import Path
from typing import TypedDict

from app.common_agents.dataset.feature_flags import OmissionsType


class DiffInfo(TypedDict):
    compilation_has_succeeded: bool
    test_has_succeeded: bool
    error_text: str


class DiffCallbackParams(TypedDict):
    code: str
    relative_path: str
    absolute_path: Path
    api_changes: str
    dependency_change: str
    error_text: str
    omissions: OmissionsType


class TokenizerType(Enum):
    GPT4O = ("o200k_base", 125000)
    GPT3 = ("cl100k_base", 13500)
    LLAMA3 = ("meta-llama/Meta-Llama-3-70B-Instruct", 7600)
    LLAMA3_1 = ("meta-llama/Meta-Llama-3.1-70B-Instruct", 125000)
    MIXTRAL = ("non-tekken", 60000)
    NEMO = ("nemo", 125000)
