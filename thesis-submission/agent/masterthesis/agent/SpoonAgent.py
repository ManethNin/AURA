import subprocess
import sys
import traceback
from pathlib import Path


class SpoonAgent:
    END_OF_INPUT_MARKER = "##END_OF_INPUT##"

    @staticmethod
    def invoke_ast_transformation(
        base_path: Path, maven_errors_dict, include_comments: bool = True
    ):
        maven_target_path = Path(
            "spoon-transformer/target/spoon-transformer-1.0-SNAPSHOT-jar-with-dependencies.jar"
        )
        jar_path = Path(__file__).parent.parent.parent / maven_target_path

        # Prepare the command
        command = ["java", "-jar", str(jar_path)]

        if not include_comments:
            command.append("--no-comments")

        # Run the Java application

        input_data = []
        for file_name, errors in maven_errors_dict.items():
            for line, column in errors:
                input_data.append(f"{base_path /file_name}:{line}:{column}")
        input_data.append(SpoonAgent.END_OF_INPUT_MARKER)
        input_string = "\n".join(input_data) + "\n"

        try:
            result = subprocess.run(
                command, input=input_string, capture_output=True, text=True, check=True
            )

            # Parse the output
            return SpoonAgent.parse_output(result.stdout)

        except subprocess.CalledProcessError as e:
            print(
                f"Error running Java application. Return code: {e.returncode}",
                file=sys.stderr,
            )
            print(f"Standard error: {e.stderr}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Error running Java application: {e}", file=sys.stderr)
            return None

    @staticmethod
    def parse_output(output):
        result = {}
        current_file = None
        current_content = []

        for line in output.split("\n"):
            if line.startswith("FILE_START:"):
                if current_file:
                    result[current_file] = "\n".join(current_content)
                current_file = line.split(":", 1)[1]
                current_content = []
            elif line == "FILE_END":
                if current_file:
                    result[current_file] = "\n".join(current_content)
                current_file = None
                current_content = []
            elif current_file:
                current_content.append(line)

        return result


# # Example usage
# maven_errors = {
#     "TestClass.java": [(10, 5), (20, 8)],
#     "AnotherClass.java": [(15, 3), (30, 12)]
# }

# modified_class = SpoonAgent.extract_error_methods(java_file_path, maven_errors)
# if modified_class:
#     print(modified_class)
