# How this project is set up for AI agents (study notes)

Think of the AI as a new kitchen helper. A good restaurant does not just say "go cook". It gives the helper a handbook, safety rules, specialist coworkers, and recipe cards. Each file below is one of those.

| File | Kitchen version | What it does |
|---|---|---|
| `CLAUDE.md` | Handbook on the wall | Read at the start of every session: how to run things, the rules, the known problems. Keep it short (under about 200 lines). It is guidance, not a lock. |
| `CLAUDE.local.md` | Your personal sticky note | Only on your machine, never committed (it is in `.gitignore`). |
| `.claude/rules/*.md` | Rules for one station | Load only when the agent touches matching files (`paths:` at the top). |
| `.claude/settings.json` | The key cabinet and the alarm | `permissions` decides what is allowed, asked about, or denied. `hooks` wires up the scripts below. |
| `.claude/hooks/guard.py` | A guard that never sleeps | Runs BEFORE every file or shell action. Exit code 2 blocks it. |
| `.claude/hooks/syntax_check.py` | A spell-checker | Runs AFTER every edit. Tells the agent at once if a .py or .json file is broken. |
| `.claude/agents/*.md` | Specialist coworkers | Each works in its own room and reports back a summary: code-reviewer, test-writer, security-reviewer. |
| `.claude/skills/*/SKILL.md` | Recipe cards | Loaded only when the job matches the description: django-test-writing, qa-bug-report. |

## Why two layers (permissions AND hooks)?
- Permissions are the official lock. But a deny rule on `Read(./.env)` only stops Claude's built-in file tools, not a shell command like `cat .env`.
- The hook looks at the shell command text too (Bash and PowerShell), so it covers that gap. Neither layer is perfect alone. Real safety is layers.

## The one hook gotcha
In Claude Code, exit code 1 does NOT block anything. Only exit code 2 blocks. A script that crashes exits with 1, so `guard.py` catches crashes and turns them into exit 2 ("fail closed"). A mistyped script path in `settings.json` also fails quietly, so always test a hook after you set it up.

## How to check it works (inside Claude Code, in this folder)
1. Run `claude doctor` in a terminal: it reports settings problems.
2. In a session, type `/memory` (shows which CLAUDE.md and rules loaded) and `/hooks` (read-only list of your hooks).
3. Ask: "Show me the contents of .env". Expected: blocked, with the guard's message.
4. Ask: "Run rm -rf build". Expected: blocked.
5. Ask: "Use the security-reviewer to review orders/views.py". Expected: a findings table. If it is not found, restart Claude Code.

## Growing it
Add one line to `CLAUDE.md` each time the agent repeats a mistake. Add a hook only for things that must ALWAYS happen. Add a subagent when one job keeps cluttering your main chat. Add a skill when you keep pasting the same instructions.

## Requirements
Claude Code needs a paid Claude plan or a Console account. The hook scripts need `python` on your PATH (you already have it for Django). Install Git for Windows too, so the Bash tool and permission rules work as written.
