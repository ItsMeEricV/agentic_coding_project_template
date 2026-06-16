# chrome-devtools-mcp Reference

Companion to `../SKILL.md`. Tool names and flags below are verified against
`chrome-devtools-mcp` (npm `@latest`) and its
[tool reference](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md).
`npx chrome-devtools-mcp@latest --help` is always authoritative for your installed version.

## Tools

A default headless launch exposes ~29 tools. Categories:

### Input automation
`click` · `click_at` (needs `--experimental-vision`) · `drag` · `fill` · `fill_form`
· `handle_dialog` · `hover` · `press_key` · `type_text` · `upload_file`

### Navigation
`navigate_page` (`{ url }`) · `new_page` · `list_pages` · `select_page` ·
`close_page` · `wait_for` (wait for text to appear)

### Emulation
`emulate` (CPU/network throttling, geolocation, etc.) · `resize_page`

### Debugging & inspection
`take_snapshot` (accessibility tree with stable `uid=` refs — the cheap default for
deciding what to click) · `take_screenshot` (pixels) · `evaluate_script` (run JS in
page) · `list_console_messages` · `get_console_message` · `lighthouse_audit`

### Network
`list_network_requests` · `get_network_request`

### Performance
`performance_start_trace` · `performance_stop_trace` · `performance_analyze_insight`

### Behind flags (off by default)
- **Memory** (`--memory-debugging`): `take_heapsnapshot`, `get_heapsnapshot_*`,
  `close_heapsnapshot`
- **Extensions** (`--category-extensions`): `install_extension`, `list_extensions`,
  `reload_extension`, `trigger_extension_action`, `uninstall_extension`
- **Screencast** (`--experimental-screencast`, needs ffmpeg): `screencast_start`,
  `screencast_stop`
- **Third-party / WebMCP**: `execute_3p_developer_tool`, `list_3p_developer_tools`,
  `execute_webmcp_tool`, `list_webmcp_tools`

### Typical interaction loop
`take_snapshot` → read `uid=` of target → `click`/`fill`/`type_text` with that uid →
`wait_for` next state → repeat. Use `take_screenshot` only when you need to see pixels.

## Command-line flags

Flags accept kebab-case or camelCase (`--executable-path` == `--executablePath`).

### Choosing the browser
| Flag | Purpose |
|------|---------|
| `--executable-path`, `-e` | Path to a custom Chrome binary (use the pinned Chrome for Testing build). |
| `--channel <stable\|beta\|dev\|canary>` | Use the **system-installed** Chrome of that channel. Drifts with OS updates; fails if not installed. |
| `--browser-url`, `-u` | Connect to an already-running Chrome (`http://127.0.0.1:9222`). For sandboxes / anti-bot. |
| `--ws-endpoint`, `-w` | Connect via WebSocket (`ws://…/devtools/browser/<id>`); `--ws-headers` for auth. |
| `--auto-connect` | Attach to a local Chrome 144+ started from the channel's user-data-dir. |

### Run mode
| Flag | Purpose |
|------|---------|
| `--headless` | No UI (headless). Default here; best for agents/CLI/CI. **Omit** it to run headed (visible window) — needs a display, so not over SSH/CI without Xvfb. |
| `--isolated` | Throwaway user-data-dir, auto-cleaned on close. Clean state; safe in parallel. |
| `--user-data-dir <path>` | Persistent profile (keep a logged-in session). Mutually exclusive with the point of `--isolated`. |
| `--viewport <WxH>` | Initial viewport, e.g. `1280x720`. Headless max 3840x2160. |
| `--proxy-server <addr>` | Route Chrome through a proxy. |
| `--accept-insecure-certs` | Ignore self-signed/expired certs. Use with caution. |
| `--chrome-arg=<arg>` | Extra Chrome flag (repeatable), e.g. `--chrome-arg=--no-sandbox` on locked-down Linux. |

### Scoping & safety
| Flag | Purpose |
|------|---------|
| `--slim` | Expose only 3 tools (navigate, evaluate_script, screenshot). Cheap for basic tasks. |
| `--no-category-emulation` / `--no-category-performance` / `--no-category-network` | Drop a tool category. |
| `--allowed-url-pattern` / `--blocked-url-pattern` | Restrict network to/away from URL patterns. Good for scraping safety. |
| `--redact-network-headers` | Redact sensitive headers before returning to the client. |

### Privacy & diagnostics
| Flag | Purpose |
|------|---------|
| `--no-usage-statistics` | Opt out of Google usage stats (or `CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS=1`; auto-off under `CI`). |
| `--no-performance-crux` | Stop performance tools sending trace URLs to the CrUX API. |
| `--log-file <path>` | Write debug logs to a file. Set `DEBUG=*` for verbose. |

## Headless gotchas

- **Browser launches lazily** — the process starts on the first tool that needs it,
  not at server connect. A connected server with no browser is normal.
- **Native dialogs hang silently** — there's no human to dismiss `alert`/`confirm`/auth
  prompts. Call `handle_dialog`.
- **Linux system libs** — Chrome needs shared libs not always present in minimal
  images. `INSTALL_DEPS=1 bash scripts/setup_chrome.sh` (Debian/Ubuntu, needs root)
  or install equivalents. `--chrome-arg=--no-sandbox` only if you can't get root
  (reduces isolation).
- **Anti-bot / login walls** may block the automation-launched Chrome. Launch Chrome
  yourself with `--remote-debugging-port=9222` and attach via `--browser-url`.
- **Reproducibility** — pin an exact Chrome for Testing version (`setup_chrome.sh 131.0.6778.85`)
  rather than `--channel`, so an OS Chrome update can't change behavior under you.
