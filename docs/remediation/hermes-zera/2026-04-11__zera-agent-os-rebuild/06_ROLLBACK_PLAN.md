# 06 Rollback Plan

## Immediate Stop

```bash
zera-evolutionctl stop
touch .agents/evolution/KILL_SWITCH
ps -Ao pid,ppid,pgid,stat,etime,command | rg 'Zera Evolution Daemon|self_evolution_loop.py|vault/loops|zera-evolve|zera-self-evolution' || true
```

If a process ignores `SIGTERM`, use process-group `SIGKILL` only after recording PID and command.

## Restore Hermes Profile

Find latest backup:

```bash
ls -td ~/.hermes/profiles/zera/backups/zera-agent-os-rebuild-* | head -1
```

Restore selected files:

```bash
BACKUP="$(ls -td ~/.hermes/profiles/zera/backups/zera-agent-os-rebuild-* | head -1)"
cp "$BACKUP/config.yaml" ~/.hermes/profiles/zera/config.yaml
cp -R "$BACKUP/cron" ~/.hermes/profiles/zera/
```

Only restore `.env` from a trusted backup if secrets were changed intentionally.

## Disable Cron

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path.home() / ".hermes/profiles/zera/cron/jobs.json"
data = json.loads(p.read_text())
for job in data.get("jobs", []):
    if "evolution" in str(job.get("name", "")).lower():
        job["enabled"] = False
        job["state"] = "paused"
        job["paused_reason"] = "rollback safety stop"
p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
PY
```

## Restore Repo Files

Use normal git review, not destructive reset:

```bash
git status --short
git diff -- scripts/zera/zera-evolutionctl.py scripts/internal/self_evolution_loop.py repos/packages/agent-os/src/agent_os/yaml_compat.py
```

Revert only the files that belong to this rebuild if rollback is approved.

## Remove Local Command Link

```bash
rm -f ~/.local/bin/zera-evolutionctl
```

## Recovery Criteria

- `zera-evolutionctl status` is not available or reports no running PID.
- No self-evolution process remains.
- Cron evolution jobs are disabled.
- Hermes profile loads without gateway auto-failure loops.
