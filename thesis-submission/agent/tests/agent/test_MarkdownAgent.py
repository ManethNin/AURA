import pytest

from masterthesis.agent.MarkdownAgent import MarkdownAgent


def test_extract_codeblock(snapshot):
    agent = MarkdownAgent()
    markdown = """# Title

Some text

```diff
print("Hello, world!")
print("Whatsupppp")
```

More text
  """

    codeblock = agent.extract_codeblock(markdown)

    assert codeblock == snapshot


def test_extract_py_codeblock():
    agent = MarkdownAgent()
    markdown = """# Title

Some text

```python
print("Hello, world!")
print("Whatsupppp")
```

More text
  """
    with pytest.raises(AssertionError):
        agent.extract_codeblock(markdown)


def test_prediction(snapshot):
    agent = MarkdownAgent()
    markdown = "```diff\n3c3\n<     obj.getInner1().doSomething();\n---\n>     obj.getInner3().doSomething();\n```"
    codeblock = agent.extract_codeblock(markdown)
    assert codeblock == snapshot
