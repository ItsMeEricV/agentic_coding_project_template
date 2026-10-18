"""Unit tests for agent_code_reviewer.py pure helpers.

Run with: python3 -m unittest cli.test_agent_code_reviewer -v
"""

from __future__ import annotations

import sys
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_code_reviewer import (  # noqa: E402
    DEFAULT_CONTEXT_WINDOW,
    REPLY_RESERVE_TOKENS,
    DEFAULT_IGNORE_PATHS,
    ConfigError,
    FocusArea,
    _build_line_content_index,
    _path_matches_any,
    annotate_diff_with_line_numbers,
    build_pr_prompt,
    check_versions,
    churn_by_file,
    diff_char_budget,
    entries_that_fit,
    filter_catalog,
    filter_diff,
    focus_file_path,
    prune_focus_paths,
    format_catalog,
    format_focus_section,
    format_version_report,
    is_prerelease,
    is_transient,
    load_config,
    make_adapter,
    model_family,
    parse_config,
    parse_focus_areas,
    parse_openrouter_catalog,
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


class ContextWindowTests(unittest.TestCase):
    def test_defaults_when_omitted(self):
        self.assertEqual(parse_config(_raw()).entries[0].context_window, DEFAULT_CONTEXT_WINDOW)

    def test_explicit_value_wins(self):
        models = [
            {
                "key": "a",
                "name": "A",
                "access_method": "gemini_api",
                "id": "m",
                "context_window": 1_050_000,
            }
        ]
        self.assertEqual(parse_config(_raw(models)).entries[0].context_window, 1_050_000)

    def test_rejects_non_positive_or_non_int(self):
        for bad in (0, -1, "1M", 1.5, True):
            models = [
                {
                    "key": "a",
                    "name": "A",
                    "access_method": "gemini_api",
                    "id": "m",
                    "context_window": bad,
                }
            ]
            with self.subTest(bad=bad), self.assertRaises(ConfigError):
                parse_config(_raw(models))

    def test_shipped_roster_declares_every_window(self):
        """A missing window silently falls back to the conservative default — keep the
        committed roster explicit so --list shows what each model can really take."""
        toml = (Path(__file__).resolve().parent / "agent_reviewer.toml").read_text()
        roster = load_config(Path(__file__).resolve().parent / "agent_reviewer.toml")
        self.assertEqual(toml.count("context_window"), len(roster.entries) + 1)  # + header doc


class DiffBudgetTests(unittest.TestCase):
    def test_budget_is_window_minus_reply_reserve_in_chars_minus_overhead(self):
        budget = diff_char_budget(context_window=100_000, overhead_chars=1_000)
        self.assertEqual(budget, (100_000 - REPLY_RESERVE_TOKENS) * 4 - 1_000)

    def test_budget_never_negative(self):
        self.assertEqual(diff_char_budget(context_window=1_000, overhead_chars=10), 0)

    def test_old_hardcoded_cap_is_far_below_a_million_token_window(self):
        """Regression guard for the 100 KB cap that forced layer-wise slicing."""
        self.assertGreater(diff_char_budget(1_050_000, 0), 759_000 * 4)

    def test_entries_that_fit_lists_only_wide_enough_windows_in_roster_order(self):
        def entry(key, window):
            return {
                "key": key,
                "name": key,
                "access_method": "gemini_api",
                "id": key,
                "context_window": window,
            }

        models = [entry("small", 200_000), entry("big", 1_050_000), entry("mid", 500_000)]
        roster = parse_config(_raw(models, default="small"))
        needed_chars = 759_000 * 4  # a ~760K-token diff; only the 1M window takes it
        fits = entries_that_fit(roster, needed_chars=needed_chars, overhead_chars=5_000)
        self.assertEqual([e.key for e in fits], ["big"])


TWO_FILE_DIFF = """diff --git a/core/router.ts b/core/router.ts
--- a/core/router.ts
+++ b/core/router.ts
@@ -1,2 +1,3 @@
 keep
-old
+new one
+new two
diff --git a/docs/x.md b/docs/x.md
--- a/docs/x.md
+++ b/docs/x.md
@@ -1,1 +1,1 @@
-a
+b
"""


class IgnorePathTests(unittest.TestCase):
    def test_bracketed_route_path_matches_literally(self):
        path = "app/api/auth/[...nextauth]/route.ts"
        self.assertTrue(_path_matches_any(path, [path]))

    def test_directory_prefix_and_glob_still_match(self):
        self.assertTrue(_path_matches_any("docs/a/b.md", ["docs/"]))
        self.assertTrue(_path_matches_any("x/y.snap", ["*.snap"]))
        self.assertFalse(_path_matches_any("src/y.ts", ["docs/", "*.snap"]))

    def test_default_ignores_drop_lockfiles_at_any_depth(self):
        diff = (
            "diff --git a/pnpm-lock.yaml b/pnpm-lock.yaml\n+x\n"
            "diff --git a/src/a.ts b/src/a.ts\n+y\n"
        )
        kept, dropped = filter_diff(diff, list(DEFAULT_IGNORE_PATHS))
        self.assertEqual(dropped, ["pnpm-lock.yaml"])
        self.assertIn("src/a.ts", kept)


class OnlyPathTests(unittest.TestCase):
    DIFF = (
        "diff --git a/core/session/a.ts b/core/session/a.ts\n+a\n"
        "diff --git a/apps/api/b.ts b/apps/api/b.ts\n+b\n"
        "diff --git a/core/session/a.test.ts b/core/session/a.test.ts\n+t\n"
    )

    def test_only_keeps_matching_blocks(self):
        kept, dropped = filter_diff(self.DIFF, [], ["core/session/"])
        self.assertIn("core/session/a.ts", kept)
        self.assertNotIn("apps/api/b.ts", kept)
        self.assertEqual(dropped, ["apps/api/b.ts"])

    def test_ignore_still_applies_inside_only(self):
        kept, dropped = filter_diff(self.DIFF, ["*.test.ts"], ["core/session/"])
        self.assertNotIn("a.test.ts", kept)
        self.assertEqual(sorted(dropped), ["apps/api/b.ts", "core/session/a.test.ts"])

    def test_no_patterns_is_identity(self):
        self.assertEqual(filter_diff(self.DIFF, [], []), (self.DIFF, []))


class FocusFileTests(unittest.TestCase):
    def test_path_is_scoped_by_repo(self):
        self.assertEqual(
            focus_file_path("68", "acme_werkshop"), Path("/tmp/agent_reviewer_acme_werkshop_pr68_focus.json")
        )
        self.assertEqual(focus_file_path("68", ""), Path("/tmp/agent_reviewer_pr68_focus.json"))

    def test_prune_drops_paths_absent_from_diff_and_disk(self):
        area = FocusArea("t", "inv", ["infra/main.tf", "src/real.ts", "cli/agent_code_reviewer.py"], "why")
        (pruned,) = prune_focus_paths([area], {"src/real.ts"})
        self.assertEqual(pruned.paths, ["src/real.ts", "cli/agent_code_reviewer.py"])
        self.assertEqual((pruned.title, pruned.invariant, pruned.why), ("t", "inv", "why"))


class _StatusError(Exception):
    def __init__(self, status_code: int):
        super().__init__(f"status {status_code}")
        self.status_code = status_code


class RetryTests(unittest.TestCase):
    def _adapter(self, outcomes):
        adapter = make_adapter(load_config().default_entry())
        calls = []

        def call_api(request_body):
            calls.append(request_body)
            outcome = outcomes.pop(0)
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome

        adapter.call_api = call_api
        return adapter, calls

    def test_classifies_transient_errors(self):
        http = lambda code: urllib.error.HTTPError("u", code, "m", {}, None)  # noqa: E731
        self.assertTrue(is_transient(http(429)))
        self.assertTrue(is_transient(http(503)))
        self.assertFalse(is_transient(http(401)))
        self.assertTrue(is_transient(urllib.error.URLError("down")))
        self.assertTrue(is_transient(TimeoutError()))
        self.assertTrue(is_transient(_StatusError(429)))
        self.assertFalse(is_transient(_StatusError(400)))
        self.assertFalse(is_transient(ValueError("bad json")))

    def test_retries_transient_then_succeeds(self):
        adapter, calls = self._adapter([_StatusError(429), _StatusError(502), {"ok": True}])
        slept = []
        self.assertEqual(adapter.call({"m": 1}, sleep=slept.append), {"ok": True})
        self.assertEqual(len(calls), 3)
        self.assertEqual(slept, [2.0, 8.0])

    def test_gives_up_after_backoffs_exhausted(self):
        adapter, calls = self._adapter([_StatusError(429)] * 3)
        with self.assertRaises(_StatusError):
            adapter.call({}, sleep=lambda _s: None)
        self.assertEqual(len(calls), 3)

    def test_non_transient_fails_immediately(self):
        adapter, calls = self._adapter([_StatusError(401), {"never": True}])
        with self.assertRaises(_StatusError):
            adapter.call({}, sleep=lambda _s: None)
        self.assertEqual(len(calls), 1)


class ChurnTests(unittest.TestCase):
    def test_counts_added_and_removed_lines_per_file_descending(self):
        self.assertEqual(churn_by_file(TWO_FILE_DIFF), [("core/router.ts", 3), ("docs/x.md", 2)])

    def test_file_headers_are_not_counted(self):
        diff = "diff --git a/f b/f\n--- a/f\n+++ b/f\n@@ -1,1 +1,1 @@\n-x\n+y\n"
        self.assertEqual(churn_by_file(diff), [("f", 2)])

    def test_empty_diff(self):
        self.assertEqual(churn_by_file(""), [])


class FocusAreaTests(unittest.TestCase):
    GOOD = {
        "title": "Cancel vs. abandon race",
        "invariant": "a cancelled task always ends in abandonStepRun(cancelled)",
        "paths": ["apps/dispatcher-core/src/workflows/session-workflow.ts"],
        "why": "the abandon implementation is outside this diff",
    }

    def test_absent_key_is_empty(self):
        self.assertEqual(parse_focus_areas({"summary": "s", "comments": []}), [])

    def test_parses_well_formed_entries(self):
        areas = parse_focus_areas({"focus_areas": [self.GOOD]})
        self.assertEqual(len(areas), 1)
        self.assertEqual(areas[0].title, "Cancel vs. abandon race")
        self.assertEqual(areas[0].paths, [self.GOOD["paths"][0]])

    def test_drops_malformed_entries_and_non_string_paths(self):
        bad = [
            "not a dict",
            {"title": "no invariant", "paths": ["a"]},
            {**self.GOOD, "paths": "a-string-not-a-list"},
            {**self.GOOD, "paths": ["ok", 7]},
        ]
        areas = parse_focus_areas({"focus_areas": bad})
        self.assertEqual(len(areas), 1)
        self.assertEqual(areas[0].paths, ["ok"])

    def test_caps_at_three(self):
        many = [{**self.GOOD, "title": f"t{i}"} for i in range(6)]
        self.assertEqual(len(parse_focus_areas({"focus_areas": many})), 3)

    def test_tolerates_non_list(self):
        self.assertEqual(parse_focus_areas({"focus_areas": "nope"}), [])


class FocusSectionTests(unittest.TestCase):
    def test_empty_when_no_areas(self):
        self.assertEqual(format_focus_section([]), "")

    def test_lists_each_area_with_invariant_and_paths(self):
        areas = parse_focus_areas({"focus_areas": [FocusAreaTests.GOOD]})
        section = format_focus_section(areas)
        self.assertIn("### Suggested focused passes", section)
        self.assertIn("**Cancel vs. abandon race**", section)
        self.assertIn("abandonStepRun(cancelled)", section)
        self.assertIn("`apps/dispatcher-core/src/workflows/session-workflow.ts`", section)


def _cat(id, context=1_000_000, alias="", prompt="0.000005", created=0):
    return {
        "id": id,
        "name": id,
        "context_length": context,
        "pricing": {"prompt": prompt, "completion": "0.00002"},
        **({"alias_target": {"slug": alias}} if alias else {}),
        **({"created": created} if created else {}),
    }


MAR_2026 = 1_774_915_200
APR_2026 = 1_777_507_200
AUG_2026 = 1_786_492_800
SEP_2026 = 1_789_948_800


class ModelFamilyTests(unittest.TestCase):
    def test_version_is_the_first_numeric_run(self):
        self.assertEqual(model_family("anthropic/claude-opus-5"), ("anthropic/claude-opus", (5,)))
        self.assertEqual(
            model_family("anthropic/claude-opus-5.5"), ("anthropic/claude-opus", (5, 5))
        )
        self.assertEqual(model_family("openai/gpt-6.1-sol"), ("openai/gpt-sol", (6, 1)))
        self.assertEqual(model_family("openai/gpt-6-astra-pro"), ("openai/gpt-astra-pro", (6,)))
        self.assertEqual(
            model_family("google/gemini-3.1-flash-lite-preview"),
            ("google/gemini-flash-lite", (3, 1)),
        )

    def test_hyphenated_version_run(self):
        self.assertEqual(
            model_family("anthropic/claude-3-5-sonnet-20241022"),
            ("anthropic/claude-sonnet-20241022", (3, 5)),
        )

    def test_no_version(self):
        self.assertEqual(model_family("openai/o-mini"), ("openai/o-mini", ()))

    def test_variant_suffix_is_part_of_the_family(self):
        self.assertNotEqual(model_family("z-ai/glm-5.3")[0], model_family("z-ai/glm-5.3:free")[0])
        self.assertNotEqual(
            model_family("openai/gpt-6-astra")[0], model_family("openai/gpt-6-astra-pro")[0]
        )

    def test_stage_tokens_are_not_part_of_the_family(self):
        self.assertEqual(model_family("google/gemini-3.1-pro-preview")[0], "google/gemini-pro")
        self.assertEqual(model_family("google/gemini-3.1-pro")[0], "google/gemini-pro")
        self.assertEqual(model_family("v/m-beta")[0], "v/m")
        self.assertTrue(is_prerelease("google/gemini-3.1-pro-preview"))
        self.assertFalse(is_prerelease("google/gemini-3.1-pro"))
        self.assertFalse(is_prerelease("google/gemini-3.1-pro:free"))


class CheckVersionsTests(unittest.TestCase):
    CATALOG = {
        "data": [
            _cat("anthropic/claude-opus-5"),
            _cat("anthropic/claude-opus-5.5", prompt="0.000004"),
            _cat("anthropic/claude-opus-5.5:batch"),
            _cat("~anthropic/claude-opus-latest", alias="anthropic/claude-opus-5.5"),
            _cat("anthropic/claude-opus-5.5-pro"),
            _cat("openai/gpt-6.1-sol"),
            _cat("google/gemini-3.1-pro-preview"),
            _cat("google/gemini-3.2-pro-preview", context=2_000_000),
        ]
    }

    def _roster(self):
        def entry(key, access_method, id):
            return {"key": key, "name": key, "access_method": access_method, "id": id}

        return parse_config(
            _raw(
                [
                    entry("opus", "openrouter", "anthropic/claude-opus-5"),
                    entry("sol", "openrouter", "openai/gpt-6.1-sol"),
                    entry("gem", "gemini_api", "gemini-3.1-pro-preview"),
                    entry("ghost", "openrouter", "x-ai/grok-9"),
                ],
                default="opus",
            )
        )

    def _report(self):
        reports = check_versions(self._roster(), parse_openrouter_catalog(self.CATALOG))
        return {r.entry.key: r for r in reports}

    def test_reports_newest_same_family_pinned_id(self):
        report = self._report()
        self.assertEqual(report["opus"].newest.id, "anthropic/claude-opus-5.5")
        self.assertIsNone(report["sol"].newest)
        self.assertTrue(report["sol"].in_catalog)

    def test_aliases_batch_and_suffixed_variants_are_not_upgrades(self):
        report = self._report()
        # not the :batch variant, the ~alias, or the -pro sibling
        self.assertEqual(report["opus"].newest.id, "anthropic/claude-opus-5.5")

    def test_direct_api_ids_match_by_catalog_suffix(self):
        report = self._report()
        self.assertEqual(report["gem"].newest.id, "google/gemini-3.2-pro-preview")

    def test_entry_missing_from_catalog_is_flagged(self):
        report = self._report()
        self.assertFalse(report["ghost"].in_catalog)
        self.assertIsNone(report["ghost"].newest)

    def test_report_format(self):
        text = format_version_report(list(self._report().values()))
        self.assertIn("anthropic/claude-opus-5.5", text)
        self.assertIn("up to date", text)
        self.assertIn("not in catalog", text)
        self.assertIn("2M", text)


class CheckVersionsByDateTests(unittest.TestCase):
    """xAI numbers decimally: 4.20 (March) precedes 4.3, 4.6 (August) and 4.7 (September)."""

    CATALOG = {
        "data": [
            _cat("x-ai/grok-4.20", context=2_000_000, created=MAR_2026),
            _cat("x-ai/grok-4.3", created=APR_2026),
            _cat("x-ai/grok-4.6", context=500_000, created=AUG_2026),
            _cat("x-ai/grok-4.7", context=500_000, created=SEP_2026),
        ]
    }

    def _report(self, current_id):
        entry = {"key": "grok", "name": "Grok", "access_method": "openrouter", "id": current_id}
        roster = parse_config(_raw([entry], default="grok"))
        return check_versions(roster, parse_openrouter_catalog(self.CATALOG))[0]

    def test_listing_date_beats_version_arithmetic(self):
        self.assertEqual(self._report("x-ai/grok-4.6").newest.id, "x-ai/grok-4.7")

    def test_decimal_style_higher_number_is_not_an_upgrade(self):
        self.assertEqual(self._report("x-ai/grok-4.20").newest.id, "x-ai/grok-4.7")
        self.assertIsNone(self._report("x-ai/grok-4.7").newest)

    def test_report_shows_both_listing_dates(self):
        text = format_version_report([self._report("x-ai/grok-4.6")])
        self.assertIn("2026-08-12", text)
        self.assertIn("2026-09-21", text)

    def test_final_release_supersedes_the_pinned_preview(self):
        catalog = parse_openrouter_catalog(
            {
                "data": [
                    _cat("google/gemini-3.1-pro-preview", created=MAR_2026),
                    _cat("google/gemini-3.1-pro", created=AUG_2026),
                    _cat("google/gemini-3.1-pro-preview-customtools", created=APR_2026),
                ]
            }
        )
        entry = {"key": "g", "name": "G", "access_method": "gemini_api"}
        entry["id"] = "gemini-3.1-pro-preview"
        roster = parse_config(_raw([entry], default="g"))
        report = check_versions(roster, catalog)[0]
        self.assertEqual(report.newest.id, "google/gemini-3.1-pro")

    def test_a_later_preview_never_supersedes_a_final_release(self):
        catalog = parse_openrouter_catalog(
            {
                "data": [
                    _cat("google/gemini-3.1-pro", created=MAR_2026),
                    _cat("google/gemini-3.1-pro-preview", created=SEP_2026),
                ]
            }
        )
        entry = {"key": "g", "name": "G", "access_method": "openrouter"}
        entry["id"] = "google/gemini-3.1-pro"
        roster = parse_config(_raw([entry], default="g"))
        self.assertIsNone(check_versions(roster, catalog)[0].newest)

    def test_final_beats_preview_at_equal_version_without_dates(self):
        catalog = parse_openrouter_catalog({"data": [_cat("v/m-2-beta"), _cat("v/m-2")]})
        entry = {"key": "m", "name": "M", "access_method": "openrouter", "id": "v/m-2-beta"}
        roster = parse_config(_raw([entry], default="m"))
        self.assertEqual(check_versions(roster, catalog)[0].newest.id, "v/m-2")

    def test_version_tuple_is_the_fallback_without_dates(self):
        catalog = parse_openrouter_catalog({"data": [_cat("v/m-1.2"), _cat("v/m-1.10")]})
        entry = {"key": "m", "name": "M", "access_method": "openrouter", "id": "v/m-1.2"}
        roster = parse_config(_raw([entry], default="m"))
        self.assertEqual(check_versions(roster, catalog)[0].newest.id, "v/m-1.10")


class BuildPrPromptTests(unittest.TestCase):
    def test_diff_only(self):
        prompt = build_pr_prompt("X", context_block="", extra_instructions="", context_files=[])
        self.assertTrue(prompt.startswith("Review this PR diff:"))
        self.assertNotIn("<context_files>", prompt)

    def test_order_is_instructions_then_description_then_files_then_diff(self):
        prompt = build_pr_prompt(
            "DIFF",
            context_block="<pr_description>\nTitle: t\n</pr_description>\n\n",
            extra_instructions="Focus on cancel paths.",
            context_files=[("docs/rfcs/0009.md", "# RFC 0009\nD4: resume adds max_attempts.")],
        )
        i_instr = prompt.index("Focus on cancel paths.")
        i_desc = prompt.index("<pr_description>")
        i_files = prompt.index('<file path="docs/rfcs/0009.md">')
        i_diff = prompt.index("Review this PR diff:")
        self.assertLess(i_instr, i_desc)
        self.assertLess(i_desc, i_files)
        self.assertLess(i_files, i_diff)
        self.assertIn("D4: resume adds max_attempts.", prompt)
        self.assertIn("</context_files>", prompt)


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


# A trimmed OpenRouter /models payload: one pinned model, its floating alias,
# its batch variant, and an unrelated family to prove the filter excludes.
CATALOG_PAYLOAD = {
    "data": [
        {
            "id": "~openai/gpt-astra-latest",
            "name": "OpenAI: GPT Astra Latest",
            "context_length": 1050000,
            "alias_target": {"slug": "openai/gpt-6-astra"},
            "pricing": {"prompt": "0.00001", "completion": "0.00005"},
        },
        {
            "id": "openai/gpt-6-astra:batch",
            "name": "OpenAI: GPT-6 Astra (batch)",
            "context_length": 1050000,
            "pricing": {"prompt": "0.000005", "completion": "0.000025"},
        },
        {
            "id": "openai/gpt-6-astra",
            "name": "OpenAI: GPT-6 Astra",
            "context_length": 1050000,
            "pricing": {"prompt": "0.00001", "completion": "0.00005"},
        },
        {
            "id": "z-ai/glm-5.3",
            "name": "Z.AI: GLM 5.3",
            "context_length": 200000,
            "pricing": {"prompt": "0.0000006", "completion": "0.0000022"},
        },
    ]
}


class CatalogParseTests(unittest.TestCase):
    def test_prices_are_converted_to_dollars_per_million_tokens(self):
        by_id = {m.id: m for m in parse_openrouter_catalog(CATALOG_PAYLOAD)}
        self.assertAlmostEqual(by_id["openai/gpt-6-astra"].prompt_price, 10.0)
        self.assertAlmostEqual(by_id["openai/gpt-6-astra"].completion_price, 50.0)

    def test_alias_target_and_batch_variants_are_flagged(self):
        by_id = {m.id: m for m in parse_openrouter_catalog(CATALOG_PAYLOAD)}
        self.assertEqual(
            by_id["~openai/gpt-astra-latest"].alias_target, "openai/gpt-6-astra"
        )
        self.assertFalse(by_id["openai/gpt-6-astra"].alias_target)
        self.assertTrue(by_id["openai/gpt-6-astra:batch"].is_batch)
        self.assertFalse(by_id["openai/gpt-6-astra"].is_batch)

    def test_missing_pricing_and_context_do_not_raise(self):
        models = parse_openrouter_catalog({"data": [{"id": "x/y", "name": "X"}]})
        self.assertEqual(models[0].prompt_price, 0.0)
        self.assertEqual(models[0].context_length, 0)

    def test_entries_without_an_id_are_skipped(self):
        self.assertEqual(parse_openrouter_catalog({"data": [{"name": "nameless"}]}), [])

    def test_absent_data_key_yields_no_models(self):
        self.assertEqual(parse_openrouter_catalog({}), [])


class CatalogFilterTests(unittest.TestCase):
    def setUp(self):
        self.models = parse_openrouter_catalog(CATALOG_PAYLOAD)

    def test_pinned_interactive_id_sorts_above_alias_and_batch(self):
        hits = filter_catalog(self.models, "astra")
        self.assertEqual(
            [m.id for m in hits],
            [
                "openai/gpt-6-astra",
                "openai/gpt-6-astra:batch",
                "~openai/gpt-astra-latest",
            ],
        )

    def test_match_is_case_insensitive_and_covers_display_name(self):
        # "Z.AI" appears only in the name; the id spells it "z-ai".
        self.assertEqual([m.id for m in filter_catalog(self.models, "z.aI")], ["z-ai/glm-5.3"])

    def test_non_matching_query_returns_nothing(self):
        self.assertEqual(filter_catalog(self.models, "claude"), [])


class CatalogFormatTests(unittest.TestCase):
    def test_table_annotates_alias_target_and_batch(self):
        table = format_catalog(filter_catalog(parse_openrouter_catalog(CATALOG_PAYLOAD), "astra"))
        self.assertIn("alias -> openai/gpt-6-astra", table)
        self.assertIn("batch (queued, not interactive)", table)

    def test_table_shows_compact_context_and_per_million_price(self):
        table = format_catalog(filter_catalog(parse_openrouter_catalog(CATALOG_PAYLOAD), "gpt-6-astra"))
        self.assertIn("1.05M", table)
        self.assertIn("$10/$50", table)
