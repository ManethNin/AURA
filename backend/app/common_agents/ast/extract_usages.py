import logging
from typing import Dict, List

from tree_sitter import Parser

logging.basicConfig(level=print, format="%(asctime)s - %(levelname)s - %(message)s")


def extract_usages(
    file_path: str,
    dependency_classes: List[str],
    imported_classes: List[str],
    parser: Parser,
) -> List[Dict]:
    """
    Extracts usages of dependency classes and imported classes in a given source code file.

    Args:
        file_path (str): The source code as a string.
        dependency_classes (List[str]): A list of dependency classes.
        imported_classes (List[str]): A list of imported classes.
        parser (Parser): The parser object used to parse the source code.

    Returns:
        List[dict]: A list of dictionaries representing the usages found. Each dictionary contains the following keys:
            - 'class': The name of the class being used.
            - 'start_point': The starting position of the usage in the source code.
            - 'end_point': The ending position of the usage in the source code.
            - 'type': The type of usage ('object_creation' or 'method_invocation').
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()
    tree = parser.parse(bytes(source_code, "utf8"))
    root_node = tree.root_node

    usages = []
    object_type_mapping = {}

    def log_node(node, level=0):
        indent = "  " * level
        node_text = source_code[node.start_byte : node.end_byte].replace("\n", "\\n")
        print(
            f"{indent}Node type: {node.type}, text: '{node_text}', start: {node.start_point}, end: {node.end_point}"
        )

    def traverse(node, level=0):
        log_node(node, level)
        if node.type == "object_creation_expression":
            type_node = node.child_by_field_name("type")
            if type_node and type_node.type == "type_identifier":
                identifier_name = source_code[type_node.start_byte : type_node.end_byte]
                print(f"Found object creation: {identifier_name}")
                if (
                    identifier_name in dependency_classes
                    and identifier_name in imported_classes
                ):
                    object_node = node.child_by_field_name("object")
                    print(object_node, object_node.type)
                    if object_node and object_node.type == "identifier":
                        object_name = source_code[
                            object_node.start_byte : object_node.end_byte
                        ]
                        object_type_mapping[object_name] = identifier_name
                        print(
                            f"Mapping object: {object_name} to type: {identifier_name}"
                        )
                    usages.append(
                        {
                            "class": identifier_name,
                            "start_point": type_node.start_point,
                            "end_point": type_node.end_point,
                            "type": "object_creation",
                        }
                    )
        elif node.type == "method_invocation":
            object_node = node.child_by_field_name("object")
            method_node = node.child_by_field_name("name")
            if object_node and object_node.type == "identifier":
                object_name = source_code[object_node.start_byte : object_node.end_byte]
                if object_name in object_type_mapping:
                    class_name = object_type_mapping[object_name]
                    print(
                        f"Found method invocation on object: {object_name} of type {class_name}"
                    )
                    usages.append(
                        {
                            "class": class_name,
                            "start_point": object_node.start_point,
                            "end_point": object_node.end_point,
                            "type": "method_invocation",
                        }
                    )
                traverse(object_node, level + 1)
            elif object_node:
                traverse(object_node, level + 1)

            if method_node:
                method_name = source_code[method_node.start_byte : method_node.end_byte]
                if object_node and object_node.type == "identifier":
                    object_name = source_code[
                        object_node.start_byte : object_node.end_byte
                    ]
                    if object_name in object_type_mapping:
                        class_name = object_type_mapping[object_name]
                        print(
                            f"Found method invocation: {method_name} on object: {object_name} of type {class_name}"
                        )
                        usages.append(
                            {
                                "class": class_name,
                                "start_point": method_node.start_point,
                                "end_point": method_node.end_point,
                                "type": "method_invocation",
                            }
                        )
                traverse(method_node, level + 1)

        for child in node.children:
            traverse(child, level + 1)

    traverse(root_node)
    return usages
