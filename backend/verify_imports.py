import ast
import os
import sys

def resolve_module_path(module_name):
    # 'app.nodes.main' -> 'app/nodes/main.py' or 'app/nodes/main/__init__.py'
    parts = module_name.split('.')
    path = os.path.join(*parts)
    if os.path.isfile(path + '.py'):
        return True
    if os.path.isfile(os.path.join(path, '__init__.py')):
        return True
    return False

def check_imports(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=file_path)
        except Exception as e:
            print(f"Syntax error in {file_path}: {e}")
            return False

    all_good = True
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app."):
                    if not resolve_module_path(alias.name):
                        print(f"[{file_path}] Failed to resolve: {alias.name}")
                        all_good = False
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("app."):
                module_name = node.module
                if not resolve_module_path(module_name):
                    # Sometimes the from part doesn't resolve alone, e.g. from app.x import y -> app/x.py
                    # Or it's a package. Let's check if module_name exists.
                    # Wait, if `from app.nodes.main import something`
                    # module_name is 'app.nodes.main'. That should resolve to app/nodes/main.py.
                    print(f"[{file_path}] Failed to resolve FROM: {module_name}")
                    all_good = False
    return all_good

if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    errors = 0
    for root, dirs, files in os.walk("app"):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                if not check_imports(path):
                    errors += 1
    
    if errors == 0:
        print("All local 'app.' imports resolved successfully!")
        sys.exit(0)
    else:
        print(f"Found {errors} files with import errors.")
        sys.exit(1)
