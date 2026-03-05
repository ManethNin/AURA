import subprocess
import tempfile

import requests


def get_classpaths_from_maven(download_link: str) -> tuple[list[str], list[str]]:
    """
    Downloads the Maven Central JAR file from the given download link and extracts the classpaths and packages from it.

    Args:
        download_link (str): The URL of the JAR file to download.

    Returns:
        A tuple containing two lists:
        - A list of fully qualified class names extracted from the JAR file.
        - A sorted list of package names extracted from the JAR file.

    Raises:
        Exception: If there is an error downloading the JAR file.

    """
    # jar_url = f"https://search.maven.org/remotecontent?filepath={maven_id}.jar"
    print(download_link)
    response = requests.get(download_link, timeout=10)

    # Check if the request was successful
    if response.status_code != 200:
        raise Exception(f"Error downloading JAR file: {response.status_code}")

    # use tmpfile module
    with tempfile.NamedTemporaryFile(suffix=".jar") as file:
        file.write(response.content)
        # file.seek(0)
        print("downloaded to", file.name)

        try:
            result = subprocess.run(
                ["jar", "tf", file.name], capture_output=True, text=True, check=True
            )
            all_files = result.stdout.splitlines()
            class_files = [f for f in all_files if f.endswith(".class")]

            classes = []
            packages = set()
            for file in class_files:
                print(file)
                if file.endswith(".class"):
                    class_name = file.replace("/", ".").replace(".class", "")
                    classes.append(class_name)
                    package_name = class_name.rsplit(".", 1)[0]
                    packages.add(package_name)
                elif file.endswith("/"):
                    package_name = file.replace("/", ".").rstrip(".")
                    packages.add(package_name)

            return classes, sorted(packages)
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while inspecting the JAR file: {e}")
