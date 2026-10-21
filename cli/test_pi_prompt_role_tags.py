"""Text pi sends to OpenRouter must not contain chat role tags.

OpenRouter rejects any request whose prompt holds `<system>`, `<assistant>`,
`<tool>`, `<developer>` or `<function>` (open or closing) with a 403
"prompt injection patterns detected", so one placeholder like
`mcp__github__<tool>` in a rules file breaks every pi prompt. `<user>` and
`<tools>` pass. Skipped where those files are absent (forks copy `cli/` alone).

Run with: python3 -m unittest cli.test_pi_prompt_role_tags -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# pi's global context files, plus every skill it can load from `~/.claude/skills`.
PROMPT_FILES = [REPO / "global" / "AGENTS.md", REPO / "global" / "pi" / "agent" / "APPEND_SYSTEM.md"]
SKILLS = REPO / "claude" / "skills"

ROLE_TAG = re.compile(r"</?(system|assistant|tool|developer|function)>", re.I)


def role_tags(text: str) -> list[str]:
    return [m.group(0) for m in ROLE_TAG.finditer(text)]


class RoleTagsTest(unittest.TestCase):
    def test_flags_blocked_tags(self) -> None:
        text = "names `mcp__github__<tool>`, </system>, <Assistant>"
        self.assertEqual(role_tags(text), ["<tool>", "</system>", "<Assistant>"])

    def test_passes_tags_openrouter_allows(self) -> None:
        self.assertEqual(role_tags("<user> <tools> <server> <name> mcp__github__*"), [])


@unittest.skipUnless(SKILLS.is_dir() and all(p.is_file() for p in PROMPT_FILES), "pi prompt files not in checkout")
class PiPromptFilesTest(unittest.TestCase):
    def test_no_role_tags_in_pi_prompt_files(self) -> None:
        problems: list[str] = []
        for path in [*PROMPT_FILES, *sorted(SKILLS.rglob("*.md"))]:
            for tag in role_tags(path.read_text()):
                problems.append(f"{path.relative_to(REPO)}: `{tag}` gets every pi request blocked by OpenRouter")
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
