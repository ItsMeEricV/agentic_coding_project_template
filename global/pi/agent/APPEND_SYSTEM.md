# pi-specific rules

Loaded as `~/.pi/agent/APPEND_SYSTEM.md` from `global/pi/agent/`. Shared rules load separately via
`~/.pi/agent/AGENTS.md`. This file holds only what is specific to `pi`.

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

### Browser automation — use `npx playwright cli`

- The interactive verbs live under the `cli` subcommand — `npx playwright cli click …`,
  not `npx playwright click …`. Bare `npx playwright` only offers one-shot
  `screenshot` / `pdf` / `codegen` / `open`.
- It is **stateful**: the browser survives between invocations, so each command is its own
  `bash` call. `open <url>` to start, `close` when done. Name concurrent sessions with
  `-s=<name>`; `list` / `close-all` / `kill-all` clean up strays.
- Core loop: `snapshot` returns element refs, then `click` / `fill` / `type` / `select` /
  `hover` / `check` / `upload` act on a ref. `find <text>` searches the snapshot without
  re-dumping it. Snapshots are written to `.playwright-cli/` in the cwd — gitignore it.
- Inspect with `console`, `requests` then `request <n>` / `response-body <n>`, and
  `screenshot`. `route <pattern>` mocks a request; `network-state-set offline` kills the network.
- Cookies and storage are first-class — no CDP script needed. `cookie-list`, `cookie-get`,
  `cookie-set <name> <value>` (with `--domain --path --expires --httpOnly --secure --sameSite`),
  `cookie-delete`, `cookie-clear`, plus `localstorage-*` and `sessionstorage-*`.
  `state-save` / `state-load` persist a logged-in session to a file for reuse.
- Attach to a Chrome already running with a debug port:
  `npx playwright cli attach --cdp http://localhost:9222`.
- Keep output small: `--raw` prints just the value, `--json` for parsing. Headless is the
  default (`--headed` only when the user wants to watch); `--mobile` renders lighter pages.
- **Not covered — say so instead of improvising:** Lighthouse audits (use the separate
  `lighthouse` CLI), Chrome performance traces with Core Web Vitals insights, heap
  snapshots, and CPU throttling. `tracing-start` / `tracing-stop` record a *Playwright*
  trace for `npx playwright show-trace`, which is a different artifact.

### Library / framework docs — use the Context7 HTTP API

- For current docs on a library, framework, SDK, or CLI (React, Next.js, Prisma,
  Tailwind, Django, …), query Context7 over plain HTTP with `curl`. No auth required.
- Resolve a library: `curl -s "https://context7.com/api/v1/search?query=<library>"`
- Fetch docs: `curl -s "https://context7.com/api/v1/<org>/<project>?type=txt&tokens=5000"`
  (e.g. `vercel/next.js`).
- Use this instead of guessing from memory — training data lags real releases. Do not
  use it for refactoring, debugging business logic, or general programming concepts.
