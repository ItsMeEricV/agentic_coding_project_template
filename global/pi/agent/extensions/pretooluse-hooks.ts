/**
 * PreToolUse guards for pi.
 *
 * pi has no Claude-style hooks config, so this extension calls the same shell
 * scripts Claude Code runs as PreToolUse. One implementation of each rule, two
 * agents. The scripts speak Claude's hook contract — JSON on stdin, exit 2 plus
 * stderr to block — so this file only translates pi's tool events into that
 * shape and maps exit 2 back onto pi's `{ block: true }`.
 *
 * To give a new PreToolUse hook pi coverage, add its filename to GUARDS.
 */

import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, resolve } from 'node:path';

const HOOK_DIR = join(homedir(), '.claude', 'hooks');

// pi tool -> the hooks/ scripts that guard it, run in order until one blocks.
const GUARDS: Record<string, string[]> = {
  edit: ['enforce-worktree-boundary.sh'],
  write: ['enforce-worktree-boundary.sh'],
  bash: ['enforce-worktree-boundary-bash.sh'],
};

// The scripts match on Claude's tool names, so report those rather than pi's.
const CLAUDE_TOOL_NAMES: Record<string, string> = { edit: 'Edit', write: 'Write', bash: 'Bash' };

interface HookResult {
  code: number;
  stderr: string;
}

async function runHook(script: string, payload: unknown, cwd: string): Promise<HookResult> {
  return new Promise((resolveResult, rejectResult) => {
    const child = spawn(join(HOOK_DIR, script), { cwd, stdio: ['pipe', 'ignore', 'pipe'] });
    let stderr = '';
    child.stderr.on('data', (chunk) => {
      stderr += String(chunk);
    });
    child.on('error', rejectResult);
    child.on('close', (code) => resolveResult({ code: code ?? 0, stderr: stderr.trim() }));
    child.stdin.end(JSON.stringify(payload));
  });
}

export default function (pi: ExtensionAPI) {
  pi.on('tool_call', async (event, ctx) => {
    const scripts = GUARDS[event.toolName];
    if (!scripts) return undefined;

    // The scripts read absolute paths; pi hands us paths relative to the session.
    const input = event.input as { path?: string; command?: string };
    const payload = {
      cwd: ctx.cwd,
      hook_event_name: 'PreToolUse',
      tool_name: CLAUDE_TOOL_NAMES[event.toolName] ?? event.toolName,
      tool_input:
        event.toolName === 'bash'
          ? { command: input.command }
          : { file_path: input.path ? resolve(ctx.cwd, input.path) : undefined },
    };

    for (const script of scripts) {
      if (!existsSync(join(HOOK_DIR, script))) continue;

      let result: HookResult;
      try {
        result = await runHook(script, payload, ctx.cwd);
      } catch (error) {
        // Fail open, but say so — a silent guard is worse than none.
        if (ctx.hasUI) {
          ctx.ui.notify(`hook ${script} failed to run (${String(error)})`, 'warning');
        }
        continue;
      }

      if (result.code === 2) {
        return { block: true, reason: result.stderr || `Blocked by ${script}.` };
      }
      if (result.code !== 0 && ctx.hasUI) {
        ctx.ui.notify(`hook ${script} exited ${result.code}; allowing.`, 'warning');
      }
    }
    return undefined;
  });
}
