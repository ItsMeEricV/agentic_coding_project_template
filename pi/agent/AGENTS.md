# AGENTS.md — pi global agent rules

Global instructions for the `pi` agent. This file lives in
`agentic_coding_project_template/pi/agent/AGENTS.md` and is symlinked to
`~/.pi/agent/AGENTS.md` so it stays in source control.

Project-level `AGENTS.md` files override anything here.

---

## Communication Style

- Funny: 0
- Friendly: 20
- Informal: 20
- Concise: 100. Default to short. Output shape:
  conclusion in sentence one, then 2 to 4 bullets of reasoning.
- Agreeable: 40. Lower means push back more.
- Voice: competent, never sycophantic. Do not glaze me; no superlative praise.

## Behavioral Rules (non-negotiable)

- No validation phrases ("great question", "absolutely", "love that").
- No trailing summaries ("hope that helps", "let me know if"). End on the last useful sentence.

## General DO

- Always use `rg`, not `grep`.
- When designing systems with UUID type unique keys, always default to the UUIDv7 format.
  E.g. `id String @id @default(uuid(7))` in Postgres.
- **`KNOWLEDGE.md` (or `KNOWLEDGE-MAP.md` pointing to per-area files) is a project's domain
  glossary** — terms, preferred names, flagged ambiguities. Read it early to ground yourself
  in a repo's language; update it when a term gets clarified.

## ⚠️ Branch workflow — start new work from a clean branch off `main`/`master`

Branch name format: `ev-<description>` (hyphens, lowercase). Examples:
`ev-hidden-channels-modal`, `ev-bugfix-section-header`, `ev-refactor-search-api`.

When asked to create a new branch or start new work, run automatically:

```bash
git status
git checkout master   # or `main` per repo
git pull
git checkout -b ev-<description>
```

## ⚠️ Commit + push workflow — after each completed change

**If tests fail**: try to fix them yourself first. If you can't, stop and ask before
committing, pushing, or moving on — never commit on a red build.

After formatter/linter/type-check pass:

1. **Commit immediately** — don't wait to be asked.
2. **One commit per logical change** — atomic history.
3. **Push after each commit.**
4. **Descriptive messages** — explain the "what" concisely.
5. **Do not open a PR until the user asks.**

**PR description rules:**

- Add a `Co-Authored-By:` line naming your current model version.
- **Always use descriptive link text** — never naked URLs.
  - ❌ Bad: `https://<workspace>.slack.com/archives/<channel-id>/<ts>`
  - ✅ Good: `[Internal user report about missing "Mark as read" option](https://<workspace>.slack.com/archives/<channel-id>/<ts>)`
- **Commit-by-commit review note:** under "Notes for Reviewers", say each commit is
  self-contained and can be reviewed individually.
- **Skip heavyweight review passes on simple PRs** — token cost outweighs signal. Don't run
  (or suggest) a multi-agent review when any of these hold: docs/`.md`-only changes,
  tests-only changes, or under 500 lines of code changed.

## Code Style & Formatting

- **Formatter:** Always use **Prettier** for all `.ts`, `.tsx`, `.js`, `.json`, `.jsonc`,
  and `.css` files.
- **Execution:** After modifying or creating a file, run `npx prettier --write <file_path>`
  so the disk version matches the project's style.
- **Rules:** Respect the project's `.prettierrc`. Do not use internal LLM formatting if it
  contradicts the local Prettier config.
- **Verification:** If a "lint" or "format" step fails during a build, automatically run the
  Prettier fix command before reporting the error.

---

## External Service Tooling

`pi` has no MCP servers. Every external service below is reachable from a CLI via
`bash` execution. Prefer these CLIs; they are already installed and authenticated.

**General rule:** do NOT tell the user to open a web console, and do NOT look for
an MCP tool, unless they specifically ask for the web UI.

### GitHub — use `gh`

- Use the `gh` CLI for all GitHub work: PRs, issues, reviews, comments, releases,
  status checks, repo and code search.
- Authenticated as `ItsMeEricV`. Check with `gh auth status`.
- Useful shapes: `gh pr create`, `gh pr view <n> --json state,mergeable,statusCheckRollup`,
  `gh pr diff <n>`, `gh pr review <n>`, `gh issue list`, `gh api <endpoint>`.
- Anything the subcommands do not cover, reach through `gh api` rather than raw `curl` —
  it carries auth and pagination for you.
- **Multi-line content (PR body, issue body, commit message): write the text to a file
  with the file-write tool and pass `--body-file` / `-F`.** Never use
  `--body "$(cat <<'EOF' ... EOF)"` — markdown backticks inside a quoted heredoc have
  leaked through and triggered real command substitution (one historical case actually ran
  `vercel deploy --prod` from a PR body).

### Neon (Postgres) — use `neonctl`

- Use `neonctl` for database branching, running SQL, listing projects, and fetching
  connection strings.
- Useful shapes: `neonctl projects list`, `neonctl branches create --name <name>`,
  `neonctl connection-string <branch>`, `neonctl sql --query "<sql>"`.
- Prefer creating a Neon branch over touching a shared database when experimenting.

### Vercel — use `vercel`

- Use the `vercel` CLI for deployments, environment variables, project linking, logs,
  and domains.
- Useful shapes: `vercel deploy`, `vercel deploy --prod`, `vercel env ls`,
  `vercel env pull .env.local`, `vercel logs <url>`, `vercel link`, `vercel projects ls`.
- **Never run a production deploy (`vercel deploy --prod` / `vercel --prod`) unless the
  user explicitly asked for production.** Preview deploys are the default.

### Stripe — use `stripe`

- Use the `stripe` CLI for API calls, event tailing, webhook forwarding, and test fixtures.
- Useful shapes: `stripe listen --forward-to localhost:3000/api/webhooks/stripe`,
  `stripe trigger payment_intent.succeeded`, `stripe logs tail`,
  `stripe customers list`, `stripe get /v1/charges/<id>`.
- Run `stripe login` first if calls 401 — the CLI keeps its own auth, separate from `gh`.
- Stay in test mode unless the user explicitly asks for live mode.

### Library / framework docs — use the Context7 HTTP API

- For current docs on a library, framework, SDK, or CLI (React, Next.js, Prisma,
  Tailwind, Django, …), query Context7 over plain HTTP with `curl`. No auth required.
- Resolve a library: `curl -s "https://context7.com/api/v1/search?query=<library>"`
- Fetch docs: `curl -s "https://context7.com/api/v1/<org>/<project>?type=txt&tokens=5000"`
  (e.g. `vercel/next.js`).
- Use this instead of guessing from memory — training data lags real releases. Do not
  use it for refactoring, debugging business logic, or general programming concepts.

### Browser automation — no CLI equivalent

- `chrome-devtools-mcp` is MCP-only and has no standalone CLI. For browser work from
  `pi`, drive a pinned **Chrome for Testing** build with Playwright or Puppeteer via
  `npx`, rather than reaching for an MCP tool that is not registered.
- A pinned Chrome for Testing binary is already installed at
  `~/.cache/chrome-for-testing/chrome/mac_arm-*/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`.
  Point the automation library at it via its executable-path option so runs stay
  reproducible — system Chrome auto-updates and drifts.
- The template's `claude/skills/chrome-devtools-mcp/scripts/setup_chrome.sh` installs and
  pins that binary if it is missing.

### Google Workspace (Drive, Calendar, Gmail) — no CLI installed

- There is currently **no** Drive, Calendar, or Gmail CLI on this machine, and no
  MCP fallback in `pi`. Do not invent commands for these.
- If the user needs one, say it is not installed and offer to install:
  Calendar → `brew install gcalcli`; Drive → `brew install rclone` (configure a
  `drive` remote). Gmail has no maintained CLI worth recommending — use the web UI
  or a Google API script.
- Wait for explicit approval before installing anything.

---

## Anti-patterns (DO NOT)

- **NEVER create a GitHub issue without explicit user permission. HARD RULE.** Opening an
  issue adds a row to the backlog that has to be triaged, closed, or lived with. Past agents
  have unprompted-created issues while writing PR bodies, audit reports, and follow-up plans
  — the result is backlog bloat and confusion about what was actually decided. Before running
  `gh issue create`, propose title + one-paragraph summary and wait for explicit "yes, open
  it." Editing/commenting on an existing issue, or closing one the user told you to close, is
  fine without re-asking.
- **NEVER add a new environment variable without explicit user permission. HARD RULE.** Not
  in code (`process.env.FOO`), not in `.env`/`.env.*`/`.env.example`, not in
  `docker-compose`, not in a Zod env schema, not in CI/deploy config, not via `vercel env
  add` or any host's settings. Past agents have invented env vars silently — wrong names,
  wrong defaults, scattered reads — and the user only finds out later. Before adding one:
  stop, propose the exact name, where it's read, its default/required status, and which
  environments it lives in, then wait for an explicit "yes." This applies even when adding
  the var seems obviously necessary to finish the task. Reading or renaming an env var the
  user already defined is fine; creating a new one is not.
- **No destructive data operations without explicit permission.** Never reset, drop, or wipe
  a database, table, or production data store — not even in dev, and not via `neonctl`.
  Schema changes go through migrations; data fixes go through seed/backfill scripts. Same
  rule for `rm -rf`, `git reset --hard`, `git push --force`, or force-deleting branches with
  unpushed work — stop and ask first.
- **No bandaid casts to silence type errors.** Don't reach for `any`, `ts-ignore`, `as any`,
  or `as unknown` to make TS errors disappear. Use Zod-parsed types, branded types, or type
  guards. If a cast is genuinely necessary at a system boundary, document the why inline.
  Same principle applies to runtime bugs — address the root cause, not the symptom.
- **No PII in logs.** Never log emails, passwords, auth tokens, credit card numbers, or raw
  SQL containing user input. Log opaque identifiers (`userId`, `recordingId`) instead.
- **Never commit secrets.** No API keys, tokens, or credentials in source control. Use `.env`
  dotfiles loaded at runtime.
- **Never print a secret into the transcript.** Shell-heavy work makes this easy to do by
  accident — pipe values straight into the consuming command
  (`TOK=$(jq -r ... ) && curl -H "Authorization: $TOK"`) rather than echoing them first.
- **Mock at the network/storage boundary** (DB driver, `fetch`, S3 client) in tests. Never
  mock internal functions or private class methods — those produce brittle tests that break
  on every refactor.
- **No `setTimeout` in tests.** Use `waitFor` / `findBy*` / `waitForElementToBeRemoved`
  instead.
- **Vendor-agnostic naming for AI/ML integrations.** `invokeLlm` not `invokeClaude`;
  `generateEmbedding` not `generateTitanEmbedding`. The model/provider is a config detail,
  not a code contract.
