import tempfile
import pytest
from masterthesis.agent.DiffAgent import DiffAgent


@pytest.fixture
def initial_content_path():
    with tempfile.NamedTemporaryFile(delete=False) as initial_file:
        initial_file.write(
            b"This is a sample file.\nIt has multiple lines.\nEach line is different."
        )
        return initial_file.name


def test_valid_unix_diff(initial_content_path):
    diff_text = """--- test1.txt   2024-06-29 00:01:21
+++ test2.txt   2024-06-29 00:01:43
@@ -1,3 +1,3 @@
-This is a sample file.
+This is a modified file.
 It has multiple lines.
 Each line is different.
\\ No newline at end of file"""

    agent = DiffAgent(diff_text)
    assert agent.is_valid_diff(initial_content_path) is True


def test_malformed_unix_diff(initial_content_path):
    malformed_diff_text = """--- test1.txt   2024-06-29 00:01:21
+++ test2.txt   2024-06-29 00:01:43
@@ -1,3 +1,3 @@
-This is a sample file.
+This is a modified file.
+Malformed line.
 It has multiple lines.
 Each line is different.
\\ No newline at end of file"""

    agent = DiffAgent(malformed_diff_text)
    assert agent.is_valid_diff(initial_content_path) is False


if __name__ == "__main__":
    pytest.main()
