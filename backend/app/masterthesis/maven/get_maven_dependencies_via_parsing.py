def get_dependencies_via_parsing() -> dict[str, str]:
    """
    Parses the pom.xml file and extracts the dependencies defined in it.

    Returns:
      A dictionary containing the parsed dependencies, where the keys are in the format "group_id::artifact_id"
      and the values are the corresponding versions.
    """
    from xml.etree import ElementTree as et

    # Define the namespace
    ns = {"maven": "http://maven.apache.org/POM/4.0.0"}
    et.register_namespace("", ns["maven"])

    # Parse the XML file
    tree = et.parse("test-parse.pom.xml")
    root = tree.getroot()

    # Find all dependencies
    dependencies = root.findall(".//maven:dependencies", ns)

    # Print dependencies
    parsed_dependencies = {}
    for dependency in dependencies:
        for dep in dependency.findall("maven:dependency", ns):
            group_id = (
                dep.find("maven:groupId", ns).text
                if dep.find("maven:groupId", ns) is not None
                else ""
            )
            artifact_id = (
                dep.find("maven:artifactId", ns).text
                if dep.find("maven:artifactId", ns) is not None
                else ""
            )
            version = (
                dep.find("maven:version", ns).text
                if dep.find("maven:version", ns) is not None
                else ""
            )
            parsed_dependencies[group_id + "::" + artifact_id] = version

    return parsed_dependencies
