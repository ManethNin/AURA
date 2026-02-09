# This code is originally from https://github.com/paul-gauthier/aider/blob/main/aider/coders/udiff_coder.py
# Authored by Paul Gauthier
# Available under the Apache License
# Version 2.0, January 2004
# http://www.apache.org/licenses/

# https://github.com/paul-gauthier/aider/blob/main/LICENSE.txt


import difflib
import json
import logging
from enum import Enum
from itertools import groupby
from pathlib import Path
from typing import Dict, List, Set, Tuple, Union

import pathvalidate
from opentelemetry import trace as trace_api

# Our Modification
from app.common_agents.agent.aider.search_replace import (
    SearchTextNotUnique,
    all_preprocs,
    diff_lines,
    flexible_search_and_replace,
    search_and_replace,
)

tracer = trace_api.get_tracer(__name__)

no_match_error = """UnifiedDiffNoMatch: hunk failed to apply!

{path} does not contain lines that match the diff you provided!
Try again.
DO NOT, NEVER, skip blank lines, comments, docstrings, etc!
The diff needs to apply cleanly to the lines in {path}!
Make extra sure the indentation is correct.

{path} does not contain these {num_lines} exact lines in a row:
```
{original}```
"""


not_unique_error = """UnifiedDiffNotUnique: hunk failed to apply!

{path} contains multiple sets of lines that match the diff you provided!
Try again.
Use additional ` ` lines to provide context that uniquely indicates which code needs to be changed.
The diff needs to apply to a unique set of lines in {path}!

{path} contains multiple copies of these {num_lines} lines:
```
{original}```
"""

no_edits_error = """UnifiedDiffNoEdits: no applicable hunks found!

The provided diff does not contain any hunks that can be applied to the files in the repository.
Ensure that your diff correctly specifies the changes and try again.
The diff needs to apply to the existing lines in the files.
"""

other_hunks_applied = "Note: some hunks did apply successfully. See the updated source code shown above.\n\n"


def tracer_assert(span, condition, message):
    if not condition:
        span.set_attribute("assertion", message)
    assert condition, message


def tracer_strategy_result(span, strategy_results):
    span.set_attributes("strategy_results", json.dumps(strategy_results))


class DiffError(Enum):
    NO_PATH = "NoPathInDiff"
    NO_MATCH = "UnifiedDiffNoMatch"
    NOT_UNIQUE = "UnifiedDiffNotUnique"
    NO_EDITS = "UnifiedDiffNoEdits"


# Our Modification
class UnifiedDiffCoder:
    edit_format = "udiff"

    # Our Modification
    def __init__(self, repo_dir, *args, **kwargs):
        # Convert to Path and resolve to handle symlinks (e.g., /var -> /private/var on macOS)
        self.repo_dir = Path(repo_dir).resolve()

    # Our Modification
    def abs_root_path(self, path):
        res = self.repo_dir / path
        reso = res.resolve()
        return str(reso)

    def get_edits(self, partial_response_content) -> list[tuple[str, list[str]]]:
        content = partial_response_content

        # might raise ValueError for malformed ORIG/UPD blocks
        raw_edits = list(find_diffs(content))
        # print("raw_edits", raw_edits)

        last_path = None
        edits = []
        for path, hunk in raw_edits:
            if path:
                test_path = path.replace("diff --git", "").strip().split(" ")
                if (
                    path.startswith("diff --git")
                    and len(path.replace("diff --git", "").strip().split(" ")) >= 2
                    and test_path[0].startswith("a/")
                    and test_path[1].startswith("b/")
                ):
                    path = test_path[1][2:]
                    # print("fixed path", path)

                # Clean the path early: strip whitespace and leading slashes
                path = path.strip().lstrip("/")
                # Also strip a/ or b/ prefix if present
                if path.startswith("a/") or path.startswith("b/"):
                    path = path[2:].lstrip("/")
                
                last_path = path
            else:
                path = last_path
            edits.append((path, hunk))
        return edits

    def get_paths(self, partial_response_content) -> list[str]:
        raw_edits = self.get_edits(partial_response_content)
        paths = set()
        for path, _ in raw_edits:
            path = path.strip()
            if path.startswith("a/") or path.startswith("b/"):
                path = path[2:]
            if " " not in path:
                paths.add(path)
        return list(paths)

    def apply_edits(
        self, partial_response_content
    ) -> tuple[bool, Union[Exception, dict[str, str]]]:
        with tracer.start_as_current_span("UnifiedDiffCoder.apply_edits") as span:
            seen: Set[str] = set()
            uniq: List[Tuple[str, List[str]]] = []
            # Our Modification
            # print("Partial response content", partial_response_content)
            try:
                for path, hunk in self.get_edits(partial_response_content):
                    hunk = normalize_hunk(hunk)
                    if not hunk:
                        continue

                    tracer_assert(
                        span,
                        path,
                        "Path is required for applying edits. Are you sure you included the Path properly?",
                    )

                    this = [path + "\n"] + hunk
                    this = "".join(this)

                    if this in seen:
                        continue
                    seen.add(this)

                    uniq.append((path, hunk))
            except AssertionError as e:
                return False, e

            errors: List[str] = []

            # assert len({u[0] for u in uniq}) < 2, "Multiple paths in a single diff not supported"

            output_buffer: Dict[str, str] = {}

            def read_file(path: str) -> str:
                if path in output_buffer:
                    return output_buffer[path]
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                output_buffer[path] = content
                return content

            def write_file(path: str, content: str) -> None:
                output_buffer[path] = content

            if len(uniq) == 0:
                errors.append(no_edits_error)
            for path, hunk in uniq:
                # Strip a/ or b/ prefix from git-style diffs
                if path.startswith("a/") or path.startswith("b/"):
                    path = path[2:]
                
                # Strip any leading/trailing whitespace and slashes
                path = path.strip().lstrip("/")

                # print("path", path)

                full_path = self.abs_root_path(path)
                # Our Modification
                content = read_file(full_path)

                original, _ = hunk_to_before_after(hunk)

                # print("hi hunk", hunk)

                try:
                    content = do_replace(full_path, content, hunk)
                except SearchTextNotUnique:
                    errors.append(
                        not_unique_error.format(
                            path=path,
                            original=original,
                            num_lines=len(original.splitlines()),
                        )
                    )
                    continue

                if not content:
                    errors.append(
                        no_match_error.format(
                            path=path,
                            original=original,
                            num_lines=len(original.splitlines()),
                        )
                    )
                    continue

                # SUCCESS!
                # Our Modification
                logging.debug("Writing to %s", full_path)
                write_file(full_path, content)

            if errors:
                errors = "\n\n".join(errors)
                if len(errors) < len(uniq):
                    errors += other_hunks_applied
                # Our Modification
                return False, ValueError(errors)

            # tracer_assert(
            #     span,
            #     len(output_buffer) == 1,
            #     "Multiple paths in a single diff not supported",
            # )

            # Strip repo_dir prefix from paths to return relative paths
            repo_dir_prefix = str(self.repo_dir) + "/"
            output_buffer = {
                k.replace(repo_dir_prefix, "") if k.startswith(repo_dir_prefix) else k: v
                for k, v in output_buffer.items()
            }

            return True, output_buffer


def do_replace(fname, content, hunk):
    logging.debug("Starting do_replace")
    fname = Path(fname)

    before_text, after_text = hunk_to_before_after(hunk)

    # does it want to make a new file?
    if not fname.exists() and not before_text.strip():
        fname.touch()
        content = ""

    if content is None:
        return

    # TODO: handle inserting into new file
    if not before_text.strip():
        # append to existing file, or start a new file
        new_content = content + after_text
        return new_content

    new_content = None
    new_content = apply_hunk(content, hunk)
    if new_content:
        return new_content


def collapse_repeats(s):
    return "".join(k for k, g in groupby(s))


def apply_hunk(content, hunk):
    before_text, after_text = hunk_to_before_after(hunk)

    res = directly_apply_hunk(content, hunk)
    if res:
        logging.debug("directly_apply_hunk worked")
        return res

    hunk = make_new_lines_explicit(content, hunk)

    # just consider space vs not-space
    ops = "".join([line[0] for line in hunk])
    ops = ops.replace("-", "x")
    ops = ops.replace("+", "x")
    ops = ops.replace("\n", " ")

    cur_op = " "
    section = []
    sections = []

    for i in range(len(ops)):
        op = ops[i]
        if op != cur_op:
            # print("Appending section", section)
            sections.append(section)
            section = []
            cur_op = op
        # print("Appending hunk", hunk[i])
        section.append(hunk[i])

    sections.append(section)
    if cur_op != " ":
        sections.append([])

    all_done = True

    # print("Sections", sections)
    for i in range(2, len(sections), 2):
        preceding_context = sections[i - 2]
        changes = sections[i - 1]
        following_context = sections[i]

        # print("preceding_context", preceding_context)
        # print("changes", changes)
        # print("following_context", following_context)

        res = apply_partial_hunk(content, preceding_context, changes, following_context)
        if res:
            content = res
        else:
            all_done = False
            # FAILED!
            # this_hunk = preceding_context + changes + following_context
            break

    if all_done:
        return content


def flexi_just_search_and_replace(texts):
    strategies = [
        (search_and_replace, all_preprocs),
    ]
    return flexible_search_and_replace(texts, strategies)


def make_new_lines_explicit(content, hunk):
    before, after = hunk_to_before_after(hunk)

    diff = diff_lines(before, content)

    back_diff = []
    for line in diff:
        if line[0] == "+":
            continue
        # if line[0] == "-":
        #    line = "+" + line[1:]

        back_diff.append(line)

    new_before = directly_apply_hunk(before, back_diff)
    if not new_before:
        return hunk

    if len(new_before.strip()) < 10:
        return hunk

    before = before.splitlines(keepends=True)
    new_before = new_before.splitlines(keepends=True)
    after = after.splitlines(keepends=True)

    if len(new_before) < len(before) * 0.66:
        return hunk

    new_hunk = difflib.unified_diff(
        new_before, after, n=max(len(new_before), len(after))
    )
    new_hunk = list(new_hunk)[3:]

    return new_hunk


def cleanup_pure_whitespace_lines(lines):
    res = [
        line if line.strip() else line[-(len(line) - len(line.rstrip("\r\n")))]
        for line in lines
    ]
    return res


def normalize_hunk(hunk):
    before, after = hunk_to_before_after(hunk, lines=True)

    before = cleanup_pure_whitespace_lines(before)
    after = cleanup_pure_whitespace_lines(after)

    diff = difflib.unified_diff(before, after, n=max(len(before), len(after)))
    diff = list(diff)[3:]
    return diff


def directly_apply_hunk(content, hunk):
    logging.debug("Starting directly_apply_hunk")
    # print(f"Hunk: {hunk}")

    before, after = hunk_to_before_after(hunk)

    if not before:
        logging.debug("No 'before' content, returning None")
        return

    before_lines, _ = hunk_to_before_after(hunk, lines=True)
    before_lines = "".join([line.strip() for line in before_lines])
    # print(f"Before lines (stripped): {before_lines}")

    # Refuse to do a repeated search and replace on a tiny bit of non-whitespace context
    if len(before_lines) < 10 and content.count(before) > 1:
        logging.debug(
            "Refusing repeated search and replace on a tiny bit of non-whitespace context"
        )
        return

    try:
        # print("Trying search and replace, direct_apply_hunk", before, after)
        new_content = flexi_just_search_and_replace([before, after, content])
        # print(f"New content after search and replace: {new_content}")
    except SearchTextNotUnique:
        logging.debug("SearchTextNotUnique exception caught")
        new_content = None

    return new_content


def apply_partial_hunk(
    content,
    preceding_context,
    changes,
    following_context,
    output_strategy_results=False,
):
    with tracer.start_as_current_span("apply_partial_hunk") as span:
        len_prec = len(preceding_context)
        len_foll = len(following_context)

        use_all = len_prec + len_foll

        strategy_results = []

        # if there is a - in the hunk, we can go all the way to `use=0`
        for drop in range(use_all + 1):
            use = use_all - drop

            for use_prec in range(len_prec, -1, -1):
                if use_prec > use:
                    continue

                use_foll = use - use_prec
                if use_foll > len_foll:
                    continue

                if use_prec:
                    this_prec = preceding_context[-use_prec:]
                else:
                    this_prec = []

                this_foll = following_context[:use_foll]

                res = directly_apply_hunk(content, this_prec + changes + this_foll)
                if res is None:
                    strategy_results.append(
                        {
                            "strategy": "direct_apply_hunk",
                            "details": {
                                "use_prec": use_prec,
                                "use_foll": use_foll,
                            },
                            "result": res,
                            "success": res is not None,
                        }
                    )
                if res:
                    span.set_attribute("strategy_results", json.dumps(strategy_results))
                    if output_strategy_results:
                        return res, strategy_results
                    return res

        logging.debug("Trying last-ditch effort: Levenshtein distance check")
        content_lines = content.splitlines()
        matched_prec_index = find_approximate_match(content_lines, preceding_context)
        if len(following_context) > 0:
            matched_foll_index = find_approximate_match(
                content_lines, following_context
            )

        if matched_prec_index is not None and (
            len(following_context) == 0
            or matched_foll_index is not None
            and matched_prec_index < matched_foll_index
        ):
            start_index = sum(
                len(line) + 1
                for line in content_lines[: matched_prec_index + len(preceding_context)]
            )
            if len(following_context) == 0:
                end_index = start_index
                start_index = sum(
                    len(line) + 1 for line in content_lines[:matched_prec_index]
                )
            else:
                end_index = sum(
                    len(line) + 1 for line in content_lines[:matched_foll_index]
                )

            original_before = content[:start_index]
            original_after = content[end_index:]

            new_content = original_before + "".join(changes) + original_after
            strategy_results.append(
                {"strategy": "levenshtein", "result": new_content, "success": True}
            )
            if new_content:
                span.set_attribute("strategy_results", json.dumps(strategy_results))
                if output_strategy_results:
                    return new_content, strategy_results
                return new_content
        else:
            strategy_results.append(
                {"strategy": "levenshtein", "result": None, "success": False}
            )

        # # Last-ditch attempt: remove all whitespace and match based on that
        # # print("Trying last-ditch attempt: remove all whitespace and match based on that")
        # stripped_content = "".join(content.split())
        # stripped_prec = "".join("".join(preceding_context).split())
        # stripped_foll = "".join("".join(following_context).split())

        # print(f"Stripped content: {stripped_content}")
        # print(f"Stripped preceding context: {stripped_prec}")
        # print(f"Stripped following context: {stripped_foll}")

        # if (
        #     stripped_prec in stripped_content and stripped_foll in stripped_content
        # ) or stripped_prec in stripped_content:
        #     start_index = stripped_content.find(stripped_prec)
        #     if stripped_foll in stripped_content:
        #         end_index = stripped_content.find(
        #             stripped_foll, start_index + len(stripped_prec)
        #         )
        #     else:
        #         end_index = start_index + len(stripped_prec)

        #     print(
        #         "Stripped_prec is in stripped_content and stripped_foll is in stripped_content"
        #     )
        #     print(f"Start index: {start_index}")
        #     print(f"End index: {end_index}")

        #     if start_index != -1 and end_index != -1:
        #         start_index = len("".join(stripped_content[:start_index].split()))
        #         end_index = len("".join(stripped_content[:end_index].split()))

        #         original_before = content[: start_index + len(preceding_context)]
        #         original_after = content[end_index:]

        #         new_content = original_before + "".join(changes) + original_after
        #         # print(f"New content after applying normal hunk: {new_content}")
        #         # print("Whitespace saved the day!")
        #         if output_strategy_results:
        #             strategy_results.append(
        #                 {"strategy": "whitespace", "result": new_content, "success": True}
        #             )
        #             return new_content, strategy_results
        #         return new_content
        # else:
        #     if output_strategy_results:
        #         strategy_results.append(
        #             {"strategy": "whitespace", "result": None, "success": False}
        #         )
        #         return None, strategy_results
        #     return None

        span.set_attribute("strategy_results", json.dumps(strategy_results))
        if output_strategy_results:
            return None, strategy_results
        return None


def find_approximate_match(content_lines, context_lines):
    with tracer.start_as_current_span("find_approximate_match") as span:
        if not context_lines:
            logging.debug("No context lines provided, no levensthein match possible")
            return None

        best_match_index = None
        best_match_ratio = 0.0

        for i in range(len(content_lines) - len(context_lines) + 1):
            current_slice = content_lines[i : i + len(context_lines)]
            current_ratio = difflib.SequenceMatcher(
                None, "".join(current_slice), "".join(context_lines)
            ).ratio()

            if current_ratio > best_match_ratio:
                best_match_ratio = current_ratio
                best_match_index = i

        logging.debug(f"Best match ratio: {best_match_ratio}")
        span.set_attribute("best_match_ratio", best_match_ratio)
        # Consider a match sufficient if the similarity ratio is greater than 0.8 (tweak as necessary)
        if best_match_ratio > 0.8:
            logging.debug(
                f"Found approximate match with ratio {best_match_ratio} at index {best_match_index}"
            )
            span.set_attribute("best_match_index", best_match_index)
            return best_match_index

        logging.debug("No sufficient approximate match found")
        return None


def find_diffs(content):
    # We can always fence with triple-quotes, because all the udiff content
    # is prefixed with +/-/space.

    with tracer.start_as_current_span("find_diffs") as span:

        if not content.endswith("\n"):

            span.set_attribute("correction_applied", "trailing_newline_added")
            content = content + "\n"

        lines = content.splitlines(keepends=True)
        line_num = 0
        edits = []

        tracer_assert(
            span,
            (content.count("```diff") > 0),
            "No diff fences found in content. Make sure that the diff is fenced with ```diff on its own line. and is closed with ```",
        )

        while line_num < len(lines):
            while line_num < len(lines):
                line = lines[line_num]
                if line.startswith("```diff"):
                    line_num, these_edits = process_fenced_block(lines, line_num + 1)
                    edits += these_edits
                    break
                line_num += 1

        # For now, just take 1!
        # edits = edits[:1]

        return edits


def process_fenced_block(lines: list[str], start_line_num):
    with tracer.start_as_current_span("process_fenced_block") as span:
        corrections = []
        line_num = None
        for line_num in range(start_line_num, len(lines)):
            line = lines[line_num]
            if line.startswith("```"):
                break

        # fix the issue where the LLM forgets to insert a closing fence
        if line_num is None or line_num == len(lines):
            corrections.append("closing_fence_missing")
            line_num = len(lines)
            lines.append("```")

        tracer_assert(
            span, line_num < len(lines), "No closing fence found for diff block"
        )

        block = lines[start_line_num:line_num]
        block.append("@@ @@")

        def check_fix_a_b(block_0, block1):
            if block_0.strip().startswith("a/") and block1.strip().startswith("b/"):
                block_0 = block_0[2:]
                block1 = block1[2:]
                corrections.append("git_diff_style")
            return block_0, block1

        fname = None
        if len(block) >= 2:
            if block[0].strip().startswith("--- ") and block[1].strip().startswith(
                "+++ "
            ):
                block[0] = block[0][4:]
                block[1] = block[1][4:]
                block[0], block[1] = check_fix_a_b(block[0], block[1])
                fname = block[1].strip()
                block = block[2:]
            # The model just added the --- not the +++ part
            elif block[0].strip().startswith("--- ") and not block[
                1
            ].strip().startswith("+++"):
                if block[0].strip().startswith("a/"):
                    block[0] = block[0][2:]
                    corrections.append("git_diff_style")
                fname = block[0][4:].strip()
                block = block[1:]
                corrections.append("filename_only_in_minus_not_plus")
            # The model took a part of the prompt
            elif block[0].strip().startswith("Path: "):
                fname = block[0].replace("Path: ", "").strip()
                block = block[1:]
                corrections.append("filename_in_path")
            # The model just put the path in there...
            elif pathvalidate.is_valid_filepath(block[0].strip()) and not block[
                0
            ].strip().startswith("@@"):
                fname = block[0].strip()
                block = block[1:]
                corrections.append("filename_without_indicator")

        edits = []

        # for line in block, if it starts with @@ - , we have a malformed hunk
        # replace @@ to @@ .. @@ and split on @@ to get the hunk
        for line_idx, line in enumerate(block):
            if line.startswith("@@") and line.count("@@") <= 1:

                corrections.append("correct_amount_of_at_symbols")
                logging.debug("Fixing malformed hunk")
                line = line.replace("@@ ", "")
                block[line_idx] = line
                # now insert a line before this one with @@ .. @@
                block.insert(line_idx, "@@ @@")
                break

        span.set_attribute("correction_applied", corrections)

        keeper = False
        hunk = []
        op = " "
        for line in block:
            hunk.append(line)
            if len(line) < 2:
                continue

            if (
                line.startswith("+++ ")
                and len(hunk) >= 2
                and hunk[-2].startswith("--- ")
            ):
                if len(hunk) >= 3 and hunk[-3] == "\n":
                    hunk = hunk[:-3]
                else:
                    hunk = hunk[:-2]

                edits.append((fname, hunk))
                hunk = []
                keeper = False

                fname = line[4:].strip()
                continue

            op = line[0]
            if line[:2].startswith(" -") or line[:2].startswith(" +"):
                op = line[0][1:]
                hunk[-1] = f"{hunk[-1][1:2]} {hunk[-1][2:]}"
            if op in "-+":
                keeper = True
                continue
            if op != "@":
                continue
            if not keeper:
                hunk = []
                continue

            hunk = hunk[:-1]
            edits.append((fname, hunk))
            hunk = []
            keeper = False

        return line_num + 1, edits


def hunk_to_before_after(hunk, lines=False):
    before = []
    after = []
    op = " "
    for line in hunk:
        if len(line) < 2:
            op = " "
            line = line
        else:
            op = line[0]
            line = line[1:]

        if op == " ":
            before.append(line)
            after.append(line)
        elif op == "-":
            before.append(line)
        elif op == "+":
            after.append(line)

    if lines:
        return before, after

    before = "".join(before)
    after = "".join(after)

    return before, after
