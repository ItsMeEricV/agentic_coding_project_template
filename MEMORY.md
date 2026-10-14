# MEMORY.md: The AI Journal

This file is the project's journal and is **always AI-maintained** — not for humans to edit by hand.

## Purpose

Capture the non-obvious: bugs, quirks, gotchas, and patterns discovered during development, so nobody rediscovers them the hard way. Because it is version-controlled and vendor-neutral, it is the one memory every reader shares — humans, Claude, Gemini, and Codex alike.

## What does NOT belong here

- **Stable engineering rules** → `AGENTS.md`. If it will be true a year from now for every contributor, it is a rule, not a memory.
- **Domain vocabulary** → `KNOWLEDGE.md`. **The "what"** → `SPEC.md`. **The "where/how"** → `ARCHITECTURE.md`.
- **Personal preferences and cross-project working style** → the agent's own memory store (e.g. Claude Code's auto-memory under `~/.claude/projects/<slug>/memory/`). Those are per-user, not per-repo, and duplicating them here rots both copies.
- **Anything git blame or the code already answers.** A memory has to save the next reader real time.

## Structure

Organize by category, newest understanding folded into the existing entry rather than appended below it. Keep entries to a summary line or two; link out to a file or PR when detail is needed.

---

## Project Context & Quirks

_Environment-specific discoveries, naming conventions, and infrastructure gotchas._

- **Example:** The staging database requires an SSH tunnel on port `5433` before running migrations.

---

## Lessons Learned & Edge Cases

_"I struggled" moments, surprising API behavior, and non-obvious solutions._

### Database / ORM

- **Example:** Composite unique constraints on optional fields may fail during upsert when a field is `null`. Always check for existence explicitly or ensure constraint fields are required.

### Infrastructure

- **Example:** `docker compose restart` does NOT re-read `env_file`. Must use `docker compose up -d` to pick up new env vars.
- **Discord deploy alerts use a plain webhook, not the official `discord` plugin.** The plugin is a two-way bot bridge: it needs Bun, a bot token, per-channel opt-in, and only connects when the session is launched with `--channels plugin:discord@claude-plugins-official` — silently absent otherwise. A webhook URL in `~/.claude/channels/discord/.env` works in every session with one `curl`.
