import tempfile
import unittest
from unittest.mock import patch
from masterthesis.maven.get_maven_dependencies_via_cli import (
    get_maven_dependencies_via_cli,
)
import os
import subprocess


class TestGetMavenDependenciesViaCli(unittest.TestCase):

    @patch("subprocess.run")
    def test_get_maven_dependencies_via_cli_success(self, mock_subprocess_run):
        # Mock the subprocess.run function to return a successful result
        mock_subprocess_run.return_value.stdout = "BUILD SUCCESS"
        mock_subprocess_run.return_value.stderr = ""
        mock_subprocess_run.return_value.check_returncode.return_value = None

        # Call the function under test
        result = get_maven_dependencies_via_cli()

        # Assert that the result is not None
        self.assertIsNotNone(result)

        # Assert that the result is a list
        self.assertIsInstance(result, list)

        # Assert that the result is empty
        self.assertEqual(len(result), 0)

    @patch("subprocess.run")
    def test_get_maven_dependencies_via_cli_failure(self, mock_subprocess_run):
        # Mock the subprocess.run function to return a failed result
        mock_subprocess_run.return_value.stdout = "BUILD FAILURE"
        mock_subprocess_run.return_value.stderr = "Error: Failed to build"
        mock_subprocess_run.return_value.check_returncode.side_effect = (
            subprocess.CalledProcessError(1, "mvn")
        )

        # Call the function under test
        result = get_maven_dependencies_via_cli()

        # Assert that the result is None
        self.assertIsNone(result)

    @patch("subprocess.run")
    def test_get_maven_dependencies_via_cli_exclude_transitive(
        self, mock_subprocess_run
    ):
        # Mock the subprocess.run function to return a successful result
        mock_subprocess_run.return_value.stdout = "BUILD SUCCESS"
        mock_subprocess_run.return_value.stderr = ""
        mock_subprocess_run.return_value.check_returncode.return_value = None

        # Call the function under test with exclude_transitive_dependencies set to False
        result = get_maven_dependencies_via_cli(exclude_transitive_dependencies=False)

        # Assert that the result is not None
        self.assertIsNotNone(result)

        # Assert that the result is a list
        self.assertIsInstance(result, list)

        # Assert that the result is empty
        self.assertEqual(len(result), 0)

    @patch("subprocess.run")
    @patch("tempfile.NamedTemporaryFile")
    def test_get_maven_dependencies_via_cli_specific_result(
        self, mock_tempfile_namedtemporaryfile, mock_subprocess_run
    ):
        # Mock the subprocess.run function to return a specific result
        mock_subprocess_run.return_value.stdout = "BUILD SUCCESS"
        mock_subprocess_run.return_value.stderr = ""
        mock_subprocess_run.return_value.check_returncode.return_value = None

        file_name = "/tmp/bla.txt"
        with open(file_name, "w", encoding="utf-8") as temp_file:

            mock_tempfile_namedtemporaryfile.return_value.__enter__.return_value.name = (
                file_name
            )

            temp_file.write(
                """
The following files have been resolved:
   com.github.aserg-ufmg:apidiff:jar:2.0.0:compile[36m -- module apidiff[0;1;33m (auto)[m
   com.fasterxml.jackson.core:jackson-databind:jar:2.12.3:compile[36m -- module com.fasterxml.jackson.databind[m
   org.eclipse.jgit:org.eclipse.jgit:jar:5.11.0.202103091610-r:compile[36m -- module org.eclipse.jgit[0;1m [auto][m
"""
            )
            temp_file.flush()

            # Call the function under test
            result = get_maven_dependencies_via_cli()

            # Assert that the result is not None
            self.assertIsNotNone(result)

            # Assert that the result is a list
            self.assertIsInstance(result, list)

            # Assert that the result contains the expected dependencies
            expected_dependencies = [
                {
                    "group_id": "com.github.aserg-ufmg",
                    "artifact_id": "apidiff",
                    "dependency_type": "jar",
                    "version": "2.0.0",
                    "scope": "compile",
                    "module": "apidiff",
                },
                {
                    "group_id": "com.fasterxml.jackson.core",
                    "artifact_id": "jackson-databind",
                    "dependency_type": "jar",
                    "version": "2.12.3",
                    "scope": "compile",
                    "module": "com.fasterxml.jackson.databind",
                },
                {
                    "group_id": "org.eclipse.jgit",
                    "artifact_id": "org.eclipse.jgit",
                    "dependency_type": "jar",
                    "version": "5.11.0.202103091610-r",
                    "scope": "compile",
                    "module": "org.eclipse.jgit",
                },
            ]
            self.assertEqual(result, expected_dependencies)


if __name__ == "__main__":
    unittest.main()
