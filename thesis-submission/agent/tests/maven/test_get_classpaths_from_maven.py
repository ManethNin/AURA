import unittest
import subprocess
from unittest.mock import patch
from masterthesis.maven.get_classpaths_from_maven import get_classpaths_from_maven


class TestGetClasspathsFromMaven(unittest.TestCase):

    @patch("masterthesis.maven.get_classpaths_from_maven.requests.get")
    def test_failed_download(self, mock_get):
        # Mock the response from requests.get
        mock_get.return_value.status_code = 404

        # Call the function with an invalid download link
        with self.assertRaises(Exception) as e:
            get_classpaths_from_maven("https://example.com/nonexistent.jar")

        # Assert that the function raises an exception
        self.assertEqual(str(e.exception), "Error downloading JAR file: 404")

    @patch("masterthesis.maven.get_classpaths_from_maven.requests.get")
    @patch("masterthesis.maven.get_classpaths_from_maven.subprocess.run")
    def test_successful_extraction(self, mock_run, mock_get):
        # Mock the response from requests.get
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"Jar file content"

        # Mock the result of subprocess.run
        mock_run.return_value.stdout = "com/example/Class1.class\ncom/example/Class2.class\ncom/example/Class3.class\ncom/example2/Class3.class\n"
        mock_run.return_value.check_returncode.return_value = None

        # Call the function with a valid download link
        classes, packages = get_classpaths_from_maven("https://example.com/myjar.jar")

        # Assert that the function returns the expected results
        self.assertEqual(
            classes,
            [
                "com.example.Class1",
                "com.example.Class2",
                "com.example.Class3",
                "com.example2.Class3",
            ],
        )
        self.assertEqual(packages, ["com.example", "com.example2"])


if __name__ == "__main__":
    unittest.main()
