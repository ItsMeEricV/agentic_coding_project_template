#!/usr/bin/env bash
#
# Installs a pinnable Chrome for Testing build and prints the binary path plus
# ready-to-use chrome-devtools-mcp config snippets (headless by default, or
# headed with HEADED=1).
#
# Usage:
#   ./setup_chrome.sh [channel-or-version]
#
# Examples:
#   ./setup_chrome.sh                 # latest stable Chrome for Testing
#   ./setup_chrome.sh beta            # latest beta
#   ./setup_chrome.sh 131             # latest build in milestone 131
#   ./setup_chrome.sh 131.0.6778.85   # an exact version
#
# Env:
#   CHROME_FOR_TESTING_DIR  Install/cache dir (default: $HOME/.cache/chrome-for-testing)
#   INSTALL_DEPS=1          On Ubuntu/Debian, also install system deps (needs sudo/root)
#   HEADED=1                Emit config WITHOUT --headless (visible window). Needs a
#                           display — won't work over SSH/CI without e.g. Xvfb.
#                           Default is headless.

set -euo pipefail

CHANNEL="${1:-stable}"
CACHE_DIR="${CHROME_FOR_TESTING_DIR:-$HOME/.cache/chrome-for-testing}"

# Headless by default; HEADED=1 drops --headless from the emitted config.
if [ "${HEADED:-0}" = "1" ]; then
  MODE_DESC="headed (visible window)"
  CLI_HEADLESS=""
  JSON_HEADLESS=""
else
  MODE_DESC="headless"
  CLI_HEADLESS="--headless "
  JSON_HEADLESS=$'        "--headless",\n'
fi

command -v node >/dev/null 2>&1 || { echo "ERROR: Node.js (LTS) is required but not found." >&2; exit 1; }
command -v npx  >/dev/null 2>&1 || { echo "ERROR: npx is required but not found." >&2; exit 1; }

mkdir -p "$CACHE_DIR"

DEPS_FLAG=""
if [ "${INSTALL_DEPS:-0}" = "1" ]; then
  DEPS_FLAG="--install-deps"
fi

echo "Installing Chrome for Testing (chrome@${CHANNEL}) into ${CACHE_DIR} ..." >&2

# @puppeteer/browsers prints a final stdout line of the form:
#   chrome@<version> <absolute-path-to-binary>
# (download progress goes to stderr). We grep for that line so stray npm
# warnings or deprecation notices on stdout can't be mistaken for the path.
INSTALL_OUTPUT="$(npx -y @puppeteer/browsers install "chrome@${CHANNEL}" --path "$CACHE_DIR" ${DEPS_FLAG})"
echo "$INSTALL_OUTPUT" >&2

# The path may contain spaces (e.g. macOS "Google Chrome for Testing.app"),
# so take everything after the first space, not just field 2.
CHROME_PATH="$(printf '%s\n' "$INSTALL_OUTPUT" | grep -E '^chrome[@ ]' | tail -n1 | cut -d' ' -f2-)"

if [ -z "$CHROME_PATH" ] || [ ! -e "$CHROME_PATH" ]; then
  echo "ERROR: could not determine the Chrome for Testing binary path from the install output." >&2
  exit 1
fi

cat >&2 <<EOF

Chrome for Testing is ready.
  Binary: $CHROME_PATH
  Mode:   $MODE_DESC

--- Claude Code (register the MCP server, user scope) ------------------------
claude mcp add chrome-devtools --scope user -- \\
  npx -y chrome-devtools-mcp@latest \\
  ${CLI_HEADLESS}--isolated --executable-path "$CHROME_PATH"

--- Generic MCP client (JSON config) ----------------------------------------
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "-y",
        "chrome-devtools-mcp@latest",
${JSON_HEADLESS}        "--isolated",
        "--executable-path=$CHROME_PATH"
      ]
    }
  }
}
-----------------------------------------------------------------------------
EOF

# Emit just the path on stdout so callers can capture it:
#   CHROME_PATH="$(./setup_chrome.sh)"
echo "$CHROME_PATH"
