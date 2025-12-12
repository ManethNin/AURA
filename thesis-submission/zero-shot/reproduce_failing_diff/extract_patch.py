import os
from pathlib import Path

repos_dir = Path(__file__).parent / "repos"

for root, dirs, files in os.walk(repos_dir):
    for directory in dirs:
        patch_name = directory
        patch_path = os.path.join(root, directory, "fix.patch")

        if os.path.isfile(patch_path):
            # Process the patch file here
            print(f"Found patch: {patch_name} - {patch_path}")
            with open(patch_name + ".patch", "w") as patch_file:
                with open(patch_path, "r") as patch_file_handle:
                    patch_file.write(patch_file_handle.read())
