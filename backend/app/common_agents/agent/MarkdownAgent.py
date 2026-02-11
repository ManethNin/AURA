from mistletoe import Document
from mistletoe.utils import traverse


class MarkdownAgent:
    def extract_codeblock(self, markdown):
        d = Document(markdown.split("\n"))

        def render_diff_code(token) -> str:
            if token.language == "diff" or not token.language:
                return token.content

        diffs = [
            render_diff_code(t.node)
            for t in traverse(d, include_source=True)
            if t.node.__class__.__name__ in ["CodeFence"]
        ]
        filtered_diffs = [diff for diff in diffs if diff is not None]

        assert len(filtered_diffs) < 2, "Only one diff is allowed in a markdown file"
        assert len(filtered_diffs) > 0, "No diff found in the markdown file"

        return filtered_diffs[0]
