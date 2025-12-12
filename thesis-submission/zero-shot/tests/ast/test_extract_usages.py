from tree_sitter import Point
from masterthesis.ast.collect_imports import collect_imports
from masterthesis.ast.extract_usages import extract_usages
from masterthesis.ast.find_dependency_usages import find_dependency_usages


# def test_extract_usages(parser, test_files, all_imports):
#     dependency_classes = ["YourDependencyClass1", "YourDependencyClass2", "ArrayList", "YourDependencyClass3", "ClassA", "ClassB", "OuterClass", "InnerClass", "ChainClass"]

#     expected_results = {
#         "test_file_1": [{"class": "YourDependencyClass1", "count": 1}],
#         "test_file_2": [{"class": "YourDependencyClass2", "count": 1}],
#         "test_file_3": [],
#         "test_file_4": [{"class": "ArrayList", "count": 1}],
#         "test_file_5": [{"class": "YourDependencyClass3", "count": 1}],
#         "test_file_6": [],
#         "test_file_7": [{"class": "ClassA", "count": 1}, {"class": "ClassB", "count": 1}],
#         "test_file_8": [{"class": "OuterClass.NestedClass", "count": 1}],
#         "test_file_9": [{"class": "InnerClass.Inner", "count": 1}],
#         "test_file_10": [{"class": "ChainClass", "count": 1}]
#     }

#     for file_name, expected in expected_results.items():
#         imported_classes = set(imp.split('.')[-1] for imp in all_imports[file_name])
#         print(imported_classes)
#         usages = extract_usages(test_files[file_name], dependency_classes, imported_classes, parser)

#         assert len(usages) == len(expected)
#         for usage, exp in zip(usages, expected):
#             assert usage['class'] == exp['class']

# def test_find_dependency_usages(parser, test_project_directory):
#     dependency_classes = ["YourDependencyClass1", "YourDependencyClass2", "ArrayList", "YourDependencyClass3", "ClassA", "ClassB", "OuterClass", "InnerClass", "ChainClass"]
#     usages = find_dependency_usages(test_project_directory, dependency_classes, parser)

#     assert len(usages) == 8
#     found_classes = {usage['class'] for usage in usages}
#     for class_name in dependency_classes:
#         assert class_name in found_classes


# ---------------------------------

# def test_extract_usages(snapshot, parser, test_files, all_imports):
#     dependency_classes = ["YourDependencyClass1", "YourDependencyClass2", "ArrayList", "YourDependencyClass3", "ClassA", "ClassB", "OuterClass", "InnerClass", "ChainClass"]

#     for file_name in test_files.keys():
#         imported_classes = set(imp.split('.')[-1] for imp in all_imports[file_name])
#         usages = extract_usages(test_files[file_name], dependency_classes, imported_classes, parser)
#         print(imported_classes, usages, file_name)
#         # snapshot.assert_match(usages, file_name+".snap")
#         assert usages == snapshot(name=file_name)

# def test_find_dependency_usages(snapshot, parser, test_project_directory):
#     dependency_classes = ["YourDependencyClass1", "YourDependencyClass2", "ArrayList", "YourDependencyClass3", "ClassA", "ClassB", "OuterClass", "InnerClass", "ChainClass"]
#     usages = find_dependency_usages(test_project_directory, dependency_classes, parser)

#     # snapshot.assert_match(usages, 'find_dependency_usages')
#     assert usages == snapshot


# def test_chained_class(snapshot, parser, test_files, all_imports):
#     dependency_classes = ["ChainClass"]
#     imported_classes = set(
#         imp.split(".")[-1] for imp in all_imports["TestChainedClass.java"]
#     )
#     usages = extract_usages(
#         test_files["TestChainedClass.java"],
#         dependency_classes,
#         imported_classes,
#         parser,
#     )
#     # assert imported_classes == snapshot
#     # assert usages == snapshot
#     expected_usages = [
#         {
#             "class": "ChainClass",
#             "start_point": Point(row=4, column=29),
#             "end_point": Point(row=4, column=39),
#             "type": "object_creation",
#         },
#         {
#             "class": "ChainClass",
#             "start_point": Point(row=5, column=8),
#             "end_point": Point(row=5, column=18),
#             "type": "method_invocation",
#         },
#         {
#             "class": "ChainClass",
#             "start_point": Point(row=6, column=8),
#             "end_point": Point(row=6, column=18),
#             "type": "method_invocation",
#         },
#         {
#             "class": "ChainClass",
#             "start_point": Point(row=7, column=8),
#             "end_point": Point(row=7, column=18),
#             "type": "method_invocation",
#         },
#         {
#             "class": "ChainClass",
#             "start_point": Point(row=9, column=8),
#             "end_point": Point(row=9, column=15),
#             "type": "method_invocation",
#         },
#     ]

#     assert usages == expected_usages
