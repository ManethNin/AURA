from masterthesis.ast.collect_imports import collect_imports


def test_collect_imports(all_imports):
    for imports in all_imports.values():
        # assert len(imports) > 0
        assert isinstance(imports, list)
        assert all(isinstance(imp, str) for imp in imports)

    assert "test.de.ChainClass" in all_imports["TestChainedClass.java"]
    assert "YourDependencyClass1" in all_imports["TestDirectImport.java"]
    assert "test.de.SuperString" in all_imports["TestGenerics.java"]
    assert "test.de.InnerClass" in all_imports["TestInnerClass.java"]
    assert "test.de.OuterClass" in all_imports["TestNestedClass.java"]
    assert "test.*" in all_imports["TestWildCardImport.java"]
