"""Unit tests for agent_code_reviewer.py pure helpers.

Run with: python3 -m unittest cli.test_agent_code_reviewer -v
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime
from email.message import Message
from io import StringIO
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_code_reviewer import (  # noqa: E402
    CHARS_PER_TOKEN,
    DEFAULT_CONTEXT_WINDOW,
    REPLY_RESERVE_TOKENS,
    MAX_SLICE_RUNS,
    SLICE_GATE_TOKENS,
    ConfigError,
    IncompleteReplyError,
    ModelEntry,
    OpenRouterAdapter,
    FocusArea,
    FocusRecord,
    _build_line_content_index,
    _path_matches_any,
    annotate_diff_with_line_numbers,
    build_pr_prompt,
    catalog_cache_path,
    catalog_check,
    check_versions,
    churn_by_file,
    diff_char_budget,
    drop_already_posted,
    entries_that_fit,
    filter_catalog,
    focus_file_path,
    prune_focus_paths,
    require_complete,
    review_pr,
    slice_gate_reason,
    write_focus_file,
    VersionReport,
    format_catalog,
    format_exclusions,
    format_focus_section,
    format_new_families,
    format_version_report,
    get_pr_diff,
    is_prerelease,
    is_transient,
    load_cached_catalog,
    load_config,
    load_focus_file,
    major_jumps,
    make_adapter,
    model_family,
    new_families,
    parse_config,
    parse_focus_areas,
    parse_openrouter_catalog,
    plan_pr_input,
)


def _newest_id(report: VersionReport) -> str:
    assert report.newest is not None
    return report.newest.id


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
    return {"default": default, "catalog_reviewed": date(2026, 1, 1), "models": models}


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

    def test_catalog_reviewed_is_a_date(self):
        self.assertEqual(parse_config(_raw()).catalog_reviewed, date(2026, 1, 1))

    def test_rejects_missing_quoted_or_timestamped_catalog_reviewed(self):
        for value in (None, "2026-01-01", datetime(2026, 1, 1, 12)):
            with self.subTest(value=value):
                raw = _raw()
                if value is None:
                    del raw["catalog_reviewed"]
                else:
                    raw["catalog_reviewed"] = value
                with self.assertRaises(ConfigError) as ctx:
                    parse_config(raw)
                self.assertIn("catalog_reviewed", str(ctx.exception))

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


def _entry(**fields: object) -> ModelEntry:
    model = {"key": "a", "name": "A", "access_method": "openrouter", "id": "v/m", **fields}
    return parse_config(_raw([model])).entries[0]


class OutputBudgetTests(unittest.TestCase):
    def test_unset_means_no_cap(self):
        self.assertIsNone(_entry().max_output_tokens)

    def test_explicit_value_wins(self):
        entry = _entry(context_window=1_050_000, max_output_tokens=128_000)
        self.assertEqual(entry.max_output_tokens, 128_000)

    def test_rejects_non_positive_non_int_or_not_below_the_window(self):
        for bad in (0, -1, "128K", True, 200_000):
            with self.subTest(bad=bad), self.assertRaises(ConfigError):
                _entry(context_window=200_000, max_output_tokens=bad)


class DiffBudgetTests(unittest.TestCase):
    def test_budget_is_window_minus_output_budget_in_chars_minus_overhead(self):
        budget = diff_char_budget(_entry(context_window=100_000), overhead_chars=1_000)
        self.assertEqual(budget, int((100_000 - REPLY_RESERVE_TOKENS) * CHARS_PER_TOKEN) - 1_000)
        wide = _entry(context_window=1_050_000, max_output_tokens=128_000)
        self.assertEqual(diff_char_budget(wide, overhead_chars=0), int(922_000 * CHARS_PER_TOKEN))

    def test_budget_never_negative(self):
        tight = _entry(context_window=1_000, max_output_tokens=999)
        self.assertEqual(diff_char_budget(tight, overhead_chars=10), 0)

    def test_old_hardcoded_cap_is_far_below_a_million_token_window(self):
        """Regression guard for the 100 KB cap that forced layer-wise slicing."""
        self.assertGreater(
            diff_char_budget(_entry(context_window=1_050_000), 0), int(759_000 * CHARS_PER_TOKEN)
        )

    def test_estimate_covers_a_measured_prompt(self):
        """werkshop PR #85: 1,557,816 chars of annotated diff drew a 479,897-token
        prompt (diff plus system prompt and description). The diff estimate alone
        must not undercount it."""
        self.assertGreaterEqual(int(1_557_816 / CHARS_PER_TOKEN), 479_897)

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
        needed_chars = int(759_000 * CHARS_PER_TOKEN)  # a ~760K-token diff; only the 1M window takes it
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


TOO_LARGE = (
    "could not find pull request diff: HTTP 406: Sorry, the diff exceeded the maximum "
    "number of lines (20000)\nPullRequest.diff too_large\n"
)
PR_HEAD = "0123456789abcdef0123456789abcdef01234567"


def fake_subprocess(*answers: tuple[int, str, str]):
    """Patch subprocess.run to answer (returncode, stdout, stderr) in call order,
    so nothing touches gh, git, or the network. Yields the argv of every call."""
    calls: list[list[str]] = []
    queue = list(answers)

    def run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        code, out, err = queue.pop(0)
        return subprocess.CompletedProcess(args, code, out, err)

    return mock.patch.object(subprocess, "run", run), calls


class PrDiffTests(unittest.TestCase):
    def _get(self, *answers: tuple[int, str, str]) -> tuple[str, list[list[str]], str]:
        patch, calls = fake_subprocess(*answers)
        err = StringIO()
        with patch, redirect_stderr(err):
            diff = get_pr_diff("85")
        return diff, calls, err.getvalue()

    def test_served_diff_is_used_as_is(self):
        diff, calls, _ = self._get((0, SAMPLE_DIFF, ""))
        self.assertEqual(diff, SAMPLE_DIFF)
        self.assertEqual(len(calls), 1)

    def test_too_large_diff_is_built_locally_at_the_pr_head(self):
        diff, calls, err = self._get(
            (1, "", TOO_LARGE),
            (0, f'{{"baseRefName": "main", "headRefOid": "{PR_HEAD}"}}', ""),
            (0, "", ""),
            (0, SAMPLE_DIFF, ""),
        )
        self.assertEqual(diff, SAMPLE_DIFF)
        fetch, local = calls[2], calls[3]
        self.assertEqual(fetch[:2], ["git", "fetch"])
        self.assertIn("pull/85/head", fetch)
        self.assertIn("+refs/heads/main:refs/remotes/origin/main", fetch)
        self.assertEqual(local[:2], ["git", "diff"])
        self.assertEqual(local[-1], f"origin/main...{PR_HEAD}")
        self.assertEqual(len(err.splitlines()), 1)
        self.assertIn("built it locally", err)

    def test_other_gh_failures_still_exit(self):
        with self.assertRaises(SystemExit):
            self._get((1, "", "HTTP 404: Not Found"))

    def test_failed_local_build_exits(self):
        with self.assertRaises(SystemExit):
            self._get(
                (1, "", TOO_LARGE),
                (0, f'{{"baseRefName": "main", "headRefOid": "{PR_HEAD}"}}', ""),
                (128, "", "fatal: 'origin' does not appear to be a git repository"),
            )


def _openrouter_payload(content: str | None, finish: str, cost: float | None = None) -> dict[str, object]:
    usage: dict[str, object] = {
        "prompt_tokens": 389454,
        "completion_tokens": 128000,
        "completion_tokens_details": {"reasoning_tokens": 128000},
    }
    if cost is not None:
        usage["cost"] = cost
    return {
        "id": "gen-1761100000-abc",
        "choices": [{"finish_reason": finish, "message": {"role": "assistant", "content": content}}],
        "usage": usage,
    }


class ModelReplyTests(unittest.TestCase):
    def setUp(self):
        self.openrouter = make_adapter(_entry(context_window=1_050_000, max_output_tokens=128_000))

    def test_a_declared_budget_is_sent_and_an_unset_one_is_not(self):
        self.assertEqual(self.openrouter.build_request("sys", [])["max_tokens"], 128_000)
        self.assertNotIn("max_tokens", make_adapter(_entry()).build_request("sys", []))
        gemini = make_adapter(_entry(access_method="gemini_api", max_output_tokens=9_000))
        body = gemini.build_request("sys", [])
        self.assertEqual(body["generationConfig"]["maxOutputTokens"], 9_000)
        bare = make_adapter(_entry(access_method="gemini_api")).build_request("sys", [])
        self.assertNotIn("generationConfig", bare)
        openai = make_adapter(_entry(access_method="openai_api", max_output_tokens=9_000))
        self.assertEqual(openai.build_request("sys", [])["max_output_tokens"], 9_000)
        bare = make_adapter(_entry(access_method="openai_api")).build_request("sys", [])
        self.assertNotIn("max_output_tokens", bare)

    def test_normal_stop_passes_with_usage_and_generation_id(self):
        reply = require_complete(
            self.openrouter.extract_response(_openrouter_payload('{"summary": "ok"}', "stop"))
        )
        self.assertEqual(reply.generation_id, "gen-1761100000-abc")
        self.assertEqual((reply.prompt_tokens, reply.reasoning_tokens), (389_454, 128_000))

    def test_openrouter_cost_is_read_and_reported(self):
        reply = self.openrouter.extract_response(_openrouter_payload("{}", "stop", cost=1.45))
        self.assertEqual(reply.cost, 1.45)
        self.assertEqual(reply.usage(), "389,454 prompt + 128,000 completion (128,000 reasoning); cost $1.4500")
        self.assertIn("cost $1.4500", reply.describe())
        self.assertIsNone(self.openrouter.extract_response(_openrouter_payload("{}", "stop")).cost)

    def test_empty_content_is_refused_with_stop_reason_usage_and_generation_id(self):
        reply = self.openrouter.extract_response(_openrouter_payload(None, "stop"))
        with self.assertRaises(IncompleteReplyError) as caught:
            require_complete(reply)
        message = str(caught.exception)
        self.assertIn("empty", message)
        self.assertIn("stop reason stop", message)
        self.assertIn("389,454 prompt + 128,000 completion (128,000 reasoning)", message)
        self.assertIn("gen-1761100000-abc", message)

    def test_length_stop_is_refused_even_with_text(self):
        reply = self.openrouter.extract_response(_openrouter_payload('{"summary": "trunc', "length"))
        with self.assertRaisesRegex(IncompleteReplyError, "cut off: stop reason length"):
            require_complete(reply)

    def test_gemini_max_tokens_is_cut_off_and_counts_thoughts_as_completion(self):
        gemini = make_adapter(_entry(access_method="gemini_api"))
        reply = gemini.extract_response(
            {
                "candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": "{"}]}}],
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 5,
                    "thoughtsTokenCount": 7,
                },
            }
        )
        self.assertFalse(reply.complete)
        self.assertEqual((reply.completion_tokens, reply.reasoning_tokens), (12, 7))

    def test_openai_incomplete_reports_its_reason(self):
        openai = make_adapter(_entry(access_method="openai_api"))
        reply = openai.extract_response(
            {
                "id": "resp_1",
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
                "output_text": "{",
                "usage": {"input_tokens": 10, "output_tokens": 32000},
            }
        )
        self.assertEqual((reply.stop_reason, reply.complete), ("max_output_tokens", False))
        self.assertEqual(reply.signature, "resp_1")


class _CannedOpenRouter(OpenRouterAdapter):
    """Answers at the network boundary: call_api returns a canned response."""

    def __init__(self, entry: ModelEntry, canned: dict[str, object]) -> None:
        super().__init__(entry)
        self.canned = canned

    def call_api(self, request_body):
        return self.canned


class ReviewPrRefusalTests(unittest.TestCase):
    def _review(self, payload: dict[str, object]) -> list[list[str]]:
        roster = parse_config(_raw([{"key": "a", "name": "A", "access_method": "openrouter", "id": "v/m"}]))
        adapter = _CannedOpenRouter(roster.entries[0], payload)
        patch, calls = fake_subprocess(
            (0, SAMPLE_DIFF, ""),
            (0, f'{{"title": "t", "body": "b", "headRefOid": "{PR_HEAD}"}}', ""),
            (0, "owner/repo\n", ""),
        )
        with patch, redirect_stderr(StringIO()), self.assertRaises(IncompleteReplyError):
            review_pr("85", adapter, roster)
        return calls

    def test_empty_reply_posts_nothing(self):
        calls = self._review(_openrouter_payload("", "stop"))
        self.assertFalse([c for c in calls if c[:2] == ["gh", "api"]])

    def test_length_cut_reply_posts_nothing(self):
        calls = self._review(_openrouter_payload('{"summary": "trunc', "length"))
        self.assertFalse([c for c in calls if c[:2] == ["gh", "api"]])


class _RecordingOpenRouter(_CannedOpenRouter):
    def call_api(self, request_body):
        self.sent = request_body
        return self.canned


class ReviewPrExclusionTests(unittest.TestCase):
    PR = "990085"

    def tearDown(self):
        focus_file_path(self.PR, "owner_repo").unlink(missing_ok=True)

    def test_dry_run_names_what_was_left_out_to_the_model_and_on_stdout(self):
        roster = parse_config(_raw([{"key": "a", "name": "A", "access_method": "openrouter", "id": "v/m"}]))
        adapter = _RecordingOpenRouter(roster.entries[0], _openrouter_payload('{"summary": "ok"}', "stop", cost=1.45))
        diff = _block("src/a.ts") + _block("pnpm-lock.yaml") + _block("docs/x.md")
        patch, _ = fake_subprocess(
            (0, diff, ""),
            (0, f'{{"title": "t", "body": "b", "headRefOid": "{PR_HEAD}"}}', ""),
            (0, "owner/repo\n", ""),
        )
        out = StringIO()
        with patch, redirect_stderr(StringIO()), redirect_stdout(out):
            review_pr(self.PR, adapter, roster, dry_run=True)
        prompt = adapter.sent["messages"][-1]["content"]
        self.assertIn("<excluded_files>", prompt)
        self.assertIn("pnpm-lock.yaml", prompt)
        self.assertNotIn("diff --git a/pnpm-lock.yaml", prompt)
        printed = json.loads(out.getvalue())
        self.assertEqual(printed["excluded"], {"lockfiles": ["pnpm-lock.yaml"], "docs": ["docs/x.md"]})
        self.assertIn("lockfiles: 1, docs: 1", printed["summary"])
        self.assertEqual(
            printed["usage"],
            {"prompt_tokens": 389_454, "completion_tokens": 128_000, "reasoning_tokens": 128_000, "cost": 1.45},
        )


class ExclusionReportTests(unittest.TestCase):
    def test_counts_per_category_in_report_order(self):
        self.assertEqual(format_exclusions({"docs": ["a.md", "b.md"], "tests": ["a.test.ts"]}), "docs: 2, tests: 1")
        self.assertEqual(format_exclusions({}), "")

    def test_prompt_block_lists_paths_before_the_diff_and_caps_each_category(self):
        tests = [f"t{i}.test.ts" for i in range(45)]
        prompt = build_pr_prompt("DIFF", "", "", [], {"lockfiles": ["yarn.lock"], "tests": tests})
        block = prompt[prompt.index("<excluded_files>") : prompt.index("</excluded_files>")]
        self.assertLess(prompt.index("</excluded_files>"), prompt.index("Review this PR diff:"))
        self.assertIn("lockfiles (1): yarn.lock", block)
        self.assertIn("tests (45): t0.test.ts", block)
        self.assertIn("t39.test.ts, and 5 more", block)
        self.assertNotIn("t40.test.ts", block)

    def test_no_exclusions_means_no_block(self):
        self.assertNotIn("<excluded_files>", build_pr_prompt("DIFF", "", "", [], {}))


class IgnorePathTests(unittest.TestCase):
    def test_bracketed_route_path_matches_literally(self):
        path = "app/api/auth/[...nextauth]/route.ts"
        self.assertTrue(_path_matches_any(path, [path]))

    def test_directory_prefix_and_glob_still_match(self):
        self.assertTrue(_path_matches_any("docs/a/b.md", ["docs/"]))
        self.assertTrue(_path_matches_any("x/y.snap", ["*.snap"]))
        self.assertFalse(_path_matches_any("src/y.ts", ["docs/", "*.snap"]))

    def test_double_star_prefix_matches_at_the_root_and_any_depth(self):
        self.assertTrue(_path_matches_any("pnpm-lock.yaml", ["**/pnpm-lock.yaml"]))
        self.assertTrue(_path_matches_any("apps/web/pnpm-lock.yaml", ["**/pnpm-lock.yaml"]))
        self.assertTrue(_path_matches_any("packages/ui/dist/a.js", ["**/dist/"]))
        self.assertFalse(_path_matches_any("src/distance.ts", ["**/dist/"]))


def _block(path: str, body: str = "+x\n", start: int = 1) -> str:
    """One file's unified-diff block adding `body` from new line `start`."""
    return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -0,0 +{start},1 @@\n{body}"


def _sized(path: str, tokens: int, text: str = "x") -> str:
    """A block whose annotated size estimates to about `tokens` tokens."""
    line = f"+{text} " + "y" * 60 + "\n"
    return _block(path, line * max(1, int(tokens * CHARS_PER_TOKEN / (len(line) + 6))))


class InputPlanTests(unittest.TestCase):
    def test_lockfiles_are_never_sent_at_any_depth(self):
        locks = ["pnpm-lock.yaml", "apps/web/package-lock.json", "rust/Cargo.lock", "go.sum"]
        plan = plan_pr_input("".join(_block(p) for p in [*locks, "src/a.ts"]))
        self.assertEqual(plan.excluded, {"lockfiles": locks})
        self.assertIn("src/a.ts", plan.diff)

    def test_prose_and_docs_are_never_sent(self):
        prose = [
            "README.md",
            "docs/rfcs/0009.md",
            "docs/diagram.png",
            ".trail/learnings/fetch-quirk.md",
            "images/runner-base/licenses/open-code-review-LICENSE",
        ]
        plan = plan_pr_input("".join(_block(p) for p in [*prose, "src/a.ts"]))
        self.assertEqual(plan.excluded, {"docs": prose})

    def test_markdown_a_program_reads_is_sent(self):
        code_input = [
            ".werkshop/workshops/werkshop/prompts/plan.md",
            "agents/review.prompt.md",
            "packages/wrapper/src/task-file/__snapshots__/coding.task.md",
        ]
        plan = plan_pr_input("".join(_block(p) for p in code_input))
        self.assertEqual(plan.excluded, {})
        for path in code_input:
            self.assertIn(path, plan.diff)

    def test_generated_output_is_never_sent(self):
        generated = [
            "src/api.generated.ts",
            "packages/ui/dist/index.js",
            "vendor/github.com/x/y.go",
            "src/__snapshots__/a.test.ts.snap",
        ]
        marked = _block("proto/user.pb.go", "+// Code generated by protoc-gen-go. DO NOT EDIT.\n+package proto\n")
        plan = plan_pr_input("".join(_block(p) for p in generated) + marked)
        self.assertEqual(plan.excluded, {"generated": [*generated, "proto/user.pb.go"]})

    def test_generated_detection_stays_conservative(self):
        kept = [
            _block("schema/workshop/v1.json", '+{\n+  "$schema": "x"\n'),  # unmarked: may be hand-written
            _block("src/a.ts", "+// DO NOT EDIT the order below\n", start=40),  # not a file header
            _block("packages/external-services/model-vendor/client.ts"),
            _block("db/migrations/2026_vendor/migration.sql"),
        ]
        self.assertEqual(plan_pr_input("".join(kept)).excluded, {})

    def test_tests_and_migrations_are_sent_when_the_diff_is_under_the_threshold(self):
        diff = _sized("src/a.ts", 1_000) + _sized("src/a.test.ts", 1_000) + _sized("db/migrations/1/m.sql", 500)
        plan = plan_pr_input(diff, trim_above=5_000)
        self.assertEqual(plan.excluded, {})
        self.assertEqual(plan.diff, diff)

    def test_over_the_threshold_unrelated_tests_go_before_related_ones(self):
        diff = (
            _sized("src/landing-service.ts", 3_000)
            + _sized("src/landing-service.test.ts", 2_000)
            + _sized("src/other/billing.test.ts", 2_000)
            + _sized("test-support/fake-github.ts", 2_000, text="import { landing } from '../src/landing-service'")
            + _sized("db/migrations/1/m.sql", 500)
        )
        plan = plan_pr_input(diff, trim_above=8_000)
        self.assertEqual(plan.excluded, {"tests": ["src/other/billing.test.ts"]})
        self.assertIn("db/migrations/1/m.sql", plan.diff)
        self.assertLessEqual(plan.tokens_sent, 8_000)
        self.assertGreater(plan.tokens_before, 8_000)

    def test_migrations_go_only_after_every_test_and_only_when_that_fits(self):
        base = _sized("src/a.ts", 3_000) + _sized("src/a.test.ts", 1_000)
        fits = plan_pr_input(base + _sized("db/migrations/1/m.sql", 2_000), trim_above=4_000)
        self.assertEqual(fits.excluded, {"tests": ["src/a.test.ts"], "migrations": ["db/migrations/1/m.sql"]})
        still_huge = plan_pr_input(base + _sized("db/migrations/1/m.sql", 2_000), trim_above=2_000)
        self.assertEqual(still_huge.excluded, {"tests": ["src/a.test.ts"]})
        self.assertIn("db/migrations/1/m.sql", still_huge.diff)

    def test_zero_threshold_never_trims(self):
        diff = _sized("src/a.ts", 3_000) + _sized("src/a.test.ts", 3_000)
        self.assertEqual(plan_pr_input(diff, trim_above=0).excluded, {})

    def test_keep_path_overrides_every_exclusion(self):
        diff = _block("SKILL.md") + _block("pnpm-lock.yaml") + _sized("src/a.ts", 3_000) + _sized("src/a.test.ts", 3_000)
        plan = plan_pr_input(diff, keep_paths=["SKILL.md", "*.test.ts"], trim_above=1_000)
        self.assertEqual(plan.excluded, {"lockfiles": ["pnpm-lock.yaml"]})
        self.assertIn("SKILL.md", plan.diff)

    def test_ignore_and_only_paths_are_reported_as_their_own_categories(self):
        diff = _block("core/session/a.ts") + _block("apps/api/b.ts") + _block("core/session/a.test.ts")
        plan = plan_pr_input(diff, ignore_paths=["*.test.ts"], only_paths=["core/session/"])
        self.assertEqual(plan.excluded, {"--ignore-path": ["core/session/a.test.ts"], "--only-path": ["apps/api/b.ts"]})
        self.assertIn("core/session/a.ts", plan.diff)

    def test_nothing_to_exclude_is_identity(self):
        diff = _block("src/a.ts") + _block("src/b.py")
        plan = plan_pr_input(diff)
        self.assertEqual((plan.diff, plan.excluded), (diff, {}))
        self.assertEqual(plan.tokens_before, plan.tokens_sent)


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

    def test_written_record_loads_back(self):
        areas = [FocusArea(title="t", invariant="i", paths=["a.py"], why="")]
        with tempfile.TemporaryDirectory() as d:
            path = write_focus_file("7", areas, [("a.py", 3)], "o_r", "abc1234", 40_000, Path(d))
            self.assertEqual(path.parent, Path(d))
            focus = load_focus_file(path)
        assert focus is not None
        self.assertEqual(focus["head"], "abc1234")
        self.assertEqual(focus["churn"], [{"path": "a.py", "lines": 3}])
        self.assertEqual(focus["slices"], [])

    def test_malformed_record_is_no_record(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "focus.json"
            for body in ("not json", "[]", '{"head": 1}', '{"head": "x", "diff_tokens": 1}'):
                path.write_text(body)
                self.assertIsNone(load_focus_file(path), body)
            self.assertIsNone(load_focus_file(Path(d) / "missing.json"))


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
        http = lambda code: urllib.error.HTTPError("u", code, "m", Message(), None)  # noqa: E731
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


class HistoryTests(unittest.TestCase):
    def test_every_adapter_has_history_methods(self):
        cfg = load_config()
        for entry in cfg.entries:
            adapter = make_adapter(entry)
            for name in ("history_file", "load_history", "save_history", "reset_history"):
                self.assertTrue(callable(getattr(adapter, name, None)), f"{entry.key}.{name}")

    def test_history_round_trip_scoped_by_session(self):
        with tempfile.TemporaryDirectory() as d:
            adapter = make_adapter(load_config().default_entry(), Path(d))
            self.assertEqual(adapter.history_file().parent, Path(d))
            adapter.reset_history()
            self.assertEqual(adapter.load_history(session="s1"), [])
            msgs = adapter.add_message([], "user", "hello")
            adapter.save_history(msgs, session="s1")
            self.assertEqual(adapter.load_history(session="s1"), msgs)
            self.assertEqual(adapter.load_history(session=None), [])
            adapter.reset_history()
            self.assertEqual(adapter.load_history(session="s1"), [])


class DedupeTests(unittest.TestCase):
    def test_drops_only_exact_path_and_line_matches(self):
        comments = [
            {"path": "a.ts", "line": 10, "body": "x"},
            {"path": "a.ts", "line": 11, "body": "y"},
            {"path": "b.ts", "line": 10, "body": "z"},
        ]
        kept = drop_already_posted(comments, {("a.ts", 10)})
        self.assertEqual([(c["path"], c["line"]) for c in kept], [("a.ts", 11), ("b.ts", 10)])

    def test_empty_posted_set_is_identity(self):
        comments = [{"path": "a.ts", "line": 1, "body": "x"}]
        self.assertEqual(drop_already_posted(comments, set()), comments)


def _focus(
    *, focus_areas: list[dict] | None = None, slices: int = 0, diff_tokens: int = 40_000
) -> FocusRecord:
    return FocusRecord(
        repo="o/r",
        pr="1",
        head="abc1234",
        diff_tokens=diff_tokens,
        focus_areas=focus_areas or [],
        churn=[],
        slices=["s"] * slices,
    )


class SliceGateTests(unittest.TestCase):
    def _refusal(self, focus: FocusRecord | None, head: str) -> str:
        reason = slice_gate_reason(focus, head)
        assert reason is not None
        return reason

    NOMINATED = _focus(focus_areas=[{"title": "t"}])
    QUIET_SMALL = _focus()
    QUIET_LARGE = _focus(diff_tokens=SLICE_GATE_TOKENS)

    def test_no_whole_pass_refuses(self):
        self.assertIn("no whole-diff pass", self._refusal(None, "abc1234"))

    def test_nomination_admits(self):
        self.assertIsNone(slice_gate_reason(self.NOMINATED, "abc1234"))

    def test_quiet_small_pass_refuses(self):
        self.assertIn("nominated no focus area", self._refusal(self.QUIET_SMALL, "abc1234"))

    def test_quiet_large_pass_admits(self):
        self.assertIsNone(slice_gate_reason(self.QUIET_LARGE, "abc1234"))

    def test_moved_head_refuses(self):
        self.assertIn("PR is now at", self._refusal(self.NOMINATED, "fff9999"))

    def test_cap_refuses_fourth_slice(self):
        full = _focus(focus_areas=[{"title": "t"}], slices=MAX_SLICE_RUNS)
        self.assertIn("already run", self._refusal(full, "abc1234"))
        almost = _focus(focus_areas=[{"title": "t"}], slices=MAX_SLICE_RUNS - 1)
        self.assertIsNone(slice_gate_reason(almost, "abc1234"))


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


def _cat(id, context=1_000_000, alias="", prompt="0.000005", created=0, outputs=None):
    return {
        "id": id,
        "name": id,
        "context_length": context,
        "pricing": {"prompt": prompt, "completion": "0.00002"},
        **({"alias_target": {"slug": alias}} if alias else {}),
        **({"created": created} if created else {}),
        **({"architecture": {"output_modalities": outputs}} if outputs else {}),
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
        self.assertEqual(_newest_id(report["opus"]), "anthropic/claude-opus-5.5")
        self.assertIsNone(report["sol"].newest)
        self.assertTrue(report["sol"].in_catalog)

    def test_aliases_batch_and_suffixed_variants_are_not_upgrades(self):
        report = self._report()
        # not the :batch variant, the ~alias, or the -pro sibling
        self.assertEqual(_newest_id(report["opus"]), "anthropic/claude-opus-5.5")

    def test_direct_api_ids_match_by_catalog_suffix(self):
        report = self._report()
        self.assertEqual(_newest_id(report["gem"]), "google/gemini-3.2-pro-preview")

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
        self.assertEqual(_newest_id(self._report("x-ai/grok-4.6")), "x-ai/grok-4.7")

    def test_decimal_style_higher_number_is_not_an_upgrade(self):
        self.assertEqual(_newest_id(self._report("x-ai/grok-4.20")), "x-ai/grok-4.7")
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
        self.assertEqual(_newest_id(report), "google/gemini-3.1-pro")

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
        self.assertEqual(_newest_id(check_versions(roster, catalog)[0]), "v/m-2")

    def test_version_tuple_is_the_fallback_without_dates(self):
        catalog = parse_openrouter_catalog({"data": [_cat("v/m-1.2"), _cat("v/m-1.10")]})
        entry = {"key": "m", "name": "M", "access_method": "openrouter", "id": "v/m-1.2"}
        roster = parse_config(_raw([entry], default="m"))
        self.assertEqual(_newest_id(check_versions(roster, catalog)[0]), "v/m-1.10")


DAY = 24 * 60 * 60


def _family_roster(reviewed=date(2026, 4, 30), extra=()):
    """A Gemini and a Claude entry, reviewed through `reviewed` (APR_2026's day)."""
    def entry(key, access_method, id):
        return {"key": key, "name": key, "access_method": access_method, "id": id}

    entries = [
        entry("gem", "gemini_api", "gemini-3.1-pro-preview"),
        entry("opus", "openrouter", "anthropic/claude-opus-5.5"),
        *extra,
    ]
    raw = _raw(entries, default="gem")
    raw["catalog_reviewed"] = reviewed
    return parse_config(raw)


ROSTER_ROWS = [
    _cat("google/gemini-3.1-pro-preview", created=MAR_2026),
    _cat("anthropic/claude-opus-5.5", created=MAR_2026),
]


class NewFamiliesTests(unittest.TestCase):
    def _found(self, rows, roster=None):
        catalog = parse_openrouter_catalog({"data": ROSTER_ROWS + rows})
        return new_families(roster or _family_roster(), catalog)

    def test_flags_a_new_name_from_a_roster_vendor(self):
        found = self._found([_cat("google/gemini-4-argon", created=SEP_2026)])
        self.assertEqual(
            [(f.family, f.newest.id) for f in found],
            [("google/gemini-argon", "google/gemini-4-argon")],
        )

    def test_a_newer_version_of_a_roster_family_is_not_new(self):
        self.assertEqual(self._found([_cat("anthropic/claude-opus-6", created=SEP_2026)]), [])

    def test_the_reviewed_day_is_settled_and_the_next_day_is_not(self):
        settled = _cat("anthropic/claude-fable-5", created=APR_2026 + DAY - 1)
        self.assertEqual(self._found([settled]), [])
        fresh = _cat("anthropic/claude-fable-5", created=APR_2026 + DAY)
        self.assertEqual([f.family for f in self._found([fresh])], ["anthropic/claude-fable"])

    def test_vendors_the_roster_does_not_use_are_ignored(self):
        self.assertEqual(self._found([_cat("deepseek/deepseek-v5", created=SEP_2026)]), [])

    def test_an_entry_missing_from_the_catalog_brings_no_vendor(self):
        ghost = {"key": "grok", "name": "X", "access_method": "openrouter", "id": "x-ai/grok-9"}
        rows = [_cat("x-ai/grok-build-1", created=SEP_2026)]
        self.assertEqual(self._found(rows, _family_roster(extra=[ghost])), [])

    def test_image_output_variants_aliases_and_batch_are_skipped(self):
        rows = [
            _cat("google/gemini-4-argon-image", created=SEP_2026, outputs=["image", "text"]),
            _cat("google/gemma-5-31b-it:free", created=SEP_2026),
            _cat("anthropic/claude-fable-5:batch", created=SEP_2026),
            _cat("anthropic/claude-fable-latest", alias="anthropic/claude-fable-5"),
        ]
        self.assertEqual(self._found(rows), [])

    def test_the_first_listing_dates_the_family_and_the_newest_id_leads(self):
        rows = [
            _cat("google/gemini-2.5-flash", created=MAR_2026),
            _cat("google/gemini-4-flash", created=SEP_2026),
            _cat("google/gemini-4-argon", created=AUG_2026),
            _cat("google/gemini-4.1-argon", created=SEP_2026),
        ]
        found = self._found(rows)
        self.assertEqual(
            [(f.family, f.newest.id) for f in found],
            [("google/gemini-argon", "google/gemini-4.1-argon")],
        )
        self.assertEqual(found[0].listed, AUG_2026)

    def test_format_names_the_family_its_newest_id_and_first_listing(self):
        text = format_new_families(self._found([_cat("google/gemini-4-argon", created=SEP_2026)]))
        self.assertIn("NEW FAMILY", text)
        self.assertIn("google/gemini-4-argon", text)
        self.assertIn("2026-09-21", text)


class MajorJumpTests(unittest.TestCase):
    def _jumps(self, rows):
        catalog = parse_openrouter_catalog({"data": ROSTER_ROWS + rows})
        return {r.entry.key: _newest_id(r) for r in major_jumps(_family_roster(), catalog)}

    def test_a_higher_major_after_the_review_date_is_a_jump(self):
        jumps = self._jumps([_cat("anthropic/claude-opus-6", created=SEP_2026)])
        self.assertEqual(jumps, {"opus": "anthropic/claude-opus-6"})

    def test_a_minor_bump_is_not_a_jump(self):
        self.assertEqual(self._jumps([_cat("anthropic/claude-opus-5.6", created=SEP_2026)]), {})

    def test_a_major_listed_by_the_review_date_is_settled(self):
        settled = _cat("anthropic/claude-opus-6", created=APR_2026 + DAY - 1)
        self.assertEqual(self._jumps([settled]), {})

    def test_the_newest_higher_major_leads_even_when_a_minor_is_newer(self):
        rows = [
            _cat("anthropic/claude-opus-6", created=AUG_2026),
            _cat("anthropic/claude-opus-5.6", created=SEP_2026),
        ]
        self.assertEqual(self._jumps(rows), {"opus": "anthropic/claude-opus-6"})

    def test_a_preview_of_the_next_major_is_a_jump_from_a_final_release(self):
        preview = _cat("anthropic/claude-opus-6-preview", created=SEP_2026)
        self.assertEqual(self._jumps([preview]), {"opus": "anthropic/claude-opus-6-preview"})

    def test_a_preview_of_the_current_major_is_not_a_jump(self):
        preview = _cat("anthropic/claude-opus-5.6-preview", created=SEP_2026)
        self.assertEqual(self._jumps([preview]), {})

    def test_a_preview_entry_jumps_to_the_next_major_preview(self):
        preview = _cat("google/gemini-4-pro-preview", created=SEP_2026)
        self.assertEqual(self._jumps([preview]), {"gem": "google/gemini-4-pro-preview"})


GATE_CATALOG = {
    "data": ROSTER_ROWS
    + [
        _cat("anthropic/claude-opus-6", created=AUG_2026),
        _cat("google/gemini-4-argon", created=SEP_2026),
    ]
}


class CatalogCheckTests(unittest.TestCase):
    NOW = float(SEP_2026 + DAY)

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.cache = catalog_cache_path(b"roster", Path(self._dir.name))
        self.fetches = 0

    def tearDown(self):
        self._dir.cleanup()

    def _fetch(self):
        self.fetches += 1
        return GATE_CATALOG

    def _unreachable(self):
        raise urllib.error.URLError("offline")

    def _check(self, roster, now):
        return catalog_check(roster, self.cache, now, self._fetch)

    def test_cache_is_per_roster_content(self):
        other = catalog_cache_path(b"edited roster", Path(self._dir.name))
        self.assertEqual(other.parent, self.cache.parent)
        self.assertNotEqual(other, self.cache)

    def test_a_cache_under_a_day_old_skips_the_fetch(self):
        _, fetched, _ = load_cached_catalog(self.cache, self.NOW, self._fetch)
        self.assertTrue(fetched)
        catalog, fetched, _ = load_cached_catalog(self.cache, self.NOW + DAY - 1, self._fetch)
        self.assertFalse(fetched)
        self.assertEqual(self.fetches, 1)
        self.assertTrue(catalog)

    def test_a_day_old_cache_is_refetched(self):
        load_cached_catalog(self.cache, self.NOW, self._fetch)
        _, fetched, _ = load_cached_catalog(self.cache, self.NOW + DAY, self._fetch)
        self.assertTrue(fetched)
        self.assertEqual(self.fetches, 2)

    def test_an_unreachable_catalog_keeps_the_stale_cache_and_says_so(self):
        load_cached_catalog(self.cache, self.NOW, self._fetch)
        catalog, fetched, problem = load_cached_catalog(
            self.cache, self.NOW + 2 * DAY, self._unreachable
        )
        self.assertTrue(catalog)
        self.assertFalse(fetched)
        self.assertIn("this uses the copy from 2026-09-22", problem)

    def test_an_unreachable_catalog_with_no_cache_is_reported_not_silent(self):
        catalog, _, problem = load_cached_catalog(self.cache, self.NOW, self._unreachable)
        self.assertIsNone(catalog)
        self.assertIn("none is cached", problem)
        report = catalog_check(_family_roster(), self.cache, self.NOW, self._unreachable)
        self.assertIn("Catalog check problem: could not fetch the catalog (", report)

    def test_a_jump_or_new_family_is_reported_every_run_until_the_date_moves(self):
        for now in (self.NOW, self.NOW + 60):
            with self.subTest(now=now):
                report = self._check(_family_roster(), now)
                self.assertIn("Model catalog review pending", report)
                self.assertIn("Major version jumps:", report)
                self.assertIn("anthropic/claude-opus-6", report)
                self.assertIn("New families:", report)
                self.assertIn("google/gemini-4-argon", report)
                self.assertIn("catalog_reviewed = 2026-04-30", report)
        self.assertEqual(self.fetches, 1)
        settled = _family_roster(reviewed=date(2026, 9, 21))
        self.assertEqual(self._check(settled, self.NOW + 120), "")

    def test_a_flagged_jump_is_not_repeated_in_the_stale_note(self):
        self.assertEqual(self._check(_family_roster(), self.NOW).count("claude-opus-6"), 1)

    def test_stale_entries_are_noted_only_on_the_fetching_run(self):
        roster = _family_roster(reviewed=date(2026, 10, 1))
        first = self._check(roster, self.NOW)
        self.assertNotIn("review pending", first)
        self.assertIn("anthropic/claude-opus-6", first)
        self.assertEqual(self._check(roster, self.NOW + 60), "")


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

    def test_attached_files_are_line_numbered(self):
        prompt = build_pr_prompt("", "", "", [("a.ts", "const a = 1;\n  system: x,")])
        self.assertIn("     1\tconst a = 1;\n     2\t  system: x,\n</file>", prompt)

    def test_no_attached_line_starts_with_a_role_label(self):
        # OpenRouter 403s a prompt holding a line like `system: x`.
        prompt = build_pr_prompt("", "", "", [("a.ts", "system: x")])
        role_label = re.compile(r"^\s*(system|developer|user|assistant|tool)\s*:", re.M)
        self.assertIsNone(role_label.search(prompt))


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
    def test_text_only_reads_output_modalities_and_defaults_true(self):
        rows = [
            _cat("v/text"),
            _cat("v/image", outputs=["image", "text"]),
            _cat("v/t", outputs=["text"]),
        ]
        by_id = {m.id: m.text_only for m in parse_openrouter_catalog({"data": rows})}
        self.assertEqual(by_id, {"v/text": True, "v/image": False, "v/t": True})

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
        self.assertEqual(models[0].max_output, 0)

    def test_max_output_is_the_top_providers_completion_cap(self):
        raw = {"id": "x/y", "top_provider": {"max_completion_tokens": 128000}}
        model = parse_openrouter_catalog({"data": [raw]})[0]
        self.assertEqual(model.max_output, 128_000)
        self.assertIn("128K", format_catalog([model]))

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
