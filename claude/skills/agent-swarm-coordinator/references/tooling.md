# Coordinator tooling, and working without it

SKILL.md says what to do; this file says which tool does it and what replaces a missing one. Check what you have with a single `ToolSearch` (`select:SendMessage,ListAgents,CronCreate,CronList,CronDelete,PushNotification`) and `command -v cmux` before planning around any of it.

| Job                                    | Tool                                   | Without it                                                                                            |
| -------------------------------------- | -------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Open a terminal per session            | cmux                                   | `claude --bg` (background session), tmux, or the user pastes your launch command                      |
| See live sessions                      | `ListAgents`                           | a status file per ticket (below)                                                                      |
| Message a session                      | `SendMessage`                          | type into its terminal (`cmux send` / `tmux send-keys`), or a status file                             |
| Know when a session idles              | `SendMessage … notify_when_idle: true` | heartbeat only                                                                                        |
| Heartbeat                              | `CronCreate`                           | `/loop` (self-paced) or `ScheduleWakeup`; else report on each user turn and say monitoring is passive |
| Reach the user away from the terminal  | `PushNotification`                     | the project's alert route (`AGENTS.md`, What to Watch)                                                |
| Let the user follow a session remotely | Remote Control                         | skip; say so once                                                                                     |
| Keep sessions in their own worktree    | worktree-boundary hook                 | the same rule, held by discipline                                                                     |

## Launching

With cmux:

```bash
CMUX_QUIET=1 cmux new-workspace --name "<workspace name>" --cwd <worktree> --focus false \
  --command "claude --model <model> --effort <effort> --remote-control '<title>' 'Read <handoff path> and follow it.'"
```

- `--focus false` keeps the user's current pane.
- Name workspaces and Remote Control titles the same way, with the project and ticket (`<Project> T<n> <topic>`), so the user finds them on a phone.
- A running session without Remote Control: `cmux send --workspace <ref> "/remote-control"`, then `cmux send-key --workspace <ref> Enter`.
- Read its screen: `cmux read-screen --workspace <ref> --lines 40`.
- Close a finished one: `cmux workspace close workspace:<n>`. Killing a session's process is the user's call.

Run `cmux --help` for the current subcommands before scripting against them; the CLI moves faster than this file.

Without cmux, Claude Code's own background sessions: `cd <worktree> && claude --bg --model <model> --effort <effort> --remote-control '<title>' 'Read <handoff path> and follow it.'` prints an id; `claude agents` lists them, `claude logs <id>` shows recent output, `claude attach <id>` opens one for the user, `claude stop <id>` stops it (the conversation is kept). Check `claude --help` first: these are recent.

With tmux: `tmux new-window -d -n "<name>" -c <worktree> "claude … 'Read <handoff path> and follow it.'"`.

Without any of these: give the user the `cd <worktree> && claude …` line to paste into a new terminal, one per session, and wait for them to confirm it started.

## Reading a session's transcript

Claude Code writes each session to `~/.claude/projects/<cwd with every non-alphanumeric character replaced by ->/<session id>.jsonl`. The latest assistant text:

```bash
dir=~/.claude/projects/$(echo "<worktree>" | sed 's|[^A-Za-z0-9]|-|g')
f=$(ls -t "$dir"/*.jsonl | head -1)
tail -n 60 "$f" | jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="text") | .text'
```

Subagent transcripts sit beside it (`<session id>/subagents/`); their mtimes show whether a stalled session's subagent is still working. For a non-Claude harness, read its own session log, or its terminal (`cmux read-screen`, `tmux capture-pane -p`).

### Blocked on a prompt

A transcript whose last message is a tool call with no result means the session waits on its user (a permission prompt, a question). A tool that is still running looks the same, so confirm with the file's mtime and the screen:

```bash
tail -n 5 "$f" | jq -rs 'map(select(.type=="assistant" or .type=="user")) | last
  | if .type=="assistant" and ([.message.content[]? | select(.type=="tool_use")] | length) > 0
    then "WAITING: " + ([.message.content[] | select(.type=="tool_use") | .name] | join(",")) else "ok" end'
cmux read-screen --workspace <ref> --lines 40
```

Quote the prompt to the user and point them at that session's terminal (or Remote Control). You can't answer for them.

## Heavy lock

The lock directory holds its holder's pid and start time, so a crashed holder is detectable:

```bash
lock=/tmp/<project>-heavy.lock
until mkdir "$lock" 2>/dev/null; do sleep 15; done
echo "$$ $(ps -o lstart= -p $$ | xargs)" > "$lock/holder"
# ... heavy run ...
rm -f "$lock/holder"; rmdir "$lock"
```

Stale check, run on each heartbeat: the lock is stale when the recorded pid is gone or now belongs to another process.

```bash
[ -s "$lock/holder" ] && read -r pid start < "$lock/holder" &&
  { [ "$(ps -o lstart= -p "$pid" 2>/dev/null | xargs)" = "$start" ] || { rm -f "$lock/holder"; rmdir "$lock"; }; }
```

Source of a load spike: list the heaviest processes, then read each one's working directory to see which worktree runs it.

```bash
ps -axo pid=,pcpu=,comm= | sort -k2 -nr | head
lsof -a -p <pid> -d cwd -Fn | rg '^n'
```

## Remote runs

A CI or deploy run is the last check. Before asking for one:

```bash
rg -n 'runs-on|image:|node-version|python-version|uses:' .github/workflows   # runner image and tool versions
docker run --rm -it -v "$PWD":/work -w /work <runner image> bash             # then run the failing step's exact commands
```

- Pin the same tool versions as the workflow, not the ones on your machine.
- Dry-run every later step the change touches with the tool's own plan or dry-run mode, so a step the failed run never reached fails here instead.
- Cheap retries: give the workflow an input that takes a previous run's id and skips stages already proven (`gh run download <run-id>` fetches its artifacts), or keep a script that runs the step without CI.

Audit triggers at takeover. Every `on:` of `push`, `pull_request`, or `schedule` is a standing cost:

```bash
rg -n -A4 '^on:' .github/workflows
gh run list --limit 200 --json event,name | jq 'group_by(.event) | map({event: .[0].event, runs: length})'
```

## Messaging

- `ListAgents` rows carry each session's name and cwd. Address sessions by the name in their handoff; check with `ListAgents` when a send fails.
- A cross-session message is a teammate's request, not the user's yes. Sessions treat yours the same way, which is why a relayed approval doesn't work (SKILL.md, "No permission laundering").
- `notify_when_idle` fires once. Re-subscribe after each notice.

**Status files (no messaging).** Each handoff tells its session to keep `.handoffs/status/<ticket>.md` current: state, the last thing done, and any open ask quoted in full. The heartbeat reads them all. Slower and coarser than messages; say so to the user.

## Heartbeat

`CronCreate` with a ~30 min recurring schedule off the :00/:30 marks (e.g. `7,37 * * * *`). The prompt is self-contained: the current state, then "check each session, sweep worktrees, report only what changed". Rewrite it (delete and recreate) when the state changes. `CronList` on resume: a job from a dead session is gone, so recreate it.

## The worktree-boundary hook

Some setups install a `PreToolUse` hook that blocks `cd`, edits, and writes outside the session's own worktree. Subagents inherit the parent's anchor. What works:

- Read: `git -C <path> …`, `git show origin/<branch>:<path>`, absolute-path reads.
- Change another worktree or repo: launch a session there.
- Never let a subagent call `EnterWorktree`: it re-anchors the whole parent session.
