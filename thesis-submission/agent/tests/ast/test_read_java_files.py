from masterthesis.ast.read_java_files import read_java_files


def test_read_java_files(test_project_directory, test_files):
    java_files = read_java_files(test_project_directory)
    for test_file in test_files.values():
        assert test_file in java_files
