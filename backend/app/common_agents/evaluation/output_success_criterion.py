from typing import Any


def output_success_criterion(output: list[Any]):
    if (
        isinstance(output, dict)
        and "test_has_succeeded" in output
        and output["test_has_succeeded"]
    ):
        return True
    if output is not None and len(output) > 0:
        if all(isinstance(item, str) for item in output):
            return True
        if len(output) == 2 and output[0] is not None and isinstance(output[1], dict):
            return True
    return False
