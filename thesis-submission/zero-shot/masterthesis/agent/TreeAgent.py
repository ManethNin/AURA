import os


def get_directory_tree(root):
    tree = {}
    for item in os.listdir(root):
        path = os.path.join(root, item)
        if os.path.isdir(path):
            tree[item] = get_directory_tree(path)
        else:
            tree[item] = None
    return tree
