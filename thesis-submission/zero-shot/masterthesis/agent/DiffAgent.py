import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path, PosixPath
from typing import Optional, Union

from diff_match_patch import diff_match_patch


class PatchError(Exception):
    pass


class Patch:
    def __init__(self, patch_file_path: str) -> None:
        self.patch_file = Path(patch_file_path)

    def apply(
        self,
        original_file_path: str,
        target_dir: Optional[str] = None,
        strip: Optional[int] = 1,
        dry_run: Optional[bool] = False,
        output_location: Optional[str] = None,
        reverse: Optional[bool] = False,
        ignore_whitespace: Optional[bool] = False,
        forgiving: Optional[bool] = False,
    ):
        with tempfile.NamedTemporaryFile(delete=False) as reject_file:
            cmd = ["patch"]

            reject_file_path = reject_file.name

            cmd.append("--reject-file=" + reject_file_path)

            if target_dir:
                cmd.extend(["-d", target_dir])

            cmd.extend(["-p", str(strip)])

            if dry_run:
                cmd.append("--dry-run")

            if ignore_whitespace:
                cmd.append("--ignore-whitespace")

            if output_location:
                cmd.extend(["-o", output_location])

            cmd.append("--posix")
            cmd.append("--verbose")

            if reverse:
                cmd.append("-R")

            cmd.extend(["-i", self.patch_file.as_posix()])

            if not original_file_path:
                raise PatchError("Original file path is required for patching")
            cmd.append(original_file_path)

            print("cmd", " ".join(cmd), "cmd")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            print("patch", result.stdout)

            if result.returncode != 0:
                raise PatchError(
                    f"Patch failed with error: {result.stderr} and output {result.stdout}"
                )

            with open(reject_file_path, "r", encoding="utf-8") as reject_file_handle:
                rejections = reject_file_handle.read()
                if len(rejections) > 0:
                    raise PatchError(f"Patch failed with rejections: {rejections}")

            if output_location:
                with open(output_location, "r", encoding="utf-8") as output_file:
                    read_output_file = output_file.read()
                    if len(read_output_file) == 0:
                        raise PatchError("Output file is empty")
                    return result.stdout, read_output_file
            return result.stdout


class DiffAgent:
    def __init__(self, diff_text) -> None:
        self.diff_text = diff_text

    @contextmanager
    def quick_persist_diff(self, diff_text):
        """
        Persists the given diff text to a temporary file, creates a Patch object from it,
        and yields the Patch object for further processing. The temporary file is deleted
        after the Patch object is no longer needed.

        Args:
            diff_text (str): The diff text to persist.

        Yields:
            Patch: The Patch object created from the diff text.

        """
        patch_file = tempfile.NamedTemporaryFile(delete=False)
        with open(patch_file.name, "w", encoding="utf-8") as patch_file:
            patch_file.write(diff_text)
        unix_patch = Patch(patch_file.name)
        try:
            yield unix_patch
        finally:
            os.remove(patch_file.name)

    def apply_diff(self, original_file_path: str) -> tuple[str, str]:
        """
        Applies a unified diff to the initial file content.

        Args:
            diff_text (str): The unified diff to be applied.

        Returns:
            str: The file content after applying the diff.
            str: The output of the patch command.
        """
        with self.quick_persist_diff(self.diff_text) as unix_patch:
            # self._apply_dry(unix_patch, original_file_path)
            # Apply the diff to the source content
            with tempfile.NamedTemporaryFile(delete=False) as output_file:
                output_file_path = output_file.name
                patch_stdout = unix_patch.apply(
                    original_file_path=original_file_path,
                    output_location=output_file_path,
                    forgiving=True,
                )
                with open(output_file_path, "r", encoding="utf-8") as output_file:
                    read_output_file = output_file.read()
                    if len(read_output_file) == 0:
                        raise PatchError("Output file is empty")
                    return read_output_file, patch_stdout

    def is_valid_diff(self, original_file_path_or_content: str) -> bool:
        """
        Checks if a given diff is valid for the initial file content.

        Args:
            diff_text (str): The unified diff to be validated.

        Returns:
            bool: True if the diff is valid, False otherwise.
        """
        is_valid, _ = self.is_valid_diff_with_stdout(original_file_path_or_content)
        return is_valid

    def is_valid_diff_with_stdout(
        self,
        original_file_path_or_content: Union[str, Path],
        ignore_whitespace: bool = True,
    ) -> tuple[bool, str]:
        """
        Checks if a given diff is valid for the initial file content.

        Args:
            original_file_path_or_content (Union[str, Path]): The unified diff to be validated.

        Returns:
            tuple[bool, str]: True if the diff is valid, False otherwise.
        """
        try:
            with self.quick_persist_diff(self.diff_text) as unix_patch:

                # TODO: This is a shitty hack but I dont want to introduce another Regex just yet.
                if (
                    not isinstance(original_file_path_or_content, PosixPath)
                    and " " in original_file_path_or_content
                ):
                    original_file_path = tempfile.NamedTemporaryFile(delete=False).name
                    with open(
                        original_file_path, "w", encoding="utf-8"
                    ) as original_file:
                        original_file.write(original_file_path_or_content)
                else:
                    original_file_path = original_file_path_or_content
                # Apply the diff to the source content
                self._apply_dry(unix_patch, original_file_path, ignore_whitespace)
                return True, ""
        except PatchError as e:

            return False, e

    def _apply_dry(
        self, unix_patch: Patch, original_file_path: str, ignore_whitespace: bool = True
    ):
        return unix_patch.apply(
            dry_run=True,
            original_file_path=original_file_path,
            ignore_whitespace=ignore_whitespace,
        )
