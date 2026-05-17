"""Unit tests for agent_code_reviewer.py pure helpers.

Run with: python3 -m unittest cli.test_agent_code_reviewer -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_code_reviewer import (  # noqa: E402
    _build_line_content_index,
    annotate_diff_with_line_numbers,
)


SAMPLE_DIFF = """diff --git a/foo.txt b/foo.txt
index 1111111..2222222 100644
--- a/foo.txt
+++ b/foo.txt
@@ -10,3 +10,4 @@
 unchanged one
-removed line
+added line A
+added line B
 unchanged two
"""


class AnnotateDiffTests(unittest.TestCase):
    def test_prefixes_context_and_added_lines_with_new_file_line_numbers(self):
        annotated = annotate_diff_with_line_numbers(SAMPLE_DIFF)
        lines = annotated.splitlines()

        self.assertIn("L10  unchanged one", lines)
        self.assertIn("L11 +added line A", lines)
        self.assertIn("L12 +added line B", lines)
        self.assertIn("L13  unchanged two", lines)

    def test_leaves_deletion_lines_unprefixed(self):
        annotated = annotate_diff_with_line_numbers(SAMPLE_DIFF)
        self.assertIn("-removed line", annotated.splitlines())

    def test_leaves_headers_unchanged(self):
        annotated = annotate_diff_with_line_numbers(SAMPLE_DIFF)
        lines = annotated.splitlines()
        self.assertIn("diff --git a/foo.txt b/foo.txt", lines)
        self.assertIn("@@ -10,3 +10,4 @@", lines)
        self.assertIn("--- a/foo.txt", lines)
        self.assertIn("+++ b/foo.txt", lines)

    def test_handles_multiple_hunks_in_same_file(self):
        diff = (
            "diff --git a/x.txt b/x.txt\n"
            "--- a/x.txt\n"
            "+++ b/x.txt\n"
            "@@ -1,2 +1,2 @@\n"
            " line one\n"
            "+inserted at 2\n"
            "@@ -50,2 +51,2 @@\n"
            " line fifty\n"
            "+inserted at 52\n"
        )
        lines = annotate_diff_with_line_numbers(diff).splitlines()
        self.assertIn("L1  line one", lines)
        self.assertIn("L2 +inserted at 2", lines)
        self.assertIn("L51  line fifty", lines)
        self.assertIn("L52 +inserted at 52", lines)

    def test_handles_multiple_files(self):
        diff = (
            "diff --git a/a.txt b/a.txt\n"
            "--- a/a.txt\n"
            "+++ b/a.txt\n"
            "@@ -1,1 +1,1 @@\n"
            "+from a\n"
            "diff --git a/b.txt b/b.txt\n"
            "--- a/b.txt\n"
            "+++ b/b.txt\n"
            "@@ -1,1 +1,1 @@\n"
            "+from b\n"
        )
        lines = annotate_diff_with_line_numbers(diff).splitlines()
        self.assertIn("L1 +from a", lines)
        self.assertIn("L1 +from b", lines)

    def test_empty_diff_returns_empty_string(self):
        self.assertEqual(annotate_diff_with_line_numbers(""), "")


class LineContentIndexTests(unittest.TestCase):
    def test_indexes_added_and_context_lines_by_content(self):
        index = _build_line_content_index(SAMPLE_DIFF)
        self.assertEqual(index["foo.txt"]["unchanged one"], [10])
        self.assertEqual(index["foo.txt"]["added line A"], [11])
        self.assertEqual(index["foo.txt"]["added line B"], [12])
        self.assertEqual(index["foo.txt"]["unchanged two"], [13])

    def test_does_not_index_deleted_lines(self):
        index = _build_line_content_index(SAMPLE_DIFF)
        self.assertNotIn("removed line", index["foo.txt"])

    def test_records_all_matches_when_excerpt_appears_twice(self):
        diff = (
            "diff --git a/foo.txt b/foo.txt\n"
            "--- a/foo.txt\n"
            "+++ b/foo.txt\n"
            "@@ -1,4 +1,4 @@\n"
            "+duplicate\n"
            " other\n"
            "+duplicate\n"
            " end\n"
        )
        index = _build_line_content_index(diff)
        self.assertEqual(index["foo.txt"]["duplicate"], [1, 3])


if __name__ == "__main__":
    unittest.main()
