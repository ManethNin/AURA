from typing import List

from tree_sitter import Parser


def collect_imports(file_path: str, parser: Parser) -> List[str]:
    """
    Collects import statements from a given file.

    Args:
        file_path (str): The path to the file.

    Returns:
        List[str]: A list of import statements found in the file.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    tree = parser.parse(bytes(source_code, "utf8"))
    root_node = tree.root_node

    imports = []

    def traverse(node):
        if node.type == "import_declaration":
            # print("import_declaration", source_code[node.start_byte:node.end_byte])
            import_path = (
                source_code[node.start_byte : node.end_byte]
                .replace("import ", "")
                .replace(";", "")
                .strip()
            )
            imports.append(import_path)
        for child in node.children:
            traverse(child)

    traverse(root_node)
    return imports
