import pytest
from unittest.mock import mock_open, patch
from masterthesis.maven.get_maven_dependencies_via_parsing import (
    get_dependencies_via_parsing,
)


@pytest.fixture
def mock_pom_xml():
    return """<project xmlns="http://maven.apache.org/POM/4.0.0"
              xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
              xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
                                  http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>my-project</artifactId>
    <version>1.0-SNAPSHOT</version>
    <dependencies>
        <dependency>
            <groupId>com.example</groupId>
            <artifactId>dependency1</artifactId>
            <version>1.0.0</version>
        </dependency>
        <dependency>
            <groupId>com.example</groupId>
            <artifactId>dependency2</artifactId>
            <version>2.0.0</version>
        </dependency>
        <dependency>
            <groupId>com.example</groupId>
            <artifactId>dependency3</artifactId>
        </dependency>
    </dependencies>
</project>"""


def test_get_dependencies_via_parsing(mock_pom_xml):
    with patch("builtins.open", mock_open(read_data=mock_pom_xml)):
        # Replace the actual file path with the mocked one
        with patch("xml.etree.ElementTree.parse") as mock_parse:
            from xml.etree import ElementTree as et

            mock_parse.return_value = et.ElementTree(et.fromstring(mock_pom_xml))
            result = get_dependencies_via_parsing()
            expected = {
                "com.example::dependency1": "1.0.0",
                "com.example::dependency2": "2.0.0",
                "com.example::dependency3": "",
            }
            assert result == expected
