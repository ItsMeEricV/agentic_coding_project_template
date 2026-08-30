# `cli/`

Standalone scripts that operate on the project but live outside the application code. Anything that's a script — bash, Python, TypeScript via `tsx` — goes here.

Make every script executable (`chmod +x`) and prefer a shebang (`#!/usr/bin/env bash`, `#!/usr/bin/env python3`) so users can invoke them directly.

## Shipped scripts

| File                     | Purpose                                                                                                                                                                                                                                                                                                                                             |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `worktree-add.sh`        | Create a new git worktree wired up for the project's Docker stack (auto-assigned ports, COMPOSE_PROJECT_NAME, WORKTREE_DB). See `docker/nextjs/README.md` → "The worktree pattern."                                                                                                                                                                 |
| `agent_code_reviewer.py` | Config-driven second-opinion code reviewer. Models come from `agent_reviewer.toml`; reviewer provides feedback only, never writes code. Run with `uv run` (deps are declared in a PEP 723 header). See the `agent-code-reviewer` skill for invocation judgment; `uv run cli/agent_code_reviewer.py --list` shows the roster and `--help` the flags. |
| `agent_reviewer.toml`    | Model roster for the reviewer: one `[[models]]` entry per model, each with a `key` (passed to `--model`), an `access_method` (`gemini_api` / `openai_api` / `openrouter` — this is the wire protocol), and an `id`. Committed and secret-free; API keys stay in env vars.                                                                           |

## Conventions

- **One-job scripts.** A script does one thing. If it grows multiple modes, split it before it grows further.
- **Fail loud.** Use `set -euo pipefail` in bash; check return codes / raise in Python. Silent failure is worse than no script.
- **Exit codes are part of the API.** Reserve `0` for success. Document non-zero exit codes in the script's docstring or `--help`.
- **Long-form usage in `--help`** (Python's `argparse` or `--help` flag in bash). Keep the README listing one-line; the details live in the script.
- **Idempotent where possible.** Re-running the script should be safe by default; gate destructive actions behind explicit confirmation.
