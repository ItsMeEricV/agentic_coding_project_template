# AGENTS.md: Rules of Engagement

This document defines the **"How"** and the **"Who."** It acts as the system prompt extension for AI agents and the style guide for humans.

### Implementation Note for AI Agents

If you are an AI assistant (like Gemini or Claude) reading this file:

1. **Acknowledge Rules:** Acknowledge these rules by summarizing the current [Tech Stack] from `ARCHITECTURE.md` before starting a task.
2. **Strict Adherence:** All technical standards defined here are the absolute source of truth.

---

## 1. Global Engineering Standards (DOs)

### Core Standards

- **Modern Patterns:** Use the latest framework conventions (e.g., App Router for Next.js, Server Components by default).
- **Performance:** Design for scalability and efficiency. Every query must be indexed.
- **Code Style:** Write clear, concise, and idiomatic code. Favor readability over verbosity. Always use `async/await` for asynchronous TypeScript code — do not use raw `.then()` chains.
- **Accessibility & i18n:** Adhere to WCAG standards and use internationalization for all strings.
- **Vendor-agnostic naming.** Use generic names for swappable services: `invokeLlm` not `invokeClaude`, `generateEmbedding` not `generateTitanEmbedding`, `sendEmail` not `sendResend`, `uploadObject` not `uploadToS3`. The model / provider / vendor is a configuration detail, not a code contract — keeping the swap painless requires the codebase to never know which vendor is behind the interface.
- **Refactoring discipline: do not preserve abstractions just because they exist.** When changing a function or module, reason about its actual failure modes before assuming the existing structure is load-bearing. Pre-existing transactions, retries, or wrapper abstractions are often there because they seemed nice at the time, not because removing them breaks anything. "It was already here" is not a reason to keep code.

### Error Handling

- **Result Types over Exceptions:** Use a Result type library (e.g., `neverthrow`) to represent operations that can fail. Reserve `try/catch` only for truly exceptional, unrecoverable situations or at system boundaries (e.g., Server Actions that must throw to communicate errors to the framework runtime).
- **No Implicit Fallbacks:** Never silently fall back to session/context data in Server Actions. All identity-related fields (like `userId`, `instructorId`) must be explicitly passed by the caller. This keeps data flow explicit and prevents subtle ownership bugs.

### Security & Logging Hygiene

- **SSRF allowlists: parse the URL, match on the hostname.** Never regex-match the full URL when validating a redirect target or fetch target. Userinfo, query, fragment, and path segments are trivially weaponizable against full-URL regexes.
  - **Good:** `const u = new URL(input); if (!ALLOWED_HOSTS.has(u.hostname)) throw new Error("blocked");`
  - **Bad:** `if (/trusted\.example/.test(input)) { fetch(input); }` — `https://evil.example?@trusted.example` slips right through.

- **No PII in logs.** Never log emails, auth tokens, passwords, credit-card data, or raw SQL containing user input. Log opaque identifiers (`userId`, `recordingId`, `requestId`) for correlation. Treat every logged field as if it were publicly visible — to anyone with log access, it is.

- **Always log through a logger module, never bare `console.log` / `print`.** A central logger lets you swap transports (CloudWatch, Axiom, Datadog), inject request context (request ID, user ID), and enforce PII redaction in one place. Bare `console.log` bypasses all of that.

### Database & Migrations

- **Default to UUIDv7 for UUID primary keys.** UUIDv7 embeds a millisecond timestamp prefix, so inserts cluster to the right edge of the B-tree — the same locality property that makes serial integer keys cheap, without giving up global uniqueness. Reach for UUIDv4 only when unguessability dominates and you accept the index-locality cost.
  - **Good (Postgres + ORM):** `id String @id @default(uuid(7))`
  - **Bad:** `id String @id @default(uuid())` — random v4 scatters inserts across the B-tree, inflating index size and write amplification on hot tables.

- **DateTime columns: prefix with `date` and a past-tense verb.** New columns and new tables should use `dateCreated`, `dateUpdated`, `dateDelivered`, `dateReminderSent`. The verb makes the column self-documenting. Existing `createdAt` / `updatedAt` columns on legacy tables are grandfathered — leave them alone unless you're already migrating that table.

- **Backwards-compatible migrations only (Expand and Contract).** Never rename or drop columns in a single migration. Add new columns as nullable, deploy, backfill data, then add constraints or drop old columns in a subsequent release. Currently-running production code must continue to work if a deployment fails mid-migration.

- **No fake migration bookkeeping.** When applying schema changes outside your ORM's migration runner (e.g. raw SQL via a one-off CLI command, hot-fixing production), reproduce the runner's bookkeeping faithfully. Most ORMs verify a content checksum on every subsequent migrate run; placeholder values like `'manual-apply'` will pass on insert and then trigger silent drift-detection failures forever after. Compute the real digest (typically SHA-256 of the file contents) and write it to the metadata table the runner owns.

### Frontend & SSR

- **Hydration mismatches: defer non-deterministic client renders.** Libraries that generate IDs on the server (drag-and-drop primitives, accordion / dropdown / dialog components built on `useId`, anything random or time-based) produce hydration mismatches because the SSR-generated value differs from the client-generated one. When rendering these inside a `'use client'` component that is also server-rendered, gate them behind a `mounted` flag.

  ```tsx
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted ? <DndContext>...</DndContext> : null;
  ```

  Same pattern applies to anything else with non-deterministic output: random IDs, locale-formatted dates, `time-since-now` strings.

### Pre-Commit Checks

Before committing any changes, run these checks in order and fix any failures:

1. **Format:** Run your project's formatter (e.g., `prettier` for JS/TS, `black` for Python, `gofmt` for Go).
2. **Type Safety:** Run the type checker for your language (e.g., `tsc --noEmit` for TypeScript, `mypy` for Python, `go vet` for Go).
3. **Tests:** Run your test suite (e.g., `vitest run`, `pytest`, `go test ./...`).

_Note: If your project uses a monorepo or subdirectory structure, ensure you run these commands from the correct directory where the tooling is installed._

### Memory Management

- **Persistence:** After completing a major feature or resolving a complex bug, reflect on the session and update `MEMORY.md`.
- **Criteria:** Record discoveries that aren't obvious from the code (API quirks, required command sequences, "I struggled" signals).
- **Compaction:** Summarize findings into "Lessons Learned" or "Project Context." Do not append raw logs.
- **Validation:** Present proposed memory updates to the user for approval.

### Testing & Quality

- **Naming:** All test files must follow the `.test.ts` suffix. Never use `.spec.ts`.
- **Coverage:** Ensure logic-heavy modules and high-traffic routes are covered by unit/integration tests.
- **No `setTimeout` / `sleep` for async waits in tests.** Use the framework's async primitives (React Testing Library's `waitFor` / `findBy*`, Playwright's auto-waiting locators, `pytest-asyncio`). Hand-rolled timers are flaky and hide real race conditions.
- **Boundary mocking over internal mocking.** Mock at the network or storage boundary (HTTP client, database driver), not at the internal-function layer. Tests that mock private methods break on every refactor and validate implementation, not behavior.
- **E2E selectors via `data-testid`, not DOM traversal or `.first()`.** Stable test IDs survive markup refactors; chained CSS selectors and positional access do not. Add `data-testid` at component boundaries during development, not retroactively.
- **Split pure logic from DB / IO-importing modules.** Functions that import an ORM, an HTTP client, or a filesystem helper drag those imports into every test that touches them, slowing the suite and forcing brittle mocks. Keep validation, transformation, and policy logic in pure modules; have the IO-shaped layer call into them.

### Docker Development

If your project uses Docker for local development:

- **Before editing `docker/`:** invoke the `new-project-setup` skill. It walks through fork-time decisions (project slug, ORM choice, ngrok, PG extensions) and substitutes placeholders in one batch. Editing files directly causes silent failures — orphaned ORM scaffolding and shared-network collisions between projects.
- **Hot-reload:** Use volume mounts so source file changes are picked up without rebuilds.
- **When to rebuild:** After changing `package.json`/lock files, `Dockerfile`, `docker-compose.yml`, or ORM schema files.
- **Anonymous volumes:** When rebuilding after dependency changes, use `docker compose up -d --build -V <service>` to recreate anonymous volumes (e.g., `node_modules`). Without `-V`, Docker reuses stale volumes and new packages will be missing.
- **Env vars:** `docker compose restart` does NOT re-read `env_file`. Use `docker compose up -d` to recreate the container with updated env vars.

---

## 2. Git Workflow & Communication

### Commit Standards

- **Commit Often:** Provide granular commits that explain intent.
- **Format:** Use prefixes: `Feature:`, `Fix:`, `Chore:`, `Test:`.
- **Branching:** Always use `main` as the primary branch (or `master` if explicitly configured).

### Inter-Agent Communication

- **Handovers across sessions or agents:** When a task spans multiple sessions, or when one agent hits a blocker that needs another agent's expertise, document the state in `IMPLEMENTATION_PLAN.md` so the next agent can pick up without re-deriving context.
- **Second-opinion reviews:** for a non-Claude review of code, a PR, or an architecture decision, invoke the `agent-code-reviewer` skill (wraps `cli/agent_code_reviewer.py`). The skill encodes when a second opinion earns its token cost, which provider to pick (Gemini default, Codex for novel-subsystem architecture critique), and how to weight the reviewer's output against your own conviction. The script gives feedback only — it never writes code.
- **PR comment attribution.** When more than one AI agent reviews PRs (e.g. Claude + Gemini + Copilot), prepend a bracketed tag to each comment so authors can distinguish them from human reviewers and from each other: `**[CLAUDE]**`, `**[GEMINI]**`, `**[COPILOT]**`. Apply the same convention in inline code-review comments and replies.

---

## 3. Global Constraints & Anti-Patterns (DO NOTs)

- **No Shortcuts:** Do not skip accessibility, i18n, or type safety for speed.
- **No Hardcoding:** Never hardcode strings, colors, or secrets.
- **No "Bandaids":** Do not use `any`, `ts-ignore`, `as any`, or `as unknown` casts to silence type errors. Reach for Zod-parsed types, branded types, or type guards first. If a cast is genuinely necessary at a system boundary (e.g. parsing untyped JSON), document the why inline.
- **No Verbosity:** Avoid unnecessary abstractions or "heavy" boilerplate. Keep it "skinny."
- **No Sync Bulk Processing:** Never perform unbounded bulk processing inside synchronous API routes; use background workers (e.g., SQS + Lambda, or similar queue-based patterns).
- **No Database Resets:** Never reset, drop, or wipe the database — not even in development. All schema changes must go through migrations. If data needs to be backfilled or transformed, write a migration or seed script.
- **No Unscoped Queries:** Never fetch unbounded data sets (e.g., all records in a table). Always scope queries with filters, pagination, or ownership constraints. Design for production scale from day one.
- **Security:** Never commit API keys or secrets to source control. Use `.env` files locally and a secrets manager (e.g., VestAuth, Vault, or platform-native env vars) for production.
- **No New Env Vars — Splatter Causes Spaghetti:** Adding a new env var is rarely the right answer. Every new var is permanent overhead in every environment (dev, staging, prod, CI, every developer machine, every fork), and a single misconfigured environment becomes a silent runtime failure with no traceback. Env-var splatter compounds: a codebase with 80 env vars is unrecoverable. Before adding one, you MUST exhaust these alternatives in order: (1) reuse an existing var, (2) hardcode a constant if the value never differs across environments, (3) derive it from existing config (e.g. `NODE_ENV === "production"`), (4) put it in a versioned config file checked into the repo. Only after all four fail is a new env var justified — and the justification (purpose, who reads it, rotation cadence) must be added to `ARCHITECTURE.md` in the same commit, not later.
