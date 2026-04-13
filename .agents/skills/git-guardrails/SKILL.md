---
name: git-guardrails
description: Set up Claude Code hooks to block dangerous git commands before they execute. Use when setting up a new project, hardening CI safety, or user mentions "git guardrails", "protect from force push", "block dangerous git".
source: https://github.com/mattpocock/skills/tree/main/git-guardrails-claude-code
---

# Git Guardrails for Claude Code

Installs pre-execution hooks that block dangerous git commands before they run.

## Blocked Commands

| Command | Risk |
|---------|------|
| `git push --force` / `git push -f` | Overwrites remote history |
| `git reset --hard` | Destroys uncommitted work |
| `git clean -f` / `git clean -fd` | Deletes untracked files permanently |
| `git checkout -- .` | Discards all working tree changes |
| `git rebase -i` on shared branches | Rewrites shared history |

## Setup

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "node .claude/hooks/git-guardrails.js"
          }
        ]
      }
    ]
  }
}
```

Create `.claude/hooks/git-guardrails.js`:

```js
const input = JSON.parse(require('fs').readFileSync('/dev/stdin', 'utf8'));
const cmd = input?.tool_input?.command || '';

const BLOCKED = [
  /git\s+push\s+.*(-f|--force)/,
  /git\s+reset\s+--hard/,
  /git\s+clean\s+-[fd]/,
  /git\s+checkout\s+--\s+\./,
];

const match = BLOCKED.find(r => r.test(cmd));
if (match) {
  console.error(JSON.stringify({
    decision: 'block',
    reason: `Dangerous git command blocked by guardrails: ${cmd}`
  }));
  process.exit(0);
}
process.exit(0);
```

## Usage

- Applies automatically to all Claude Code sessions in the project
- To override for a specific command: add `# GUARDRAIL_OVERRIDE` comment in the bash command
- Review blocked commands in `.claude/logs/` if enabled

## Key Rules
- Install at project root, not globally
- Pairs with `finishing-a-development-branch` for safe branch lifecycle
- C5 tasks (security/payments) should always have this active
