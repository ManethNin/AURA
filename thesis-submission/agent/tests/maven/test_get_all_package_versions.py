import unittest
from unittest.mock import patch

from masterthesis.maven.get_all_package_versions import get_all_package_versions


class TestGetAllPackageVersions(unittest.TestCase):
    @patch("masterthesis.maven.get_all_package_versions.requests.get")
    def test_get_all_package_versions(self, mock_get):
        # Mock response from the API
        mock_response = {
            "responseHeader": {
                "status": 0,
                "QTime": 2,
                "params": {
                    "q": "g:org.springframework.boot AND a:spring-boot",
                    "core": "gav",
                    "indent": "off",
                    "fl": "id,g,a,v,p,ec,timestamp,tags",
                    "start": "",
                    "sort": "score desc,timestamp desc,g asc,a asc,v desc",
                    "rows": "200",
                    "wt": "json",
                    "version": "2.2",
                },
            },
            "response": {
                "numFound": 2,
                "start": 0,
                "docs": [
                    {
                        "id": "org.springframework.boot:spring-boot:3.3.0",
                        "g": "org.springframework.boot",
                        "a": "spring-boot",
                        "v": "3.3.0",
                        "p": "jar",
                        "timestamp": 1716471229000,
                        "ec": [
                            ".module",
                            "-sources.jar",
                            ".pom",
                            "-javadoc.jar",
                            ".jar",
                        ],
                        "tags": ["spring", "boot"],
                    },
                    {
                        "id": "org.springframework.boot:spring-boot:3.2.6",
                        "g": "org.springframework.boot",
                        "a": "spring-boot",
                        "v": "3.2.6",
                        "p": "jar",
                        "timestamp": 1716460145000,
                        "ec": [
                            "-sources.jar",
                            ".module",
                            ".pom",
                            "-javadoc.jar",
                            ".jar",
                        ],
                        "tags": ["spring", "boot"],
                    },
                ],
            },
        }
        mock_get.return_value.json.return_value = mock_response

        # Test case 1: Valid group ID and artifact ID
        group_id = "com.google.inject"
        artifact_id = "guice"
        expected_versions = ["3.3.0", "3.2.6"]
        versions = get_all_package_versions(group_id, artifact_id)
        self.assertEqual(versions, expected_versions)

        # Test case 2: Empty response from the API
        mock_response = {"response": {"docs": []}}
        mock_get.return_value.json.return_value = mock_response

        # Test case 3: API timeout
        mock_get.side_effect = TimeoutError

        group_id = "com.example"
        artifact_id = "example-artifact"
        self.assertRaises(TimeoutError, get_all_package_versions, group_id, artifact_id)


if __name__ == "__main__":
    unittest.main()
