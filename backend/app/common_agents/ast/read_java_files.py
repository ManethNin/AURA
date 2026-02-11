import os
from typing import List


def read_java_files(directory: str) -> List[str]:
    """
    Reads all Java files in the specified directory and its subdirectories.

    Args:
        directory (str): The directory to search for Java files.

    Returns:
        List[str]: A list of file paths to the Java files found.
    """
    java_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".java"):
                java_files.append(os.path.join(root, file))
    return java_files
