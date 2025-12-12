from enum import Enum
from typing import TypedDict


class CodeType(Enum):
    MINIFIED = "MINIFIED"
    MINIFIED_NO_COMMENT = "MINIFIED_NO_COMMENT"
    ALL = "ALL"


class ErrorType(Enum):
    # FULL = "FULL"
    MINIFIED = "MINIFIED"
    SUPER_MINIFIED = "SUPER_MINIFIED"
    OMIT = "OMIT"


class DependencyChangeType(Enum):
    MINIFIED_PARSED = "MINIFIED_PARSED"
    DIFF = "DIFF"
    OMIT = "OMIT"


class APIChangeType(Enum):
    # JAPI = "JAPI"
    REVAPI = "REVAPI"
    # MARACAS = "MARACAS"
    OMIT = "OMIT"


class OmissionsType(TypedDict):
    api_changes: bool
    error: bool
    dependency_change: bool


class FeatureFlags(TypedDict):
    codeType: CodeType
    errorType: ErrorType
    dependencyChangeType: DependencyChangeType
    apiChangeType: APIChangeType
    lspCheck: bool
    max_hops: int
