#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["openrouter"]
# ///
"""
agent_code_reviewer.py — Config-driven second-opinion code reviewer

Used by Claude as a collaboration tool to get architecture reviews, edge case
audits, and second opinions from another model. Claude is the sole code writer —
the reviewer provides feedback only.

The available models are data, not code: they live in the roster at
`cli/agent_reviewer.toml` next to this script. Each entry declares a `key`
(passed to --model), an `access_method` (which API to speak), and an `id` (the
model identifier that API expects). Add a model by editing the roster; adding a
new *access method* is the only change that needs Python.

  uv run cli/agent_code_reviewer.py --list        # resolved roster + key status

Setup:
  Only the access methods you actually use need a key.
    openrouter  OPENROUTER_API_KEY
                https://openrouter.ai/keys
    gemini_api  GEMINI_API_KEY
                https://aistudio.google.com/api-keys → create a Tier 1 key
                (free-tier rate limits are too low for PR review)
    openai_api  OPENAI_API_KEY
                https://platform.openai.com/api-keys

PR Review Mode (--pr):
  Fetches the PR diff via `gh`, sends it to the selected model for line-level
  review, and posts comments directly on the PR as inline review comments.
  Each comment is prefixed with the entry's attribution tag, e.g. **[GEMINI]**.

    uv run cli/agent_code_reviewer.py --pr 60
    uv run cli/agent_code_reviewer.py --model codex --pr 60

Conversation History:
  - One file per roster entry: /tmp/agent_reviewer_<key>.json
  - Persists across invocations; cleared on system reboot or via --reset.
  - --history prints the selected entry's history as formatted JSON.
  - TTL-pruned (default 30 min, --ttl 0 disables) and optionally scoped to a
    --session id. A session mismatch discards the whole file rather than
    replaying a prior run's diff into an unrelated call.

Usage:
  uv run cli/agent_code_reviewer.py "Your question here"
  uv run cli/agent_code_reviewer.py --model codex "Same question via Codex"
  uv run cli/agent_code_reviewer.py --file path/to/file.ts "Review this code"
  uv run cli/agent_code_reviewer.py --pr 60 "Focus on error handling"
  uv run cli/agent_code_reviewer.py --model grok --pr 60
  uv run cli/agent_code_reviewer.py --reset "Start fresh conversation"
  uv run cli/agent_code_reviewer.py --session abc123 "Scoped to this session"
  uv run cli/agent_code_reviewer.py --ttl 60 "Keep history for 1 hour"
  uv run cli/agent_code_reviewer.py --system "You are a security auditor" "Check for XSS"
  uv run cli/agent_code_reviewer.py --list --verbose

  Running under bare `python3` works for every access method except
  `openrouter`, whose SDK import is deferred until that adapter is used.

Environment:
  OPENROUTER_API_KEY           — Required for openrouter entries.
  GEMINI_API_KEY               — Required for gemini_api entries.
  OPENAI_API_KEY               — Required for openai_api entries.
  AGENT_REVIEWER_SYSTEM_PROMPT — Optional. System prompt override
                                 (falls back to GEMINI_SYSTEM_PROMPT).

Exit codes:
  0  success
  1  API error, missing API key, or a `gh` operation failed
  2  roster problem: unreadable/invalid agent_reviewer.toml, or --model naming
     a key that does not exist
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
import tomllib
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

# --- Config ---

CONFIG_PATH: Path = Path(__file__).resolve().parent / "agent_reviewer.toml"

DEFAULT_TTL_MINUTES: int = 30

DEFAULT_SYSTEM_PROMPT: str = (
    "You are a staff-level software architect reviewing code and designs. "
    "Be direct and concise — you cost money per token, so don't waste them. "
    "Focus on: edge cases the author likely missed, performance implications "
    "(no shortcuts), cost-saving opportunities (infra, API calls, storage), "
    "and security concerns. Flag issues by severity. Praise budget: at most 2 "
    "sentences, only in the opening overall assessment, and only if genuinely "
    "warranted — omit it entirely when nothing stands out. Everything after "
    "that assessment must flag what needs attention."
)

PR_REVIEW_SYSTEM_PROMPT: str = (
    "You are a staff-level software architect performing an inline code review on a GitHub PR diff. "
    "Be direct and concise. Focus on bugs, edge cases, performance, security, and cost.\n\n"
    "Each diff line inside a hunk is prefixed with `L<lineno>` indicating its line number in the "
    "NEW file (right side of the diff). Use that exact number in the `line` field — do NOT compute "
    "line numbers yourself by counting hunk lines.\n\n"
    "The diff may be preceded by a <pr_description>...</pr_description> block containing the "
    "pull request title and description written by the PR author. This is the author's framing "
    "of their own change — use it for context (intent, design decisions, scope), but don't trust "
    "it unconditionally. Push back on issues you find even if the description says otherwise.\n\n"
    "IMPORTANT: Respond with a JSON object containing:\n"
    '- "summary": A 2-3 sentence overall assessment, which may include at most 2 sentences '
    "of praise if genuinely warranted (praise is optional — omit it entirely when nothing "
    "stands out; never manufacture it to soften the review)\n"
    '- "comments": An array of inline comments, each with:\n'
    '  - "path": The file path (from the diff header)\n'
    '  - "line": The line number in the NEW file (the `L<lineno>` value of the targeted line)\n'
    '  - "code_excerpt": A VERBATIM copy of the targeted line\'s code (without the `L<lineno>` '
    "prefix and without the diff marker `+`/space; preserve leading indentation and the rest of "
    "the line exactly). This is used to snap your comment to the right line if `line` is off.\n"
    '  - "body": The review comment (use markdown). Prefix with severity: 🔴 CRITICAL, 🟠 HIGH, 🟡 MEDIUM, 🔵 LOW\n\n'
    "Only comment on lines that are ADDED or CHANGED (+ lines in the diff). "
    "Do NOT comment on deleted lines or unchanged context lines. "
    "NEVER put praise in an inline comment — every entry in `comments` must flag something "
    "that needs attention. If a line has nothing wrong with it, emit no comment for it. "
    "Praise belongs only in `summary`, capped at 2 sentences. "
    "Return ONLY valid JSON, no markdown fences."
)

# Diff hunks for these paths are dropped from PR review input. Plans / specs
# under docs/superpowers are agentic-coding scratch material — committing them
# is fine for record-keeping, but they're never code-relevant for review and
# would otherwise waste tokens (and crowd out the real diff).
DEFAULT_IGNORE_PATHS: list[str] = [
    "docs/superpowers/",
]


# ---------------------------------------------------------------------------
# Roster
# ---------------------------------------------------------------------------
#
# The set of reviewable models is data, loaded from agent_reviewer.toml. An
# entry's `access_method` IS its wire protocol — `id` alone cannot tell the
# script whether to speak Gemini's generateContent or OpenAI's Responses API,
# and inferring it from the model id would break the first time a vendor
# renames a family.

ACCESS_METHODS: tuple[str, ...] = ("openrouter", "gemini_api", "openai_api")

REQUIRED_FIELDS: tuple[str, ...] = ("key", "name", "access_method", "id")
OPTIONAL_FIELDS: tuple[str, ...] = ("tag", "store")


class ConfigError(Exception):
    """Roster missing, unreadable, or invalid. main() exits 2 on these."""


@dataclass(frozen=True)
class ModelEntry:
    """One [[models]] table from the roster."""

    key: str
    name: str
    access_method: str
    id: str
    tag: str
    store: bool = False


@dataclass(frozen=True)
class Roster:
    entries: list[ModelEntry]
    default_key: str

    def get(self, key: str) -> ModelEntry:
        for entry in self.entries:
            if entry.key == key:
                return entry
        valid = ", ".join(e.key for e in self.entries)
        raise ConfigError(f"unknown model {key!r}; valid keys: {valid}")

    def default_entry(self) -> ModelEntry:
        return self.get(self.default_key)


def parse_config(raw: dict) -> Roster:
    """Validate a parsed roster. Pure — takes the toml dict, not a path.

    Strict on purpose: this file is hand-edited, and a silently-ignored typo
    (`tags = "GEMINI"`) would surface much later as a wrong PR comment."""
    default = raw.get("default")
    if not isinstance(default, str) or not default:
        raise ConfigError("roster needs a top-level `default = \"<key>\"`")

    models = raw.get("models")
    if not isinstance(models, list) or not models:
        raise ConfigError("roster needs at least one [[models]] entry")

    entries: list[ModelEntry] = []
    seen: set[str] = set()
    for i, model in enumerate(models):
        where = f"[[models]] #{i + 1}"
        if not isinstance(model, dict):
            raise ConfigError(f"{where}: not a table")

        for field in REQUIRED_FIELDS:
            value = model.get(field)
            if not isinstance(value, str) or not value:
                raise ConfigError(f"{where}: missing or empty required field `{field}`")

        unknown = set(model) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS)
        if unknown:
            allowed = ", ".join(REQUIRED_FIELDS + OPTIONAL_FIELDS)
            raise ConfigError(
                f"{where}: unknown field(s) {', '.join(sorted(unknown))}; allowed: {allowed}"
            )

        key = model["key"]
        if key in seen:
            raise ConfigError(f"{where}: duplicate key {key!r}")
        seen.add(key)

        access_method = model["access_method"]
        if access_method not in ACCESS_METHODS:
            raise ConfigError(
                f"{where}: unknown access_method {access_method!r}; "
                f"expected one of {', '.join(ACCESS_METHODS)}"
            )

        tag = model.get("tag", key.upper())
        if not isinstance(tag, str) or not tag:
            raise ConfigError(f"{where}: `tag` must be a non-empty string")

        store = model.get("store", False)
        if not isinstance(store, bool):
            raise ConfigError(f"{where}: `store` must be a boolean")
        if store and access_method != "openai_api":
            raise ConfigError(
                f"{where}: `store` is only valid on openai_api entries "
                f"(this one is {access_method})"
            )

        entries.append(
            ModelEntry(
                key=key,
                name=model["name"],
                access_method=access_method,
                id=model["id"],
                tag=tag,
                store=store,
            )
        )

    if default not in seen:
        raise ConfigError(
            f"default {default!r} matches no entry; valid keys: {', '.join(sorted(seen))}"
        )
    return Roster(entries=entries, default_key=default)


def load_config(path: Path = CONFIG_PATH) -> Roster:
    try:
        raw = tomllib.loads(path.read_text())
    except FileNotFoundError:
        raise ConfigError(f"roster not found: {path}") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: invalid TOML: {exc}") from None
    return parse_config(raw)


def format_roster(roster: Roster, verbose: bool = False) -> str:
    """--list output: what is available and what is actually usable today."""
    rows = []
    for entry in roster.entries:
        adapter = make_adapter(entry)
        marker = "*" if entry.key == roster.default_key else " "
        row = [
            f"{entry.key}{marker}",
            entry.access_method,
            entry.id,
            "set" if adapter.api_key() else f"MISSING {adapter.api_key_env_var()}",
        ]
        if verbose:
            row.insert(1, entry.name)
            row.append(f"[{entry.tag}]")
        rows.append(row)

    headers = ["KEY", "ACCESS", "ID", "API KEY"]
    if verbose:
        headers.insert(1, "NAME")
        headers.append("TAG")
    widths = [max(len(r[i]) for r in [headers] + rows) for i in range(len(headers))]
    lines = ["  ".join(h.ljust(w) for h, w in zip(headers, widths)).rstrip()]
    lines += ["  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip() for r in rows]
    lines.append("")
    lines.append("* = default")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Access-method adapters
# ---------------------------------------------------------------------------
#
# Each adapter owns its message format, API endpoint, and response parsing for
# one access method. The only shared surface is what main() needs to run a
# turn-and-save cycle. History-file layout is shared: one file per roster entry.


class Adapter(ABC):
    """Strategy interface for one access method, bound to one roster entry."""

    def __init__(self, entry: ModelEntry) -> None:
        self.entry = entry

    @abstractmethod
    def api_key(self) -> str | None:
        """Configured key, or None if unset. main() does the fail-fast check."""

    @abstractmethod
    def api_key_env_var(self) -> str:
        """Env var name holding this access method's key (for error messages)."""

    @abstractmethod
    def add_message(
        self, history: list[dict], role: str, text: str, signature: str = ""
    ) -> list[dict]: ...

    @abstractmethod
    def build_request(self, system_prompt: str, history: list[dict]) -> dict: ...

    @abstractmethod
    def call_api(self, request_body: dict) -> dict: ...

    @abstractmethod
    def extract_response(self, data: dict) -> tuple[str, str]:
        """Returns (visible_text, opaque_signature). Signature is access-method
        specific and threaded back into the next turn's history record."""

    # Shared history-file ops. The on-disk shape is the same everywhere
    # (entries list + session + per-entry timestamps); only the per-entry
    # `message` payload is access-method-flavored. Scoped by roster key so
    # switching models never replays another model's conversation.

    def history_file(self) -> Path:
        return Path(f"/tmp/agent_reviewer_{self.entry.key}.json")

    def load_history_raw(self) -> dict:
        hf = self.history_file()
        if hf.exists():
            try:
                return json.loads(hf.read_text())
            except json.JSONDecodeError:
                return {}
        return {}

    def load_history(
        self, session: str | None = None, ttl_minutes: int = DEFAULT_TTL_MINUTES
    ) -> list[dict]:
        raw = self.load_history_raw()
        # Clear on any session mismatch, including the case where the caller
        # omits --session but the saved history was scoped to one. Without
        # this, a prior `--session abc` run's entries (a diff, a prompt) would
        # silently replay into the next un-scoped call and leak back out.
        if raw.get("session") != session:
            return []
        entries: list[dict] = raw.get("entries", [])
        if ttl_minutes > 0:
            cutoff = time.time() - (ttl_minutes * 60)
            entries = [e for e in entries if e.get("timestamp", 0) >= cutoff]
        return [e["message"] for e in entries]

    def save_history(
        self,
        history_messages: list[dict],
        session: str | None = None,
        timestamps: list[float] | None = None,
    ) -> None:
        now = time.time()
        entries = []
        for i, msg in enumerate(history_messages):
            ts = timestamps[i] if timestamps and i < len(timestamps) else now
            entries.append({"timestamp": ts, "message": msg})
        data: dict = {"entries": entries}
        if session:
            data["session"] = session
        self.history_file().write_text(json.dumps(data))

    def reset_history(self) -> None:
        self.history_file().write_text(json.dumps({}))


class GeminiAdapter(Adapter):
    """Google Gemini generateContent API."""

    def api_key(self) -> str | None:
        return os.environ.get("GEMINI_API_KEY") or None

    def api_key_env_var(self) -> str:
        return "GEMINI_API_KEY"

    def add_message(
        self, history: list[dict], role: str, text: str, signature: str = ""
    ) -> list[dict]:
        part: dict = {"text": text}
        if signature:
            part["thoughtSignature"] = signature
        history.append({"role": role, "parts": [part]})
        return history

    def build_request(self, system_prompt: str, history: list[dict]) -> dict:
        return {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": history,
        }

    def call_api(self, request_body: dict) -> dict:
        key = self.api_key()
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.entry.id}"
            f":generateContent?key={key}"
        )
        data = json.dumps(request_body).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read())

    def extract_response(self, data: dict) -> tuple[str, str]:
        if data.get("error"):
            msg = data["error"].get("message", "unknown error")
            print(f"API Error: {msg[:200]}", file=sys.stderr)
            sys.exit(1)
        candidate = data.get("candidates", [{}])[0]
        parts = candidate.get("content", {}).get("parts", [{}])
        text = "".join(p.get("text", "") for p in parts)
        signature = parts[0].get("thoughtSignature", "") if parts else ""
        return text, signature


class OpenAIAdapter(Adapter):
    """OpenAI Responses API.

    Default mode is **stateless**: each call sets `store: false`, so no
    prompt/diff/file payload is persisted on OpenAI's side. This matches
    the Gemini path's privacy model and is the right default for `--pr`
    reviews, where the diff often contains private source.

    Opt-in stateful chaining: set `store = true` on the roster entry.
    With that, each session becomes a chain of `previous_response_id`
    references the server maintains, and only the last response id is
    persisted locally. Useful for `--session <id>` multi-turn work where
    the cost of re-sending the full transcript every turn is high enough
    to justify the server-side retention trade-off.

    Local-store entries are kept for `--history` display + TTL bookkeeping
    regardless of mode."""

    def __init__(self, entry: ModelEntry) -> None:
        super().__init__(entry)
        # Populated by load_history(); read by build_request().
        self._last_response_id: str | None = None

    def api_key(self) -> str | None:
        return os.environ.get("OPENAI_API_KEY") or None

    def api_key_env_var(self) -> str:
        return "OPENAI_API_KEY"

    def load_history(
        self, session: str | None = None, ttl_minutes: int = DEFAULT_TTL_MINUTES
    ) -> list[dict]:
        # Side effect: capture the most recent assistant message's response_id
        # so build_request() can pass it as previous_response_id. main() uses
        # the Gemini-flavored role name "model" for assistant turns, so accept
        # either spelling here rather than forcing a callsite normalization.
        history = super().load_history(session=session, ttl_minutes=ttl_minutes)
        self._last_response_id = None
        for msg in reversed(history):
            if msg.get("role") in ("assistant", "model") and msg.get("response_id"):
                self._last_response_id = msg["response_id"]
                break
        return history

    def add_message(
        self, history: list[dict], role: str, text: str, signature: str = ""
    ) -> list[dict]:
        # OpenAI's message shape is {role, content[]}, but we only persist the
        # bits we need: role, visible text, and (for assistant messages) the
        # response id we'll thread into the next turn's previous_response_id.
        msg: dict = {"role": role, "text": text}
        if signature:
            msg["response_id"] = signature
        history.append(msg)
        return history

    def build_request(self, system_prompt: str, history: list[dict]) -> dict:
        # Two modes:
        #
        # 1. Stateless (default, store = false): replay the full local history
        #    as `input[]` each turn — same shape Gemini uses. OpenAI does not
        #    retain anything. --session multi-turn context is preserved
        #    client-side in the entry's history file.
        #
        # 2. Stateful (opt-in, store = true): send only the latest user
        #    message + `previous_response_id`; the server walks the chain it
        #    retained. Cheaper per-turn (no transcript re-send) at the cost
        #    of server-side retention of all prior payloads.
        store = self.entry.store
        body: dict = {
            "instructions": system_prompt,
            "store": store,
        }
        if store:
            latest_user = ""
            for msg in reversed(history):
                if msg.get("role") == "user":
                    latest_user = msg.get("text", "")
                    break
            body["input"] = latest_user
            if self._last_response_id:
                body["previous_response_id"] = self._last_response_id
        else:
            # Map our local role names ("model" is the Gemini-flavored
            # assistant tag also used by main()) to OpenAI's vocabulary.
            def to_openai_role(role: str) -> str:
                return "assistant" if role == "model" else role

            body["input"] = [
                {"role": to_openai_role(msg["role"]), "content": msg.get("text", "")}
                for msg in history
                if msg.get("role") in ("user", "assistant", "model")
            ]
        return body

    def call_api(self, request_body: dict) -> dict:
        key = self.api_key()
        url = "https://api.openai.com/v1/responses"
        body = dict(request_body)
        body["model"] = self.entry.id
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read())

    def extract_response(self, data: dict) -> tuple[str, str]:
        # OpenAI returns `"error": null` on success; only treat truthy as a failure.
        if data.get("error"):
            msg = data["error"].get("message", "unknown error")
            print(f"API Error: {msg[:200]}", file=sys.stderr)
            sys.exit(1)
        # `output_text` is the convenience flattener; fall back to walking
        # output[].content[].text for older payload shapes.
        text = data.get("output_text", "")
        if not text:
            for item in data.get("output", []) or []:
                for content in item.get("content", []) or []:
                    if isinstance(content, dict) and "text" in content:
                        text += content["text"]
        response_id = data.get("id", "")
        return text, response_id


class OpenRouterAdapter(Adapter):
    """OpenRouter, via the `openrouter` SDK.

    Stateless: OpenRouter has no server-side conversation chaining, so the
    full local transcript is replayed as `messages` every turn — the same
    shape the OpenAI adapter uses in its default mode. No signature is
    threaded back, so multi-turn history is purely client-side."""

    def api_key(self) -> str | None:
        return os.environ.get("OPENROUTER_API_KEY") or None

    def api_key_env_var(self) -> str:
        return "OPENROUTER_API_KEY"

    def add_message(
        self, history: list[dict], role: str, text: str, signature: str = ""
    ) -> list[dict]:
        history.append({"role": role, "text": text})
        return history

    def build_request(self, system_prompt: str, history: list[dict]) -> dict:
        def to_chat_role(role: str) -> str:
            return "assistant" if role == "model" else role

        messages = [{"role": "system", "content": system_prompt}]
        messages += [
            {"role": to_chat_role(msg["role"]), "content": msg.get("text", "")}
            for msg in history
            if msg.get("role") in ("user", "assistant", "model")
        ]
        return {"messages": messages}

    def call_api(self, request_body: dict) -> dict:
        # Deferred import: the SDK is declared in this script's PEP 723 header,
        # but the two direct adapters must keep working under a bare `python3`
        # with nothing installed.
        try:
            from openrouter import OpenRouter
        except ImportError:
            print(
                "Error: the openrouter access method needs the SDK. Run this "
                "script with `uv run` (which installs it from the PEP 723 "
                "header), or `pip install openrouter`.",
                file=sys.stderr,
            )
            sys.exit(1)

        # timeout_ms matches the 300s the urllib adapters pass to urlopen.
        with OpenRouter(api_key=self.api_key(), timeout_ms=300_000) as client:
            response = client.chat.send(
                model=self.entry.id, messages=request_body["messages"]
            )
        return {"text": response.choices[0].message.content or ""}

    def extract_response(self, data: dict) -> tuple[str, str]:
        return data.get("text", ""), ""


ADAPTERS: dict[str, type[Adapter]] = {
    "openrouter": OpenRouterAdapter,
    "gemini_api": GeminiAdapter,
    "openai_api": OpenAIAdapter,
}


def make_adapter(entry: ModelEntry) -> Adapter:
    try:
        return ADAPTERS[entry.access_method](entry)
    except KeyError:
        # parse_config validates the enum, so reaching here means a new
        # access_method was added to ACCESS_METHODS without an adapter.
        raise ConfigError(
            f"no adapter registered for access_method {entry.access_method!r}"
        ) from None


# ---------------------------------------------------------------------------
# PR Review Mode
# ---------------------------------------------------------------------------


def get_pr_diff(pr_number: str) -> str:
    """Fetch PR diff using gh CLI."""
    result = subprocess.run(
        ["gh", "pr", "diff", pr_number],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error fetching PR diff: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def _path_matches_any(path: str, patterns: list[str]) -> bool:
    """True if `path` matches any of `patterns`. Trailing-slash patterns are
    treated as directory prefixes; everything else as fnmatch globs."""
    for pat in patterns:
        if pat.endswith("/"):
            if path.startswith(pat):
                return True
        elif fnmatch.fnmatch(path, pat):
            return True
    return False


def filter_diff(diff: str, ignore_paths: list[str]) -> tuple[str, list[str]]:
    """Drop unified-diff blocks whose file paths match any ignore pattern.

    Returns the filtered diff plus the list of paths that were dropped (for
    logging — so users can see what got skipped).
    """
    if not ignore_paths or not diff:
        return diff, []
    # Split on file boundaries while keeping each `diff --git` header attached
    # to its own block. The first split element is anything before the first
    # block (usually empty); the rest are full file blocks.
    blocks = re.split(r"^(?=diff --git )", diff, flags=re.MULTILINE)
    kept: list[str] = []
    dropped: list[str] = []
    for block in blocks:
        if not block.strip():
            kept.append(block)
            continue
        match = re.match(r"diff --git a/(\S+) b/(\S+)", block)
        if not match:
            kept.append(block)  # malformed — keep so we don't silently drop content
            continue
        path_a, path_b = match.group(1), match.group(2)
        if _path_matches_any(path_a, ignore_paths) or _path_matches_any(path_b, ignore_paths):
            dropped.append(path_b)
            continue
        kept.append(block)
    return "".join(kept), dropped


def get_pr_info(pr_number: str) -> dict:
    """Fetch PR title and body using gh CLI."""
    result = subprocess.run(
        ["gh", "pr", "view", pr_number, "--json", "title,body,headRefOid"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error fetching PR info: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def _parse_diff_anchorable_lines(diff: str) -> dict[str, set[int]]:
    """Return {path: set of new-file line numbers eligible for RIGHT-side
    inline review comments} for a unified diff.

    GitHub's PR review API rejects (422) any inline comment whose line
    isn't inside a hunk on the side it targets. LLM reviewers regularly
    hallucinate line numbers — off-the-end of files, on pure-deletion
    lines, in unchanged regions. We pre-validate against this map and
    bucket invalid anchors into the review body instead of losing them
    to a 422.

    RIGHT-side eligibility: lines that exist in the new file inside a
    hunk — i.e. additions ('+') and context (' '). Pure deletions ('-')
    are LEFT-side only.
    """
    result: dict[str, set[int]] = {}
    current_path: str | None = None
    current_new_line = 0
    in_hunk = False
    for raw in diff.splitlines():
        m = re.match(r"^diff --git a/\S+ b/(\S+)", raw)
        if m:
            current_path = m.group(1)
            result.setdefault(current_path, set())
            in_hunk = False
            continue
        if current_path is None:
            continue
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
        if m:
            current_new_line = int(m.group(1))
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            result[current_path].add(current_new_line)
            current_new_line += 1
        elif raw.startswith(" "):
            result[current_path].add(current_new_line)
            current_new_line += 1
        # '-' lines: no new-file advance. Other lines ('\\ No newline...'): skip.
    return result


def annotate_diff_with_line_numbers(diff: str) -> str:
    """Prefix every in-hunk new-file line with `L<lineno> ` so the reviewing
    model can read line numbers directly off each line instead of counting
    hunk offsets (which it gets wrong).

    Additions (`+`) and context (` `) get the prefix using their new-file
    line number. Deletions (`-`) and other lines (headers, hunk markers,
    `\\ No newline...`) pass through unchanged.
    """
    out: list[str] = []
    current_new_line = 0
    in_hunk = False
    for raw in diff.splitlines():
        if re.match(r"^diff --git a/\S+ b/(\S+)", raw):
            in_hunk = False
            out.append(raw)
            continue
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
        if m:
            current_new_line = int(m.group(1))
            in_hunk = True
            out.append(raw)
            continue
        if not in_hunk:
            out.append(raw)
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            out.append(f"L{current_new_line} {raw}")
            current_new_line += 1
        elif raw.startswith(" "):
            out.append(f"L{current_new_line} {raw}")
            current_new_line += 1
        else:
            out.append(raw)
    return "\n".join(out)


def _build_line_content_index(diff: str) -> dict[str, dict[str, list[int]]]:
    """Map `{path: {line_content: [new_file_line_numbers]}}` for RIGHT-side
    lines (additions + context). Used by `post_pr_review` to snap a comment's
    `line` to the actual file line by matching the model-provided
    `code_excerpt` against this index.

    `line_content` is the verbatim text after the diff marker — for `+ foo`
    we index `"foo"`; for ` foo` (context) we also index `"foo"`. Deletions
    are not indexed (LEFT-side only)."""
    result: dict[str, dict[str, list[int]]] = {}
    current_path: str | None = None
    current_new_line = 0
    in_hunk = False
    for raw in diff.splitlines():
        m = re.match(r"^diff --git a/\S+ b/(\S+)", raw)
        if m:
            current_path = m.group(1)
            result.setdefault(current_path, {})
            in_hunk = False
            continue
        if current_path is None:
            continue
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
        if m:
            current_new_line = int(m.group(1))
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            content = raw[1:]
            result[current_path].setdefault(content, []).append(current_new_line)
            current_new_line += 1
        elif raw.startswith(" "):
            content = raw[1:]
            result[current_path].setdefault(content, []).append(current_new_line)
            current_new_line += 1
    return result


def post_pr_review(
    pr_number: str,
    summary: str,
    comments: list[dict],
    attribution: str,
    diff: str = "",
) -> None:
    """Post a review with inline comments on the PR using gh API. The
    `attribution` tag (the roster entry's `tag`, e.g. "GEMINI") prefixes every
    comment + the review body so reviewers can tell at a glance which model
    authored each.

    Comments whose (path, line) pair isn't a valid RIGHT-side anchor in the
    PR diff get bucketed into the review body's "Additional comments"
    section instead of being submitted as inline (which would 422). The
    `diff` argument is the unified diff used to compute anchor eligibility;
    pass the full pre-truncation diff so anchor validation matches what
    GitHub sees, not what the model saw."""
    pr_info = get_pr_info(pr_number)
    commit_id = pr_info.get("headRefOid", "")

    if not diff and comments:
        # Caller forgot to thread the diff through. Every comment will be
        # bucketed to the body, which is correct-but-degraded — warn so the
        # regression is visible instead of silently losing all inline anchors.
        print(
            f"Warning: post_pr_review called without diff but with {len(comments)} "
            "comment(s); all will be posted in body, none inline",
            file=sys.stderr,
        )
    anchorable = _parse_diff_anchorable_lines(diff) if diff else {}
    content_index = _build_line_content_index(diff) if diff else {}

    valid_inline: list[dict] = []
    invalid_fallback: list[dict] = []
    for c in comments:
        line = c.get("line")
        path = c.get("path", "")
        # Snap to excerpt: if the model returned a code_excerpt that appears
        # exactly once in the file's anchorable lines, trust the excerpt over
        # the (often-miscounted) line number. Models reliably copy text more
        # accurately than they count hunk offsets.
        excerpt = c.get("code_excerpt")
        if excerpt and path in content_index:
            matches = content_index[path].get(excerpt, [])
            if len(matches) == 1:
                snapped = matches[0]
                if snapped != line:
                    print(
                        f"  snapped {path}: line {line} -> {snapped} via code_excerpt",
                        file=sys.stderr,
                    )
                    c["line"] = snapped
                    line = snapped
        if line and path in anchorable and line in anchorable[path]:
            valid_inline.append(c)
        else:
            invalid_fallback.append(c)

    body_parts = [f"## [{attribution}] Code Review", "", summary]
    if invalid_fallback:
        body_parts += [
            "",
            "### Additional comments",
            "",
            "_These anchors fell outside the diff (off-the-end line numbers, "
            "unchanged regions, or LEFT-side-only lines) so GitHub would have "
            "rejected them as inline. Posted here instead so nothing is lost._",
            "",
        ]
        for c in invalid_fallback:
            line_str = f" (line {c['line']})" if c.get("line") else ""
            body_parts.append(f"**{c['path']}**{line_str}")
            if c.get("code_excerpt"):
                body_parts.append(f"> `{c['code_excerpt']}`")
            body_parts.append(c["body"])
            body_parts.append("")
    body = "\n".join(body_parts)

    review_comments = [
        {
            "path": c["path"],
            "body": f"**[{attribution}]** {c['body']}",
            "line": c["line"],
            "side": "RIGHT",
        }
        for c in valid_inline
    ]

    payload = {
        "commit_id": commit_id,
        "body": body,
        "event": "COMMENT",
        "comments": review_comments,
    }

    result = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/reviews",
            "--method",
            "POST",
            "--input",
            "-",
        ],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        # Defensive fallback for unexpected failures (network, auth, malformed
        # JSON, etc.). Inline-anchor 422s are already handled above by
        # bucketing invalids — this path shouldn't normally fire.
        print("Warning: review POST failed, retrying as body-only", file=sys.stderr)
        print(f"  gh error: {result.stderr[:200]}", file=sys.stderr)
        fallback_body = f"## [{attribution}] Code Review\n\n{summary}\n\n"
        for c in comments:
            fallback_body += f"**{c['path']}**"
            if c.get("line"):
                fallback_body += f" (line {c['line']})"
            fallback_body += f"\n{c['body']}\n\n"

        retry = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/reviews",
                "--method",
                "POST",
                "--input",
                "-",
            ],
            input=json.dumps({
                "commit_id": commit_id,
                "body": fallback_body,
                "event": "COMMENT",
                "comments": [],
            }),
            capture_output=True,
            text=True,
        )
        if retry.returncode != 0:
            # Both POSTs failed — surface the second error and exit non-zero so
            # the caller doesn't see misleading green output.
            print("Error: body-only retry also failed", file=sys.stderr)
            print(f"  gh error: {retry.stderr[:500]}", file=sys.stderr)
            sys.exit(1)
        print("Posted review as summary comment (no inline comments)", file=sys.stderr)
    else:
        print(
            f"Posted review: {len(valid_inline)} inline, "
            f"{len(invalid_fallback)} bucketed to summary",
            file=sys.stderr,
        )


def review_pr(
    pr_number: str,
    adapter: Adapter,
    extra_instructions: str = "",
    ignore_paths: list[str] | None = None,
) -> None:
    """Full PR review flow: fetch diff → filter ignored paths → review → post."""
    print(
        f"--> Reviewing PR #{pr_number} with {adapter.entry.name} ({adapter.entry.id})",
        file=sys.stderr,
    )

    diff = get_pr_diff(pr_number)
    if not diff.strip():
        print("PR diff is empty.", file=sys.stderr)
        return

    diff, dropped = filter_diff(diff, ignore_paths or [])
    if dropped:
        print(
            f"--> Skipped {len(dropped)} file(s) per ignore patterns: "
            + ", ".join(dropped[:5])
            + ("..." if len(dropped) > 5 else ""),
            file=sys.stderr,
        )

    # If every changed file was filtered out (docs-only PR, all snapshots, etc.),
    # exit cleanly. Sending an empty diff to the model would produce hallucinated
    # comments about content we explicitly meant to skip.
    if not diff.strip():
        print(
            f"--> Nothing to review: all {len(dropped)} changed file(s) match ignore patterns.",
            file=sys.stderr,
        )
        return

    # Capture full filtered diff for anchor validation before truncation —
    # GitHub validates against the real diff, not what we sent the model.
    full_diff_for_anchors = diff

    # Truncate very large diffs to stay within token limits
    max_diff_chars = 100_000  # ~25K tokens
    if len(diff) > max_diff_chars:
        diff = diff[:max_diff_chars] + "\n\n... [diff truncated] ..."
        print(f"--> Diff truncated to {max_diff_chars} chars", file=sys.stderr)

    annotated_diff = annotate_diff_with_line_numbers(diff)

    # Give the reviewer the author's framing (intent, scope, design choices)
    # alongside the diff. System prompt tells the model to treat it as the
    # author's view, not ground truth.
    pr_info = get_pr_info(pr_number)
    pr_title = pr_info.get("title", "").strip()
    pr_body = pr_info.get("body", "").strip()
    context_block = ""
    if pr_title or pr_body:
        context_block = (
            "<pr_description>\n"
            f"Title: {pr_title}\n\n"
            f"{pr_body}\n"
            "</pr_description>\n\n"
        )

    prompt = f"{context_block}Review this PR diff:\n\n```diff\n{annotated_diff}\n```"
    if extra_instructions:
        prompt = f"{extra_instructions}\n\n{prompt}"

    # Single-turn review — no persisted history.
    history: list[dict] = []
    history = adapter.add_message(history, "user", prompt)
    request_body = adapter.build_request(PR_REVIEW_SYSTEM_PROMPT, history)
    response_data = adapter.call_api(request_body)
    text, _ = adapter.extract_response(response_data)

    # Parse JSON response
    try:
        # Strip markdown fences if present
        clean = text.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1]
        if clean.endswith("```"):
            clean = clean.rsplit("```", 1)[0]
        review = json.loads(clean.strip())
    except json.JSONDecodeError:
        print("Response not valid JSON, posting as summary:", file=sys.stderr)
        print(text, file=sys.stderr)
        # Post raw text as review body
        post_pr_review(pr_number, text, [], attribution=adapter.entry.tag)
        return

    summary = review.get("summary", "No summary provided.")
    comments = review.get("comments", [])

    print(f"\n{summary}\n", file=sys.stderr)
    print(f"  {len(comments)} inline comment(s)", file=sys.stderr)

    # Post to GitHub — pass full pre-truncation diff so anchor validation
    # matches what GitHub sees, not what the model saw.
    post_pr_review(
        pr_number,
        summary,
        comments,
        attribution=adapter.entry.tag,
        diff=full_diff_for_anchors,
    )
    print(f"--> Review posted to PR #{pr_number}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Config-driven second-opinion code reviewer. "
        f"Models are declared in {CONFIG_PATH.name} next to this script; "
        "run --list to see them."
    )
    parser.add_argument("message", nargs="?", default="", help="Message to send")
    parser.add_argument(
        "--model",
        dest="model_key",
        default="",
        metavar="KEY",
        help="Roster key of the model to use (default: the roster's `default`). See --list.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List the roster (key, access method, model id, whether its API key is set) and exit.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="With --list, also show each entry's full name and attribution tag.",
    )
    parser.add_argument("--file", dest="file_path", default="", help="Attach file content")
    parser.add_argument(
        "--system", dest="system_prompt", default="", help="Override system prompt"
    )
    parser.add_argument("--pr", dest="pr_number", default="", help="Review a GitHub PR by number")
    parser.add_argument(
        "--ignore-path",
        dest="ignore_paths",
        action="append",
        default=[],
        metavar="PATTERN",
        help=(
            "Skip files matching PATTERN when reviewing a PR. Trailing-slash "
            "patterns match a directory prefix (e.g. 'docs/'); other patterns "
            "use fnmatch globs (e.g. '*.snap'). Repeatable. Combined with the "
            f"hardcoded defaults: {', '.join(DEFAULT_IGNORE_PATHS)}."
        ),
    )
    parser.add_argument("--session", dest="session", default="", help="Session ID to scope history (e.g. a UUID per conversation)")
    parser.add_argument("--ttl", dest="ttl_minutes", type=int, default=DEFAULT_TTL_MINUTES, help=f"Prune history older than N minutes (default: {DEFAULT_TTL_MINUTES}, 0 to disable)")
    parser.add_argument("--reset", action="store_true", help="Reset conversation history")
    parser.add_argument(
        "--history", action="store_true", help="Print conversation history"
    )
    args = parser.parse_args()

    # Roster problems are exit 2 — distinct from an API failure (1), so a
    # caller can tell "you configured it wrong" from "the model call failed".
    try:
        roster = load_config()
        if args.list:
            print(format_roster(roster, verbose=args.verbose))
            return
        entry = roster.get(args.model_key) if args.model_key else roster.default_entry()
    except ConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    adapter = make_adapter(entry)

    # Offline operations first — these are pure local file ops and must not
    # require an API key. A user setting up the script for the first time
    # may legitimately want to inspect or wipe history before configuring
    # any provider key.

    # Show history and exit
    if args.history:
        raw = adapter.load_history_raw()
        print(json.dumps(raw, indent=2))
        return

    # Read from stdin if no message yet (do it now so we know whether
    # --reset is being used standalone or with a message to send).
    message: str = args.message
    if not message and not sys.stdin.isatty():
        message = sys.stdin.read().strip()

    # Standalone --reset (no message) is also offline — clear and exit
    # without requiring an API key.
    if args.reset and not message and not args.pr_number:
        adapter.reset_history()
        print(f"History reset for {entry.key}.", file=sys.stderr)
        return

    # Anything past this point will call the model's API.
    if not adapter.api_key():
        print(
            f"Error: {adapter.api_key_env_var()} not set "
            f"(required by model {entry.key!r}, access_method {entry.access_method}).",
            file=sys.stderr,
        )
        sys.exit(1)

    # PR review mode
    if args.pr_number:
        ignore_paths = list(DEFAULT_IGNORE_PATHS) + args.ignore_paths
        review_pr(args.pr_number, adapter, args.message, ignore_paths=ignore_paths)
        return

    # --reset combined with a message: reset first, then proceed to send.
    if args.reset:
        adapter.reset_history()

    if not message:
        parser.print_help()
        sys.exit(1)

    # Load file content
    file_content = ""
    if args.file_path:
        path = Path(args.file_path)
        if not path.is_file():
            print(f"Error: File not found: {args.file_path}", file=sys.stderr)
            sys.exit(1)
        file_content = path.read_text()

    print(f"--> Model: {entry.name} ({entry.id})", file=sys.stderr)

    # Build full message
    full_message = message
    if file_content:
        full_message = f"{message}\n\n```\n{file_content}\n```"

    # Token estimate for large context warning
    token_est = len(full_message) // 4
    if token_est > 32000:
        print(
            f"--> Large context: ~{token_est} tokens. Consider context caching.",
            file=sys.stderr,
        )

    # Load history (filtered by session + TTL)
    session = args.session or None
    ttl = args.ttl_minutes
    history = adapter.load_history(session=session, ttl_minutes=ttl)

    # Preserve timestamps from surviving entries for re-save
    raw = adapter.load_history_raw()
    old_entries = raw.get("entries", [])
    # After load_history filtering, we have len(history) surviving messages.
    # Grab their timestamps (from the tail of old_entries that survived).
    if session and raw.get("session") != session:
        surviving_timestamps: list[float] = []
    else:
        cutoff = time.time() - (ttl * 60) if ttl > 0 else 0
        surviving_timestamps = [
            e["timestamp"] for e in old_entries if e.get("timestamp", 0) >= cutoff
        ]

    history = adapter.add_message(history, "user", full_message)
    surviving_timestamps.append(time.time())

    system_prompt = (
        args.system_prompt
        or os.environ.get("AGENT_REVIEWER_SYSTEM_PROMPT")
        or os.environ.get("GEMINI_SYSTEM_PROMPT")
        or DEFAULT_SYSTEM_PROMPT
    )

    # API call
    request_body = adapter.build_request(system_prompt, history)
    response_data = adapter.call_api(request_body)

    # Parse response
    text, signature = adapter.extract_response(response_data)

    # Save to history
    history = adapter.add_message(history, "model", text, signature)
    surviving_timestamps.append(time.time())
    adapter.save_history(history, session=session, timestamps=surviving_timestamps)

    # Output
    print(text)


if __name__ == "__main__":
    main()
