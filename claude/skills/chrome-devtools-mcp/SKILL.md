---
name: chrome-devtools-mcp
description: Use when driving, automating, testing, debugging, scraping, screenshotting, or performance-profiling a web page from an agent or the command line via the Chrome DevTools MCP server (chrome-devtools-mcp) on a pinned Chrome for Testing build, headless or headed. Triggers on "headless browser", "headed browser", "browser automation", "Chrome DevTools MCP", "Chrome for Testing", "screenshot a site", "check console errors", "capture network requests", "record a performance trace", "Lighthouse audit", or "drive Chrome programmatically" — even when only the goal is described (e.g. "automate filling this form").
---

# Chrome via Chrome DevTools MCP (headless or headed)

Wires [`chrome-devtools-mcp`](https://github.com/ChromeDevTools/chrome-devtools-mcp)
to a pinned **Chrome for Testing** binary, run **headless by default** (or headed —
see step 2). The MCP server (built on Puppeteer) exposes Chrome DevTools as agent
tools: navigation, clicking/typing, screenshots, accessibility snapshots, console +
network inspection, performance traces, and Lighthouse audits.

Use Chrome for Testing rather than system Chrome because it is versioned and does
**not** auto-update — runs stay reproducible. `chrome-devtools-mcp` officially
supports Google Chrome and Chrome for Testing only.

**Pinning vs. `--channel`:** the server's `--channel stable|beta|dev|canary` flag
uses whatever Chrome of that channel is *installed on the system* — version
drifts as the OS updates it, and it fails if none is installed. Installing a
specific Chrome for Testing build and passing `--executable-path` is what makes
runs self-contained and reproducible. That is what this skill sets up.

## When to do what

- **No `chrome-devtools` MCP server registered yet** → run the Setup workflow.
- **Already set up, doing browser work** → skip to "Driving the browser" and call
  the MCP tools.
- **Setup failing** → see Troubleshooting.

## Prerequisites

- Node.js **LTS** and npm on PATH (`node -v`, `npx -v`).
- Network access to download Chrome for Testing (~150 MB) and to `npx` the package.
- On headless Linux, Chrome's system libraries (see Troubleshooting).

## Setup workflow

### 1. Install Chrome for Testing

The bundled script installs the latest **stable** Chrome for Testing, prints the
binary path on **stdout**, and prints ready-to-paste MCP config on **stderr**:

```bash
CHROME_PATH="$(bash scripts/setup_chrome.sh)"
```

Pass a channel or version to pin something specific: `stable` (default), `beta`,
`dev`, `canary`, a milestone like `131`, or an exact version like `131.0.6778.85`.
The script wraps `npx @puppeteer/browsers install chrome@<channel>` — the canonical
way to fetch Chrome for Testing — and caches under `$HOME/.cache/chrome-for-testing`.
It also prints the registration snippets for step 2; run it with `HEADED=1` to get
the headed variants.

### 2. Register the MCP server

Pin the server with `@latest`, point it at the binary from step 1. **Headless is the
default** — best for agents, CLIs, CI, and remote/SSH machines with no display.

**Claude Code** (user scope, available across projects):

```bash
claude mcp add chrome-devtools --scope user -- \
  npx -y chrome-devtools-mcp@latest \
  --headless --isolated --executable-path "$CHROME_PATH"
```

**Any other MCP client** — add to its MCP config (each `args` value is its own
array entry; flags accept kebab-case or camelCase):

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "-y",
        "chrome-devtools-mcp@latest",
        "--headless",
        "--isolated",
        "--executable-path=/absolute/path/to/chrome-for-testing"
      ]
    }
  }
}
```

**Headless vs. headed:** the snippets above are headless (the `--headless` flag).
To run **headed** — a visible Chrome window, useful for watching automation or
debugging locally — simply **omit `--headless`** (or generate the snippets with
`HEADED=1 bash scripts/setup_chrome.sh`). Headed needs a real display, so it won't
work over SSH or in CI without a virtual display (e.g. Xvfb on Linux). Everything
else about driving the browser is identical in both modes.

`--isolated` gives each run a throwaway profile (clean state, safe for parallel
sessions). For a persistent logged-in profile, drop it and add
`--user-data-dir=<path>`. Add `--viewport=1280x720` for deterministic layout.

**Privacy:** the server sends anonymous usage stats to Google, and performance
tools send trace URLs to the CrUX API. Add `--no-usage-statistics`
`--no-performance-crux` (or set `CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS=1`; both
auto-disable when `CI` is set) to opt out.

In Claude Code, restart the session (or `/mcp` reconnect) so the server loads, then
confirm the `chrome-devtools` tools are listed.

### 3. Smoke test

Ask the running agent:

> Navigate to https://example.com and take a snapshot.

It should launch headless Chrome for Testing and return an accessibility snapshot
with `uid=` element references. The browser starts lazily — it won't launch until
the first tool that needs it is called.

## Driving the browser

- To decide what to interact with, prefer **`take_snapshot`** (accessibility-tree
  text with stable element UIDs like `uid=1_3`) over `take_screenshot`. It's cheaper
  and gives the references you pass to `click`, `fill`, `hover`, etc. Use
  `take_screenshot` only when you need pixels.
- Forms: `fill_form` sets multiple fields in one call; `fill` / `type_text` for a
  single input. `press_key` for keyboard, `upload_file` for file inputs.
- Multiple tabs: `new_page`, `list_pages`, `select_page`, `close_page`. Wait for
  page state with `wait_for` (text appears). Run JS with `evaluate_script`.
- Debugging a page: `list_console_messages` + `list_network_requests`, then
  `get_network_request` for one request's detail.
- Performance: `performance_start_trace` → load/interact → `performance_stop_trace`
  → `performance_analyze_insight`. `lighthouse_audit` gives a scored report.
- Always `handle_dialog` for native prompts (alert, confirm, auth, geolocation) —
  there's no human to click them in headless mode.

Full tool list, every flag, and headless gotchas are in
[`references/mcp-reference.md`](references/mcp-reference.md). Read it when you need a
tool not covered above or need to tune flags. `npx chrome-devtools-mcp@latest --help`
is authoritative.

## Troubleshooting

- **`claude mcp add` not available** → use the JSON config form for the MCP client
  in use.
- **Server connects but browser never launches** → expected until a
  browser-requiring tool is called. Trigger one (e.g. navigate).
- **Chrome fails to start on headless Linux** with missing-library errors → install
  Chrome's system deps. On Ubuntu/Debian: `INSTALL_DEPS=1 bash scripts/setup_chrome.sh`
  (needs sudo/root). In a sandbox without root, install the equivalent libs via the
  environment's own mechanism. As a last resort, add
  `--chrome-arg=--no-sandbox` (reduces isolation — use with caution).
- **Login/anti-bot blocks the automated Chrome** → start Chrome manually with
  `--remote-debugging-port=9222 --user-data-dir=<temp dir>` and register with
  `--browser-url=http://127.0.0.1:9222` instead of `--executable-path`. See the
  README's "Connecting to a running Chrome instance".
- **Wrong/old Chrome used** → confirm `--executable-path` points at the Chrome for
  Testing binary from the script, not system Chrome.
- **Download slow/blocked** → the binary caches under `$HOME/.cache/chrome-for-testing`
  (override with `CHROME_FOR_TESTING_DIR`); reuse it across machines.
