import requests


def get_all_package_versions(group_id: str, artifact_id: str):
    """
    Retrieves all versions of a Maven artifact from the Maven Central Repository.

    Args:
        group_id (str): The group ID of the Maven artifact.
        artifact_id (str): The artifact ID of the Maven artifact.

    Returns:
        list: A list of strings representing the versions of the Maven artifact.
    """
    # https://search.maven.org/solrsearch/select?q=g:com.google.inject+AND+a:guice&core=gav&rows=20&wt=json
    search_url = f"https://search.maven.org/solrsearch/select?q=g:{group_id}+AND+a:{artifact_id}&core=gav&rows=200&wt=json"
    response = requests.get(search_url, timeout=10)
    data = response.json()
    versions = []
    for result in data["response"]["docs"]:
        versions.append(result["v"])
    return versions
