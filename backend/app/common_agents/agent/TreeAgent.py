import os


def get_directory_tree(root, include_file_sizes=False, ignore_list=None):
    if ignore_list is None:
        ignore_list = [".git", ".DS_Store", "Thumbs.db", "node_modules"]

    def get_tree(path):
        tree = []
        try:
            for item in os.listdir(path):
                if item in ignore_list:
                    continue

                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    tree.append(
                        {
                            "name": item,
                            "type": "directory",
                            "contents": get_tree(item_path),
                        }
                    )
                else:
                    file_info = {"name": item, "type": "file"}
                    if include_file_sizes:
                        file_info["size"] = os.path.getsize(item_path)
                        file_info["modified_time"] = os.path.getmtime(item_path)
                    tree.append(file_info)
        except PermissionError:
            tree.append({"name": "Permission Denied", "type": "error"})
        except FileNotFoundError:
            tree.append({"name": "File Not Found", "type": "error"})
        return tree

    return get_tree(root)
