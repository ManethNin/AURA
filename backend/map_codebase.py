import os
import ast
import json
import sys

def analyze_file(filepath, base_dir):
    rel_path = os.path.relpath(filepath, base_dir).replace('\\', '/')
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content)
            
        imports = []
        definitions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module if node.module else ''
                for alias in node.names:
                    if alias.name == '*':
                        imports.append(f"{module}.*")
                    else:
                        imports.append(f"{module}.{alias.name}")
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                definitions.append(f"def {node.name}")
            elif isinstance(node, ast.ClassDef):
                definitions.append(f"class {node.name}")
                
        return {
            "path": rel_path,
            "imports": imports,
            "definitions": definitions
        }
    except Exception as e:
        return {
            "path": rel_path,
            "error": str(e)
        }

def map_codebase(root_dir):
    data = []
    excludes = ['.venv', '__pycache__', '.git', '.pytest_cache', 'alembic']
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Mutating dirnames inline to skip excluded directories
        dirnames[:] = [d for d in dirnames if d not in excludes and not d.startswith('.')]
        
        for filename in filenames:
            if filename.endswith('.py'):
                filepath = os.path.join(dirpath, filename)
                info = analyze_file(filepath, root_dir)
                data.append(info)
    return data

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python map_codebase.py <target_dir> <output_json_path>")
        sys.exit(1)
        
    target_dir = sys.argv[1]
    output_path = sys.argv[2]
    
    result = map_codebase(target_dir)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    
    print(f"Codebase mapped: {len(result)} files analyzed.")
