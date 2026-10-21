"""Every MCP server a skill names must resolve under pi too.

pi loads the same skills as Claude Code (`~/.claude/skills`), so a skill naming
`mcp__<server>__<tool>` breaks there unless `global/pi/agent/mcp.json` declares
<server>. Skipped where those files are absent (forks copy `cli/` alone).

Run with: python3 -m unittest cli.test_skill_mcp_servers -v
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "claude" / "skills"
PI_MCP = REPO / "global" / "pi" / "agent" / "mcp.json"
# Anthropic-managed skills synced from claude.ai; they target Claude-only servers.
SYNCED = SKILLS / "synced"

SERVER_REF = re.compile(r"mcp__([A-Za-z0-9_-]+?)__")


def referenced_servers(text: str) -> set[str]:
    return set(SERVER_REF.findall(text))


class ReferencedServersTest(unittest.TestCase):
    def test_extracts_server_names(self) -> None:
        text = "Call `mcp__github__create_pull_request`, then mcp__foo_bar__x; not mcp__<server>__."
        self.assertEqual(referenced_servers(text), {"github", "foo_bar"})

    def test_keeps_hyphens(self) -> None:
        self.assertEqual(referenced_servers("mcp__claude-in-chrome__tabs"), {"claude-in-chrome"})


@unittest.skipUnless(SKILLS.is_dir() and PI_MCP.is_file(), "skills or pi mcp.json not in checkout")
class SkillServersResolveUnderPiTest(unittest.TestCase):
    def test_every_referenced_server_is_declared_for_pi(self) -> None:
        # pi treats `-` and `_` in server names as the same server.
        declared = {name.replace("-", "_") for name in json.loads(PI_MCP.read_text())["mcpServers"]}
        problems: list[str] = []
        for path in sorted(SKILLS.rglob("*.md")):
            if SYNCED in path.parents:
                continue
            rel = path.relative_to(REPO)
            for name in sorted(referenced_servers(path.read_text())):
                if "-" in name:
                    # pi rewrites non-word characters in tool names to `_`.
                    problems.append(f"{rel}: mcp__{name}__ never resolves under pi; use `_`")
                elif name not in declared:
                    problems.append(f"{rel}: server `{name}` is not in {PI_MCP.relative_to(REPO)}")
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
