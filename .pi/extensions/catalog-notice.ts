/**
 * Reviewer catalog notice for pi, the counterpart of the SessionStart hook in
 * .claude/settings.json. At session start it runs the roster's catalog check,
 * shows the report to the user, and hands it to the model with the first prompt.
 * A check that cannot run says so, so a broken check never reads as a quiet day.
 */

import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join } from 'node:path';

const SCRIPT = join('cli', 'agent_code_reviewer.py');

interface CheckResult {
  code: number;
  stdout: string;
  stderr: string;
}

async function runCheck(cwd: string): Promise<CheckResult> {
  return new Promise((resolveResult, rejectResult) => {
    const child = spawn('uv', ['run', '--quiet', join(cwd, SCRIPT), '--catalog-notice'], {
      cwd,
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => {
      stdout += String(chunk);
    });
    child.stderr.on('data', (chunk) => {
      stderr += String(chunk);
    });
    // ENOENT here means uv is not installed.
    child.on('error', rejectResult);
    child.on('close', (code) =>
      resolveResult({ code: code ?? 0, stdout: stdout.trim(), stderr: stderr.trim() }),
    );
  });
}

export default function (pi: ExtensionAPI) {
  let report = '';

  pi.on('session_start', async (_event, ctx) => {
    report = '';
    if (!existsSync(join(ctx.cwd, SCRIPT))) return;

    let result: CheckResult;
    try {
      result = await runCheck(ctx.cwd);
    } catch (error) {
      result = { code: -1, stdout: '', stderr: String(error) };
    }
    report =
      result.code === 0
        ? result.stdout
        : `Reviewer catalog check failed (exit ${result.code}), so models newer than the ` +
          `roster go unreported: ${result.stderr.split('\n').slice(-3).join(' ')}`;
    if (report && ctx.hasUI) ctx.ui.notify(report, 'warning');
  });

  pi.on('before_agent_start', async () => {
    if (!report) return undefined;
    const content = report;
    report = '';
    return { message: { customType: 'catalog-notice', content, display: false } };
  });
}
