# AGENTS.md — pi global agent rules

Global instructions for the `pi` agent. This file lives in
`agentic_coding_project_template/pi/agent/AGENTS.md` and is symlinked to
`~/.pi/agent/AGENTS.md` so it stays in source control.

Project-level `AGENTS.md` files override anything here.

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
  leaked through and triggered real command substitution.
- **Never create a GitHub issue without explicit user permission.** Propose the title
  and a one-paragraph summary, then wait for a clear "yes." Editing or commenting on an
  existing issue is fine.

### Neon (Postgres) — use `neonctl`

- Use `neonctl` for database branching, running SQL, listing projects, and fetching
  connection strings.
- Useful shapes: `neonctl projects list`, `neonctl branches create --name <name>`,
  `neonctl connection-string <branch>`, `neonctl sql --query "<sql>"`.
- Prefer creating a Neon branch over touching a shared database when experimenting.
- Never reset, drop, or wipe a database or table without explicit permission — schema
  changes go through migrations, data fixes through seed/backfill scripts.

### Vercel — use `vercel`

- Use the `vercel` CLI for deployments, environment variables, project linking, logs,
  and domains.
- Useful shapes: `vercel deploy`, `vercel deploy --prod`, `vercel env ls`,
  `vercel env pull .env.local`, `vercel logs <url>`, `vercel link`, `vercel projects ls`.
- **Never run a production deploy (`vercel deploy --prod` / `vercel --prod`) unless the
  user explicitly asked for production.** Preview deploys are the default.
- Adding a new environment variable requires explicit user permission — propose the
  exact name, where it is read, and its default before running `vercel env add`.

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

## Secrets Hygiene

- Never print an API key, token, or connection string into the transcript. Pipe values
  straight into the consuming command (`TOK=$(jq -r ... ) && curl -H "Authorization: $TOK"`).
- Never commit secrets. Credentials live in `.env` dotfiles loaded at runtime.
- Log opaque identifiers (`userId`, `recordingId`) — never emails, passwords, tokens, or
  raw SQL containing user input.
