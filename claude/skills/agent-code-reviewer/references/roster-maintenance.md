# Roster maintenance

Read this only when the user asks to add, bump, or audit a model in `cli/agent_reviewer.toml`, or a catalog check report asks them to. Never edit the roster unprompted: an entry commits a model choice to the repo for every future run.

## Checking for newer versions

Review runs check the public catalog once a day on their own. To run the check on demand:

```bash
uv run cli/agent_code_reviewer.py --check-versions
```

It reports two things. First, a same-family id listed later (`claude-opus-5` → `claude-opus-5.5`), with both listing dates, window, and price. The listing date decides, not the version number: xAI's `grok-4.20` predates `grok-4.6`. Second, a **new family**: a model from a vendor the roster already uses, under a name no entry carries (`gemini-4-argon` beside `gemini-3.1-pro`). A suffix makes a separate family, so `gpt-6.1-sol-pro` is never offered as an upgrade of `gpt-6.1-sol`.

Review runs report these on stderr and carry on, and session-start adapters for Claude Code (`.claude/settings.json`) and pi (`.pi/extensions/catalog-notice.ts`) run `--catalog-notice` to show the same report to the user at the start of each session, or a warning when the check cannot run. A minor bump is reported once a day. A **major jump** (`claude-opus-5.5` → `claude-opus-6`, preview or final) or a new family, listed after the roster's `catalog_reviewed` date, is reported on every run until it is settled.

Settling it is the user's call. Show them the tables, and for each model they want, bump or add the entry (below). Then set `catalog_reviewed` to today, even if they declined everything: the date records that someone looked. Report only — the script never edits the roster. Bump `id`, `name`, `context_window`, and `max_output_tokens` together, and only when the user asks.

## Adding a model

The only hard part is the provider's exact `id`. Never guess a slug from a marketing name; resolve it:

```bash
uv run cli/agent_code_reviewer.py --find-model astra
```

That searches OpenRouter's catalog (public, no key) and prints each match's id, context window, max output, per-million price, and whether it is an alias or a batch variant. Adding the entry never needs a Python change: the roster is data, and the three `access_method` adapters cover every model these providers host.

Pick from what it returns:

- **Take the pinned id, not a floating alias.** Aliases are annotated `alias -> <target>` and sorted last. An alias silently changes model under an entry whose `key` and `name` still claim the old one.
- **Skip `:batch` variants.** Half price, but queued rather than interactive — wrong shape for a review loop you are waiting on.
- **Copy the context window the catalog prints.** A guess that is too high overflows the model instead of failing early. Leave `max_output_tokens` unset unless a review stops on `length` (exit 5), and then set it no higher than the catalog's MAX OUT: it is held back from the window.
- **Set `tag`** when the family already has one (the OpenAI/Codex entries share `CODEX`); otherwise it defaults to the key upper-cased and becomes a public label on PR comments. Never `CLAUDE`: `AGENTS.md` reserves that for the authoring agent's own replies.
- **Confirm with `--list`**, which resolves the roster and shows whether the entry's API key is set.

A model reachable only through a direct provider API (a preview id OpenRouter has not listed) will not appear. Take the id from the provider's own model list and set `access_method` to `gemini_api` or `openai_api`.
