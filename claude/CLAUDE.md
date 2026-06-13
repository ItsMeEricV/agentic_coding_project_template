## General DO

- **Be very concise.** Drop preambles ("Let me…", "I'll go ahead and…"), trailing summaries ("I've now…"), unnecessary articles, and section headers on short replies. One sentence beats two. Sacrifice grammar when meaning survives. If the answer is a path, return the path — don't wrap it. Do not glaze me; no superlative praise.
- Always use `rg`, not `grep`.
- When designing systems with UUID type unique keys, always default to the UUIDv7 format. E.g. `id String @id @default(uuid(7))` in Postgres.
- **Use the `pull-request-creator` skill** when creating, updating, or commenting on a PR — title format, body template, and comment-reply discipline all live there.
- **`KNOWLEDGE.md` (or `KNOWLEDGE-MAP.md` pointing to per-area files) is a project's domain glossary** — terms, preferred names, flagged ambiguities. Read it early to ground yourself in a repo's language; update it when a term gets clarified. Created/maintained by the `deep-discuss` skill.

### Github interactions

- **Prefer the GitHub MCP server** (`mcp__github__*` tools) for all GitHub operations: PR create/edit, issue create/edit, commenting, reviewing, reading PR/issue state, status checks, etc. JSON-typed args mean no shell-quoting hazards (markdown backticks in PR bodies stay literal), tool calls parallelize within a single message, and a single `pull_request_read` returns mergeable state + checks + stats in one shot.
- **Fall back to the `gh` CLI** only when (a) the MCP doesn't expose the operation you need, (b) the MCP fails, or (c) you genuinely need an interactive flow. When using `gh` for multi-line content (PR body, issue body, commit message), write the body to `/tmp/<purpose>.txt` with the Write tool and pass `--body-file` / `-F` — never use `"$(cat <<'EOF' ... EOF)"`, since markdown backticks have leaked through quoted heredocs and triggered real command substitution (one historical case actually ran `vercel deploy --prod` from a PR body).

### ⚠️ Branch workflow — start new work from a clean branch off `main`/`master`

Branch name format: `ev-<description>` (hyphens, lowercase). Examples: `ev-hidden-channels-modal`, `ev-bugfix-section-header`, `ev-refactor-search-api`.

When asked to create a new branch or start new work, run automatically:

```bash
git status
git checkout master   # or `main` per repo
git pull
git checkout -b ev-<description>
```

### ⚠️ Commit + push workflow — after each completed change

**If tests fail**: try to fix them yourself first. If you can't, stop and ask before committing, pushing, or moving on — never commit on a red build.

After formatter/linter/type-check pass:

1. **Commit immediately** — don't wait to be asked.
2. **One commit per logical change** — atomic history.
3. **Push after each commit.**
4. **Descriptive messages** — explain the "what" concisely.
5. **Do not open a PR until the user asks.** When they do, invoke the `pull-request-creator` skill (owns title/body/reply discipline).

**PR description rules worth restating here** (the `pull-request-creator` skill owns the full template):

- Add a `Co-Authored-By:` line using your current model version (e.g. `Co-Authored-By: Claude 4.6`).
- **Always use descriptive link text** — never naked URLs.
  - ❌ Bad: `https://<workspace>.slack.com/archives/<channel-id>/<ts>`
  - ✅ Good: `[Internal user report about missing "Mark as read" option](https://<workspace>.slack.com/archives/<channel-id>/<ts>)`
- **Commit-by-commit review note:** under "Notes for Reviewers", say each commit is self-contained and can be reviewed individually.
- **Skip `pr-review-toolkit` on simple PRs** — token cost outweighs signal. Don't run it (and don't suggest it) when any of these hold: docs/`.md`-only changes, tests-only changes, or under 500 lines of code changed. This overrides the `pull-request-creator` skill's default to always run it.

## Code Style & Formatting

- **Formatter:** Always use **Prettier** for all `.ts`, `.tsx`, `.js`, `.json`, `.jsonc`, and `.css` files.
- **Execution:** After modifying or creating a file, run `npx prettier --write <file_path>` to ensure the disk version matches the project's style.
- **Rules:** Respect the project's `.prettierrc` file. Do not use internal LLM formatting if it contradicts the local Prettier config.
- **Verification:** If a "lint" or "format" step fails during a build, automatically run the Prettier fix command before reporting the error.

## Anti-patterns (DO NOT)

- **NEVER create a GitHub issue without explicit user permission. HARD RULE.** Opening an issue adds a row to the user's backlog that has to be triaged, closed, or lived with. Past agents have unprompted-created issues while writing PR bodies, audit reports, and follow-up plans — the result is backlog bloat and confusion about what was actually decided. Before calling `mcp__github__issue_write` with `method: create` (or `gh issue create`), propose title + one-paragraph summary and wait for explicit "yes, open it." Editing/commenting on an existing issue, or closing one the user told you to close, is fine without re-asking.
- **NEVER add a new environment variable without explicit user permission. HARD RULE.** Do not introduce a new env var anywhere — not in code (`process.env.FOO`), not in `.env`/`.env.*`/`.env.example`, not in `docker-compose`, not in a Zod env schema, not in CI/deploy config, not in Vercel/host settings. Past agents have invented env vars silently — wrong names, wrong defaults, scattered reads — and the user only finds out later. Before adding one: stop, propose the exact name, where it's read, its default/required status, and which environments it lives in, then wait for an explicit "yes." This applies even when adding the var seems obviously necessary to finish the task. Reading or renaming an env var the user already defined is fine; creating a new one is not.
- **No destructive data operations without explicit permission.** Never reset, drop, or wipe a database, table, or production data store — not even in dev. Schema changes go through migrations; data fixes go through seed/backfill scripts. Same rule for `rm -rf`, `git reset --hard`, `git push --force`, or force-deleting branches with unpushed work — stop and ask first.
- **No bandaid casts to silence type errors.** Don't reach for `any`, `ts-ignore`, `as any`, or `as unknown` to make TS errors disappear. Use Zod-parsed types, branded types, or type guards. If a cast is genuinely necessary at a system boundary, document the why inline. Same principle applies to runtime bugs — address the root cause, not the symptom.
- **No PII in logs.** Never log emails, passwords, auth tokens, credit card numbers, or raw SQL containing user input. Log opaque identifiers (`userId`, `recordingId`) instead.
- **Never commit secrets.** No API keys, tokens, or credentials in source control. Use `.env` dotfiles loaded at runtime.
- **Mock at the network/storage boundary** (DB driver, `fetch`, S3 client) in tests. Never mock internal functions or private class methods — those produce brittle tests that break on every refactor.
- **No `setTimeout` in tests.** Use `waitFor` / `findBy*` / `waitForElementToBeRemoved` instead.
- **Vendor-agnostic naming for AI/ML integrations.** `invokeLlm` not `invokeClaude`; `generateEmbedding` not `generateTitanEmbedding`. The model/provider is a config detail, not a code contract.
