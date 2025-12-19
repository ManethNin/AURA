# keep in mind, in the future we can also search by classpath

from typing import Optional

import requests


def get_maven_package_metadata(
    artifact_name: str, version: Optional[str] = None
) -> tuple[str, str, str, str]:
    """
    Retrieves Maven package information for a given artifact name and version.

    Args:
        artifact_name (str): The name of the artifact to search for.
        version (str, optional): The version of the artifact. If not provided, the latest version will be searched.

    Returns:
        tuple[str, str, str, str]: A tuple containing the group ID, artifact ID, Maven ID, and download link of the artifact.

    Raises:
        Exception: If there was an error fetching data from Maven Central or if no results were found for the artifact.
    """

    search_url = (
        f"https://search.maven.org/solrsearch/select?q={artifact_name}&rows=50&wt=json"
    )
    if version is not None:
        search_url = f"https://search.maven.org/solrsearch/select?q=a:{artifact_name}%20AND%20v:{version}&rows=50&wt=json"

    # Docs from: https://central.sonatype.org/search/rest-api-guide/
    # https://search.maven.org/solrsearch/select? q=g:com.google.inject%20AND%20a:guice%20AND%20v:3.0%20AND%20l:javadoc%20AND%20p:jar&rows=20&wt=json
    # Mimics searching by coordinate in Advanced Search. This search uses all coordinates ("g" for groupId, "a" for artifactId, "v" for version, "p" for packaging, "l" for classifier)

    # Send the GET request to Maven Central API
    response = requests.get(search_url, timeout=10)
    print(search_url)

    # Check if the request was successful
    if response.status_code != 200:
        raise Exception(
            f"Error fetching data from Maven Central: {response.status_code}"
        )

    # Parse the JSON response
    data = response.json()

    # Check if there are any results
    if data["response"]["numFound"] == 0:
        raise Exception(f"No results found for artifact: {artifact_name}")

    print(
        f"Found {data['response']['numFound']} results for artifact: {artifact_name} with version {version}"
    )

    # Extract the first result
    first_result = data["response"]["docs"][0]
    print(first_result)

    # Extract groupId and artifactId
    group_id = first_result.get("g", "N/A")
    artifact_id = first_result.get("a", "N/A")
    maven_id = first_result.get("id", "N/A")

    # joda-time/joda-time/2.12.7/joda-time-2.12.7.jar
    download_link = f"https://repo1.maven.org/maven2/{group_id.replace('.', '/')}/{artifact_id}/{version}/{artifact_id}-{version}.jar"

    if version is None:
        download_link = f"https://repo1.maven.org/maven2/{group_id.replace('.', '/')}/{artifact_id}/None/{artifact_id}-None.jar"

    return group_id, artifact_id, maven_id, download_link
