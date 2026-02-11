import shutil
from pathlib import Path
import tempfile
from typing import List

import git
from unidiff import PatchSet, PatchedFile

from app.common_agents.agent.DiffAgent import Patch, PatchError


class GitAgent:
    def __init__(self, repo_path: Path, commit_hash: str, github_slug: str) -> None:
        self.repo_path = repo_path
        self.commit_hash = commit_hash
        if not repo_path.exists():
            self.repo = self.raw_checkout(repo_path, github_slug)
        else:
            try:
                self.repo = git.Repo(repo_path)
            except Exception as e:
                shutil.rmtree(repo_path)
                self.repo = self.raw_checkout(repo_path, github_slug)

    def is_dirty(self) -> bool:
        return self.repo.is_dirty(untracked_files=True)

    def raw_checkout(self, repo_path: Path, github_slug: str) -> None:
        # Clone the repository
        repo = git.Repo.clone_from(f"https://github.com/{github_slug}.git", repo_path)
        repo.git.fetch("origin", self.commit_hash, depth=2)
        repo.git.checkout(self.commit_hash)
        return repo

    def get_full_diff(self) -> str:
        """
        Get the full diff of the current state of the repository compared to the last commit.

        Returns:
            str: A string containing the full diff.
        """
        if not self.is_dirty():
            return "No changes detected."

        # Get the diff for tracked files
        diff = self.repo.git.diff("HEAD", ignore_all_space=True)

        # Get the list of untracked files
        untracked_files = self.repo.untracked_files

        if untracked_files:
            diff += "\n\n{Untracked files}:\n"
            for file in untracked_files:
                diff += f"{file}\n"

        return diff

    def apply_diff(self, diff: str) -> List[str]:
        """
        Apply the full diff and return the paths of the modified files.

        Args:
            diff (str): The diff string produced by get_full_diff method.

        Returns:
            List[str]: A list of paths for the modified files.
        """
        if diff == "No changes detected.":
            return []

        modified_files = []

        # Split the diff into sections for tracked and untracked files
        tracked_diff, untracked_diff = (
            diff.split("{Untracked files}:")
            if "{Untracked files}:" in diff
            else (diff, "")
        )

        # Apply changes to tracked files

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".diff", encoding="utf-8", delete=False
        ) as f:
            f.write(tracked_diff)
            f.flush()

            patch = Patch(f.name)
            patch.apply(
                target_dir=self.repo_path.as_posix(),
                ignore_whitespace=True,
                forgiving=True,
            )

            # print(['--ignore-whitespace', '--allow-empty', f.name])
            # self.repo.git.apply(['--ignore-whitespace', '--verbose', '-3', f.name])

            # print(self.repo.is_dirty())
            # print(self.repo.untracked_files)

        # Extract modified file paths from the tracked diff

        patch = PatchSet(tracked_diff)
        modified_set = set()

        def get_file_path(patched_files: List[PatchedFile]):
            for patched_file in patched_files:
                if patched_file.target_file:
                    modified_set.add(Path(*Path(patched_file.target_file).parts[1:]))

        get_file_path(patch.modified_files)
        get_file_path(patch.added_files)
        get_file_path(patch.removed_files)

        modified_files = list(modified_set)

        # Handle untracked files
        if untracked_diff:
            for file_path in untracked_diff.strip().split("\n"):
                file_path = file_path.strip()
                if file_path:
                    full_path = self.repo_path / file_path
                    if not full_path.exists():
                        full_path.touch()
                    modified_files.append(file_path)

        return modified_files

    def discard_changes(self):
        try:
            if self.is_dirty():
                print("Repository is dirty. Discarding changes...")

                # Reset tracked files
                self.repo.head.reset(index=True, working_tree=True)

                # Clean untracked files and directories
                self.repo.git.clean("-fd")

                print("All changes have been discarded.")
        except Exception as e:
            print(f"An error occurred while discarding changes: {e}")

        if self.repo.head.commit.hexsha != self.commit_hash:
            shutil.rmtree(self.repo.working_dir)
            self.repo = self.raw_checkout(self.repo_path, self.commit_hash)
