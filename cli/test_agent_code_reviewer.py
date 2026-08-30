"""Unit tests for agent_code_reviewer.py pure helpers.

Run with: python3 -m unittest cli.test_agent_code_reviewer -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_code_reviewer import (  # noqa: E402
    ConfigError,
    _build_line_content_index,
    annotate_diff_with_line_numbers,
    load_config,
    make_adapter,
    parse_config,
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


# ---------------------------------------------------------------------------
# Roster config parsing
# ---------------------------------------------------------------------------


def _raw(models=None, default="a"):
    """Minimal valid raw-toml dict, overridable per test."""
    if models is None:
        models = [
            {"key": "a", "name": "A", "access_method": "gemini_api", "id": "m-a"}
        ]
    return {"default": default, "models": models}


class ParseConfigTests(unittest.TestCase):
    def test_parses_entries_and_default(self):
        roster = parse_config(_raw())
        self.assertEqual(roster.default_key, "a")
        self.assertEqual([e.key for e in roster.entries], ["a"])
        self.assertEqual(roster.entries[0].id, "m-a")
        self.assertEqual(roster.entries[0].access_method, "gemini_api")

    def test_tag_defaults_to_key_uppercased(self):
        roster = parse_config(_raw())
        self.assertEqual(roster.entries[0].tag, "A")

    def test_explicit_tag_wins(self):
        models = [
            {
                "key": "gemini-pro",
                "name": "A",
                "access_method": "gemini_api",
                "id": "m",
                "tag": "GEMINI",
            }
        ]
        roster = parse_config(_raw(models, default="gemini-pro"))
        self.assertEqual(roster.entries[0].tag, "GEMINI")

    def test_store_defaults_false(self):
        self.assertFalse(parse_config(_raw()).entries[0].store)

    def test_store_allowed_on_openai_api(self):
        models = [
            {
                "key": "codex",
                "name": "C",
                "access_method": "openai_api",
                "id": "gpt",
                "store": True,
            }
        ]
        roster = parse_config(_raw(models, default="codex"))
        self.assertTrue(roster.entries[0].store)

    def test_store_rejected_on_other_access_methods(self):
        models = [
            {
                "key": "grok",
                "name": "G",
                "access_method": "openrouter",
                "id": "x-ai/grok-4.6",
                "store": True,
            }
        ]
        with self.assertRaises(ConfigError) as ctx:
            parse_config(_raw(models, default="grok"))
        self.assertIn("store", str(ctx.exception))

    def test_rejects_default_not_matching_any_key(self):
        with self.assertRaises(ConfigError) as ctx:
            parse_config(_raw(default="nope"))
        self.assertIn("nope", str(ctx.exception))

    def test_rejects_missing_default(self):
        raw = _raw()
        del raw["default"]
        with self.assertRaises(ConfigError):
            parse_config(raw)

    def test_rejects_empty_roster(self):
        with self.assertRaises(ConfigError):
            parse_config(_raw(models=[]))

    def test_rejects_duplicate_keys(self):
        models = [
            {"key": "a", "name": "A", "access_method": "gemini_api", "id": "1"},
            {"key": "a", "name": "B", "access_method": "openai_api", "id": "2"},
        ]
        with self.assertRaises(ConfigError) as ctx:
            parse_config(_raw(models))
        self.assertIn("a", str(ctx.exception))

    def test_rejects_unknown_access_method(self):
        models = [{"key": "a", "name": "A", "access_method": "carrier_pigeon", "id": "1"}]
        with self.assertRaises(ConfigError) as ctx:
            parse_config(_raw(models))
        self.assertIn("carrier_pigeon", str(ctx.exception))

    def test_rejects_unknown_field(self):
        """A typo'd optional field (`tags`) must fail loudly, not default silently."""
        models = [
            {
                "key": "a",
                "name": "A",
                "access_method": "gemini_api",
                "id": "1",
                "tags": "GEMINI",
            }
        ]
        with self.assertRaises(ConfigError) as ctx:
            parse_config(_raw(models))
        self.assertIn("tags", str(ctx.exception))

    def test_rejects_missing_required_field(self):
        for field in ("key", "name", "access_method", "id"):
            with self.subTest(field=field):
                model = {
                    "key": "a",
                    "name": "A",
                    "access_method": "gemini_api",
                    "id": "1",
                }
                del model[field]
                with self.assertRaises(ConfigError):
                    parse_config(_raw([model], default="a"))


class RosterLookupTests(unittest.TestCase):
    def setUp(self):
        models = [
            {"key": "a", "name": "A", "access_method": "gemini_api", "id": "1"},
            {"key": "b", "name": "B", "access_method": "openai_api", "id": "2"},
        ]
        self.roster = parse_config(_raw(models))

    def test_get_returns_entry_by_key(self):
        self.assertEqual(self.roster.get("b").id, "2")

    def test_get_unknown_key_lists_valid_keys(self):
        with self.assertRaises(ConfigError) as ctx:
            self.roster.get("zzz")
        msg = str(ctx.exception)
        self.assertIn("zzz", msg)
        self.assertIn("a", msg)
        self.assertIn("b", msg)

    def test_default_entry_resolves(self):
        self.assertEqual(self.roster.default_entry().key, "a")


class ShippedRosterTests(unittest.TestCase):
    """The committed roster must always be valid — it is what a fork inherits."""

    def test_shipped_roster_parses(self):
        roster = load_config(Path(__file__).resolve().parent / "agent_reviewer.toml")
        self.assertTrue(roster.entries)
        self.assertEqual(roster.default_entry().key, roster.default_key)

    def test_every_access_method_is_exercised_by_an_adapter(self):
        roster = load_config(Path(__file__).resolve().parent / "agent_reviewer.toml")
        for entry in roster.entries:
            with self.subTest(key=entry.key):
                self.assertIsNotNone(make_adapter(entry))
