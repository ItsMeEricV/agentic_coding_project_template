## General DO

- Always use `rg` , not `grep`
- When designing systems with UUID type unique keys, always default to the UUIDv7 format. E.g. `id String @id @default(uuid(7))` in Postgres.

### Github interactions

- Always use the `gh` cli tool for interacting with remote Github

### ⚠️ CRITICAL: Always start new work from a clean branch off master

### Branch Naming Format

All new branches MUST follow this format:

```text
ev-<description>
```

Examples:

- `ev-hidden-channels-modal`
- `ev-bugfix-section-header`
- `ev-refactor-search-api`

### Creating New Branches (AUTOMATED WORKFLOW)

**When I ask you to create a new branch or start new work, ALWAYS execute these steps automatically:**

1. **Check current status**: Run `git status` to see current branch
2. **Switch to main and ensure it's clean**: Run `git checkout master`
3. **Pull latest changes**: Run `git pull origin master` (or just `git pull`)
4. **Verify master is up to date**: Check the pull output to confirm "Already up to date" or successful pull
5. **Create new branch**: Run `git checkout -b ev-<description>`
   - Use hyphens (not underscores) to separate words
   - Keep description concise and descriptive

```bash
# Complete workflow (run these commands in sequence):
git status
git checkout master
git pull
git checkout -b ev-<description>
```

**Why this matters**:

- Clean commit history in PRs (only your changes)
- No unrelated commits from other feature branches
- Easier code review for teammates
- Cleaner git history overall

### Commit and Push Workflow

### ⚠️ CRITICAL: Automatically commit and push after each completed change

**If tests fail**: First attempt to fix them yourself. If you cannot resolve the failure, stop and ask the user how to proceed — do not commit, push, or continue with other work while tests are failing.

After verifying that formatting, linting, and type checks pass:

1. **Commit immediately** — don't wait for the user to ask. Make sure you only commit the files for your persona! For example, if you are a backend engineer then only commit files assigned to your in AGENTS.md/CLAUDE.md
2. **One commit per logical change** — keep commits focused and atomic for a clean history
3. **Push after each commit**
4. **Use descriptive commit messages** — explain the "what" concisely
5. **Do not open a pull request until the user asks you to** - We want to keep the momentum flowing. When the user asks for a PR then use the `Guidelines for PR descriptions` below.

**Why this matters**:

- No giant "do everything" commits that are hard to understand
- Changes are pushed promptly so CI runs and reviewers see progress

**Guidelines for PR descriptions**:

- Use conversational, detailed bullet points
- Include inline descriptions in Before/After screenshots
- Add dev preview links with force parameters when applicable
- Focus on reviewer experience - give them context
- Add blank line after each header before content
- Only include sections that are relevant
- Add a Co-Authored-By line using your current model version (e.g. Co-Authored-By: Claude 4.6)
- Do NOT add `---` separator lines
- **Always use descriptive link text** - never use naked URLs
  - ❌ Bad: `https://slack-pde.slack.com/archives/CUV8P3GUA/p1768922402598969`
  - ✅ Good: `[Internal user report about missing "Mark as read" option](https://slack-pde.slack.com/archives/CUV8P3GUA/p1768922402598969)`
- **Note for reviewers about commit-by-commit review**: Add a note in "Notes for Reviewers" that commits can be reviewed individually since each commit contains focused, individual changes
  - Example: "**Commit-by-commit review**: Each commit is self-contained and can be reviewed individually for easier review"

## Code Style & Formatting

- **Formatter:** Always use **Prettier** for all `.ts`, `.tsx`, `.js`, `.json`, `.jsonc`, and `.css` files.
- **Execution:** After modifying or creating a file, run `npx prettier --write <file_path>` to ensure the disk version matches the project's style.
- **Rules:** Respect the project's `.prettierrc` file. Do not use internal LLM formatting if it contradicts the local Prettier config.
- **Verification:** If a "lint" or "format" step fails during a build, automatically run the Prettier fix command before reporting the error.
- **rg:** Always use `rg`, not `grep`.

## Anti-patterns:
