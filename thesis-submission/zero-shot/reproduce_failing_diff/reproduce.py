import os
import json
import subprocess


# Function to write content to a file
def write_to_file(directory, filename, content):
    with open(os.path.join(directory, filename), "w") as file:
        file.write(str(content))


# Function to create folders and files from JSON data
def create_folders_from_json(json_data, base_directory):
    # Create the base directory if it doesn't exist
    os.makedirs(base_directory, exist_ok=True)

    # Iterate over each commit in the JSON data
    for commit_hash, commit_data in json_data.items():
        unittest_directory = os.path.join(base_directory, "unittest")
        os.makedirs(unittest_directory, exist_ok=True)
        commit_directory = os.path.join(base_directory, commit_hash)
        os.makedirs(commit_directory, exist_ok=True)

        repo_dir = os.path.join(commit_directory, "repo")
        os.makedirs(repo_dir, exist_ok=True)
        repo_slug = commit_data["input"]["repo_slug"]
        _ = subprocess.run(
            ["git", "clone", f"https://github.com/{repo_slug}.git", repo_dir],
            capture_output=True,
            check=True,
        )
        _ = subprocess.run(
            ["git", "fetch", "--depth", "2", "origin", commit_hash],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )
        _ = subprocess.run(
            ["git", "checkout", commit_hash],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )

        for key, value in commit_data.items():
            if key == "input":
                # Special treatment for input key
                input_directory = os.path.join(commit_directory, "input")
                os.makedirs(input_directory, exist_ok=True)

                for input_key, input_value in value.items():
                    if input_key == "prepared_file":
                        write_to_file(commit_directory, "original.java", input_value)
                        write_to_file(
                            unittest_directory, commit_hash + ".java", input_value
                        )
                        continue
                    filename = f"{input_key}.txt"
                    if isinstance(input_value, list):
                        input_value = "\n".join(input_value)
                    write_to_file(input_directory, filename, input_value)

            else:
                # General treatment for other keys
                filename = f"{key}.txt"
                if isinstance(value, list):
                    value = "\n".join(value)
                write_to_file(commit_directory, filename, value)
                if key == "patch":
                    write_to_file(unittest_directory, commit_hash + ".diff", value)


# Path to the JSON file
json_file_path = (
    "/Users/anon/Projects/masterthesis/reproduce_failing_diff/errors.json"
)

# Load the JSON data
with open(json_file_path, "r") as file:
    file_text = file.read()
    print(file_text)
    assert len(file_text) > 0, "File is empty"
    data = json.loads(file_text)

# Base directory to create commit folders
base_directory = (
    "/Users/anon/Projects/masterthesis/reproduce_failing_diff/committs"
)

# Create folders and files from JSON data
create_folders_from_json(data, base_directory)

print("Folders and files created successfully.")
