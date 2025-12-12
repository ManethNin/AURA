import unittest
from unittest.mock import patch
from masterthesis.maven.get_maven_package_metadata import get_maven_package_metadata


class TestGetMavenPackageMetadata(unittest.TestCase):
    @patch("masterthesis.maven.get_maven_package_metadata.requests.get")
    def test_get_maven_package_metadata_success(self, mock_get):
        # Mock the response from the requests.get method
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "response": {
                "numFound": 1,
                "docs": [
                    {
                        "g": "com.example",
                        "a": "example-artifact",
                        "id": "com.example:example-artifact",
                    }
                ],
            }
        }

        # Call the function under test
        group_id, artifact_id, maven_id, download_link = get_maven_package_metadata(
            "example-artifact", "1.0.0"
        )

        # Assert the expected values
        self.assertEqual(group_id, "com.example")
        self.assertEqual(artifact_id, "example-artifact")
        self.assertEqual(maven_id, "com.example:example-artifact")
        self.assertEqual(
            download_link,
            "https://repo1.maven.org/maven2/com/example/example-artifact/1.0.0/example-artifact-1.0.0.jar",
        )

    @patch("masterthesis.maven.get_maven_package_metadata.requests.get")
    def test_get_maven_package_metadata_success_no_version(self, mock_get):
        # Mock the response from the requests.get method
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "response": {
                "numFound": 1,
                "docs": [
                    {
                        "g": "com.example",
                        "a": "example-artifact",
                        "id": "com.example:example-artifact",
                    }
                ],
            }
        }

        # Call the function under test
        group_id, artifact_id, maven_id, download_link = get_maven_package_metadata(
            "example-artifact"
        )

        # Assert the expected values
        self.assertEqual(group_id, "com.example")
        self.assertEqual(artifact_id, "example-artifact")
        self.assertEqual(maven_id, "com.example:example-artifact")
        self.assertEqual(
            download_link,
            "https://repo1.maven.org/maven2/com/example/example-artifact/None/example-artifact-None.jar",
        )

    @patch("masterthesis.maven.get_maven_package_metadata.requests.get")
    def test_get_maven_package_metadata_no_results(self, mock_get):
        # Mock the response from the requests.get method
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "response": {"numFound": 0, "docs": []}
        }

        # Call the function under test and assert that it raises an exception
        with self.assertRaises(Exception) as context:
            get_maven_package_metadata("non-existent-artifact")

        # Assert the exception message
        self.assertEqual(
            str(context.exception),
            "No results found for artifact: non-existent-artifact",
        )

    @patch("masterthesis.maven.get_maven_package_metadata.requests.get")
    def test_get_maven_package_metadata_error(self, mock_get):
        # Mock the response from the requests.get method
        mock_get.return_value.status_code = 500

        # Call the function under test and assert that it raises an exception
        with self.assertRaises(Exception) as context:
            get_maven_package_metadata("example-artifact")

        # Assert the exception message
        self.assertEqual(
            str(context.exception), "Error fetching data from Maven Central: 500"
        )


if __name__ == "__main__":
    unittest.main()
