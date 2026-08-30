# Config-driven model roster for the agent code reviewer

`cli/agent_code_reviewer.py` hardcoded two backends (Gemini, Codex) selected by `--provider`, with a `--pro`/`--lite` switch per backend. Adding a model meant editing Python. This RFC replaces that with a committed **roster** — `cli/agent_reviewer.toml` — that declares the available models as data, and adds OpenRouter as a third access method so any model OpenRouter carries is reachable without new code.

## Vocabulary

- **Roster** — `cli/agent_reviewer.toml`, the committed list of models this project can review with. Contains no secrets: API keys stay in env vars.
- **Model entry** — one `[[models]]` table in the roster.
- **Key** — a model entry's short slug; the value passed to `--model` and the identity used for its history file. Stable: renaming a key breaks saved invocations.
- **Access method** — how a model entry is reached: `gemini_api`, `openai_api`, or `openrouter`.
- **Tag** — the bracketed attribution label prefixed to inline PR comments (`**[GEMINI]**`), per `AGENTS.md`. Optional; defaults to the key upper-cased.
- **Direct adapter** — an access method that talks to a vendor's own API (`gemini_api`, `openai_api`) rather than going through OpenRouter.

## Decisions

**The access method *is* the wire protocol.** The obvious schema — `access_method = "direct_api" | "openrouter"` plus an `id` — is underspecified: `direct_api` cannot tell the script whether to speak Gemini's `generateContent` (system_instruction/contents/parts, key in the query string) or OpenAI's `/v1/responses` (instructions/input, Bearer header). Rather than add a second field the validator would have to keep consistent with the first, the enum itself names the protocol. Adding a direct provider later means a new enum value and a new adapter class — one field, no inference from model ids.

**The roster lives in the repo, not in `~/.claude`.** This repository is a project template: everything a fork needs must travel with the fork. A `~/.claude` tier would make the roster unversioned, undiffable, and invisible to the project. The path is `Path(__file__).parent / "agent_reviewer.toml"`, with no env-var override — a second lookup site earned nothing once the user tier was rejected.

**OpenRouter uses its SDK; the direct adapters keep `urllib`.** The script was deliberately dependency-free, which is why both existing adapters hand-roll HTTP. That constraint is lifted via PEP 723 inline metadata plus `uv run`, so the `openrouter` package costs one line — but only the new adapter adopts it. Rewriting the two working adapters would put the Gemini `thoughtSignature` round-trip and the OpenAI `store` / `previous_response_id` chaining at risk with no test coverage to catch a regression. The resulting mixed style is intentional, and the migration is tracked as a separate issue blocked on those tests.

**`store` moves from an env var into the roster.** Server-side response retention was an opt-in `CODEX_STORE=1` env var. It is a per-model behavior knob with a privacy trade-off — enabling it means OpenAI retains every payload, including private `--pr` diffs — so it belongs where a reader of the roster can see it. Valid only on `openai_api` entries; the validator rejects it elsewhere.

## Considered and rejected

- **OpenRouter only, dropping both direct adapters.** One protocol, one key, one code path. Rejected: it discards two working adapters and routes every review through a single vendor's margin and uptime.
- **Migrating all three adapters to official SDKs.** Consistent style, less hand-rolled JSON walking. Rejected for this change on scope and risk grounds; see the SDK-migration issue.
- **Merged repo + user roster tiers.** A user file patching entries by key. Rejected: merge semantics are the kind of thing that bites a year later, when an entry behaves unexpectedly and the cause is two files deep.
- **Selecting a model by `name` substring, by slugified name, or by array index.** Rejected in favor of an explicit `key`: substring matching silently changes meaning as the roster grows, derived slugs break saved commands when a `name` is edited, and an index silently repoints every invocation when the file is reordered.

## Consequences

- Invocation changes everywhere to `uv run cli/agent_code_reviewer.py …` — the skill, `cli/README.md`, and the module docstring all carry the old form.
- `--provider`, `--pro`, and `--lite` are deleted, along with `AGENT_REVIEWER_PROVIDER`, `GEMINI_MODEL`, `CODEX_MODEL`, `GEMINI_HISTORY_FILE`, and `CODEX_HISTORY_FILE`. `OPENROUTER_API_KEY` is the only addition — a net reduction of four env vars.
- History files are keyed per model entry (`/tmp/agent_reviewer_<key>.json`), so switching models no longer collides with an existing conversation.
- `AGENTS.md` documents a fixed set of attribution tags; that convention now sources its tags from the roster.
