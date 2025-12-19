from collections import defaultdict
import re

java_error_pattern = re.compile(
    r"(?:\[(?:ERROR|WARN|INFO)\]\s+)?([^:\[]+\.java):?\[?(\d+)(?:,(\d+))?\]?"
)


extended_java_error_pattern = re.compile(
    r"(?:\[(?:ERROR|WARN|INFO)\]\s+)?([^:\[]+\.java):?\[?(\d+)(?:,(\d+))?\]\s(.+?)(?=\[ERROR\]|\[INFO\]|\Z)",
    re.DOTALL,
)


def find_compilation_errors(initial_error_lines):
    errors = defaultdict(list)
    for match in extended_java_error_pattern.findall(initial_error_lines):
        filename, line, col, message = match
        errors[filename].append((line, col, message))
    return errors
