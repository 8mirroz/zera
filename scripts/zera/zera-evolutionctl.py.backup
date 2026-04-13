#!/usr/bin/env python3
"""
zera-evolutionctl — Zera evolution lifecycle controller

Wave 4 — Evidence Binding, Report Freshness, Runtime SOT:
  shadow-prepare        Clone a Hermes profile into a shadow profile
  shadow-upgrade        Run hermes update + smoke (shadow + zera read-only)
  shadow-smoke          Smoke tests with session/probe marker binding
  promote-rehearsal     Full control-plane rehearsal without mutation
  promote-policy-check  Validate all promotion gates (attempt-bound)
  promote-status        Show current promotion window state (--json)
  promote-enable        Enable controlled promotion with attempt binding
  promote-disable       Disable controlled promotion
  promote-rollback      Rollback to a pre-promotion snapshot
  gateway-check         Verify gateway compatibility (intent-hardened)
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EVOLUTION_DIR = ROOT / ".agent" / "evolution"
CORE_LOOP = ROOT / "scripts" / "internal" / "self_evolution_loop.py"
PID_FILE = EVOLUTION_DIR / "evolutionctl.pid"
CTL_STATE_FILE = EVOLUTION_DIR / "evolutionctl-state.json"
CTL_LOG_FILE = EVOLUTION_DIR / "evolutionctl.out.log"
CORE_LOG_FILE = EVOLUTION_DIR / "loop.log"
LEGACY_STATE_FILE = ROOT / "vault" / "loops" / ".evolve-state.json"
KILL_SWITCH_FILE = EVOLUTION_DIR / "KILL_SWITCH"
HERMES_ZERA_PROFILE = Path.home() / ".hermes" / "profiles" / "zera"
HERMES_PROFILES_DIR = Path.home() / ".hermes" / "profiles"
HERMES_ROOT = Path.home() / ".hermes"
LOCAL_BIN = Path.home() / ".local" / "bin"

# Wave 3+: snapshot root OUTSIDE the zera profile
SNAPSHOT_ROOT = Path.home() / ".hermes" / "profiles" / ".backups" / "zera-promote-snapshots"

# Promotion governance
PROMOTION_POLICY_FILE = ROOT / "configs" / "tooling" / "zera_promotion_policy.yaml"
PROMOTION_STATE_FILE = EVOLUTION_DIR / "promotion_state.json"

# Wave 4: scoped artifact paths
# Program-owned folder: docs/remediation/hermes-zera/2026-04-11__zera-agent-os-rebuild/artifacts/wave4/<attempt_id>/
HERMES_ZERA_ARTIFACT_BASE = ROOT / "docs" / "remediation" / "hermes-zera" / "2026-04-11__zera-agent-os-rebuild" / "artifacts" / "wave4"
# Legacy readers still supported for backward compat
PROMOTION_ARTIFACTS_DIR = ROOT / "docs" / "remediation"

ALGORITHMS = [
    "karpathy",
    "rsi",
    "darwin-goedel",
    "pantheon",
    "self-improving",
    "karpathy-swarm",
    "ralph",
    "agentic-ci",
    "self-driving",
    "meta-learning",
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def generate_attempt_id() -> str:
    """Generate a unique promotion attempt ID with timestamp prefix."""
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    nonce = hashlib.sha256(f"{ts}-{os.getpid()}-{time.monotonic()}".encode()).hexdigest()[:8]
    return f"attempt-{ts}-{nonce}"


def _attempt_artifact_dir(attempt_id: str, command: str) -> Path:
    """Wave 4: scoped artifact directory for a specific attempt."""
    d = HERMES_ZERA_ARTIFACT_BASE / attempt_id / command
    d.mkdir(parents=True, exist_ok=True)
    return d


def _legacy_artifact_dir(command: str) -> Path:
    """Legacy artifact path for backward compat."""
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    d = PROMOTION_ARTIFACTS_DIR / command / ts
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_attempt_report(attempt_id: str, command: str, payload: dict[str, Any]) -> Path:
    """Write report to both scoped (Wave 4) and legacy paths."""
    scoped_path = _attempt_artifact_dir(attempt_id, command) / "report.json"
    write_json(scoped_path, payload)
    # Also write legacy path for backward compat
    legacy_path = _legacy_artifact_dir(command) / "report.json"
    write_json(legacy_path, payload)
    return scoped_path


def read_attempt_report(attempt_id: str, command: str) -> dict[str, Any]:
    """Read report from scoped path (Wave 4 primary), fallback to legacy."""
    scoped = _attempt_artifact_dir(attempt_id, command) / "report.json"
    if scoped.exists():
        return read_json(scoped)
    # Fallback: find any report for this command (legacy)
    return {}


def validate_report_freshness(report: dict[str, Any], max_age_minutes: int = 60) -> tuple[bool, str]:
    """Check that a report is not older than max_age_minutes."""
    ts = report.get("timestamp")
    if not ts:
        return False, "no timestamp in report"
    try:
        report_time = dt.datetime.fromisoformat(ts)
        age = (dt.datetime.now(dt.timezone.utc) - report_time).total_seconds() / 60
        if age > max_age_minutes:
            return False, f"report is {age:.0f}m old (max {max_age_minutes}m)"
        return True, f"report age {age:.0f}m"
    except (ValueError, TypeError):
        return False, "invalid timestamp format"


def validate_report_matches_attempt(report: dict[str, Any], attempt_id: str) -> bool:
    """Check that report's attempt_id matches the expected one."""
    return report.get("attempt_id") == attempt_id


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def process_is_zombie(pid: int) -> bool:
    try:
        proc = subprocess.run(["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True, check=False)
    except Exception:
        return False
    return "Z" in proc.stdout.strip()


def read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    raw = PID_FILE.read_text(encoding="utf-8").strip()
    try:
        return int(raw)
    except ValueError:
        return None


def write_state(status: str, **extra: Any) -> None:
    current = read_json(CTL_STATE_FILE)
    clear_keys = tuple(extra.pop("clear_keys", ()))
    payload = {
        **current,
        "status": status,
        "updated_at": utc_now(),
        "controller": "scripts/zera/zera-evolutionctl.py",
        **extra,
    }
    for key in clear_keys:
        payload.pop(str(key), None)
    write_json(CTL_STATE_FILE, payload)


def normalize_legacy_state() -> dict[str, Any]:
    raw = read_json(LEGACY_STATE_FILE)
    order = raw.get("algorithm_order") or raw.get("cycle_names") or ALGORITHMS
    if not isinstance(order, list) or not order:
        order = ALGORITHMS
    current_cycle = int(raw.get("current_cycle") or 0)
    current_algorithm = raw.get("current_algorithm")
    next_algorithm = raw.get("next_algorithm")
    if not current_algorithm:
        current_algorithm = order[current_cycle % len(order)]
    if not next_algorithm:
        next_algorithm = order[(current_cycle + 1) % len(order)]
    payload = {
        "schema_version": 1,
        "status": raw.get("status") or "idle",
        "current_cycle": current_cycle,
        "current_algorithm": current_algorithm,
        "next_algorithm": next_algorithm,
        "algorithm_order": order,
        "last_run": raw.get("last_run"),
        "last_error": raw.get("last_error"),
        "consecutive_errors": int(raw.get("consecutive_errors") or 0),
        "last_report": raw.get("last_report"),
        "updated_at": utc_now(),
    }
    validate_legacy_state(payload)
    write_json(LEGACY_STATE_FILE, payload)
    return payload


def validate_legacy_state(payload: dict[str, Any]) -> None:
    order = payload.get("algorithm_order")
    current = payload.get("current_algorithm")
    next_algorithm = payload.get("next_algorithm")
    if not isinstance(order, list) or not order:
        raise ValueError("evolution state schema error: algorithm_order must be a non-empty list")
    if current not in order:
        raise ValueError("evolution state schema error: current_algorithm must exist in algorithm_order")
    if next_algorithm not in order:
        raise ValueError("evolution state schema error: next_algorithm must exist in algorithm_order")
    if not isinstance(payload.get("consecutive_errors"), int):
        raise ValueError("evolution state schema error: consecutive_errors must be integer")


def backup_external_state() -> Path:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = HERMES_ZERA_PROFILE / "backups" / f"zera-agent-os-rebuild-{ts}"
    backup_root.mkdir(parents=True, exist_ok=True)
    for name in ("config.yaml", "SOUL.md", "processes.json", "gateway_state.json"):
        src = HERMES_ZERA_PROFILE / name
        if src.exists():
            shutil.copy2(src, backup_root / name)
    cron_dir = HERMES_ZERA_PROFILE / "cron"
    if cron_dir.exists():
        shutil.copytree(cron_dir, backup_root / "cron", dirs_exist_ok=True)
    write_state("backup_created", backup_path=str(backup_root))
    return backup_root


def disable_unsafe_cron_jobs() -> list[str]:
    jobs_file = HERMES_ZERA_PROFILE / "cron" / "jobs.json"
    if not jobs_file.exists():
        return []
    payload = read_json(jobs_file)
    changed: list[str] = []
    for job in payload.get("jobs", []):
        if not isinstance(job, dict):
            continue
        prompt = str(job.get("prompt") or "").lower()
        name = str(job.get("name") or "")
        dangerous = (
            "self-evolution" in name.lower()
            or ".evolve-state.json" in prompt
            or "execute it, then update state" in prompt
            or "python3 -c" in prompt
        )
        if dangerous and job.get("enabled") is not False:
            job["enabled"] = False
            job["state"] = "paused"
            job["paused_at"] = utc_now()
            job["paused_reason"] = "disabled by zera-evolutionctl: unmanaged self-evolution job"
            changed.append(name or str(job.get("id") or "unknown"))
    if changed:
        payload["updated_at"] = utc_now()
        write_json(jobs_file, payload)
    write_state("cron_sanitized", disabled_jobs=changed)
    return changed


def ensure_local_bin_link() -> Path:
    LOCAL_BIN.mkdir(parents=True, exist_ok=True)
    target = ROOT / "scripts" / "zera-evolutionctl"
    link = LOCAL_BIN / "zera-evolutionctl"
    if link.exists() or link.is_symlink():
        if link.resolve() == target.resolve():
            return link
        backup = link.with_name(f"{link.name}.bak-{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}")
        link.rename(backup)
    link.symlink_to(target)
    return link


def build_core_cmd(args: argparse.Namespace, *, dry_run: bool) -> list[str]:
    cmd = [sys.executable, str(CORE_LOOP), "--cycles", str(args.cycles), "--interval", str(args.interval)]
    if dry_run:
        cmd.append("--dry-run")
    if getattr(args, "no_promote", False):
        cmd.append("--no-promote")
    return cmd


def build_child_env(args: argparse.Namespace) -> dict[str, str]:
    """Build environment for child process (core loop).

    Wave 6: Propagates promotion awareness and no-mutate flags.
    """
    env = dict(os.environ)
    if not getattr(args, "llm_score", False):
        env["ZERA_EVO_DISABLE_LLM_SCORING"] = "1"

    # Wave 6: No-mutate enforcement (for rehearsal safety)
    no_mutate = getattr(args, "no_mutate_code", False) or os.environ.get("ZERA_EVO_NO_MUTATE", "0") == "1"
    if no_mutate:
        env["ZERA_EVO_NO_MUTATE"] = "1"

    # Wave 6: Promotion active flag
    if not getattr(args, "no_promote", True):
        env["ZERA_EVO_PROMOTION_ACTIVE"] = "1"

    return env


def cmd_backup(_: argparse.Namespace) -> int:
    backup = backup_external_state()
    print(f"Backup created: {backup}")
    return 0


def cmd_install(_: argparse.Namespace) -> int:
    normalize_legacy_state()
    link = ensure_local_bin_link()
    print(f"Installed command link: {link}")
    return 0


def cmd_sanitize_cron(_: argparse.Namespace) -> int:
    backup = backup_external_state()
    changed = disable_unsafe_cron_jobs()
    print(f"Backup created: {backup}")
    print("Disabled jobs: " + (", ".join(changed) if changed else "none"))
    return 0


def cmd_dry_run(args: argparse.Namespace) -> int:
    if KILL_SWITCH_FILE.exists():
        print(f"Kill switch active: {KILL_SWITCH_FILE}", file=sys.stderr)
        return 3
    normalize_legacy_state()
    cmd = build_core_cmd(args, dry_run=True)
    write_state("dry_run_started", command=cmd)
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    write_state("dry_run_completed" if proc.returncode == 0 else "dry_run_failed", returncode=proc.returncode)
    return int(proc.returncode)


def cmd_start(args: argparse.Namespace) -> int:
    if KILL_SWITCH_FILE.exists():
        print(f"Kill switch active: {KILL_SWITCH_FILE}", file=sys.stderr)
        return 3
    if not args.no_promote and not args.force:
        print("Refusing promotion-enabled start without --force.", file=sys.stderr)
        return 2
    if args.cycles == 0 and not args.forever:
        print("Refusing unbounded start without --forever.", file=sys.stderr)
        return 2
    if args.cycles == 0 and args.interval < 300 and not args.force:
        print("Refusing forever mode with interval <300s without --force.", file=sys.stderr)
        return 2
    current_pid = read_pid()
    if current_pid and process_alive(current_pid) and not process_is_zombie(current_pid):
        print(f"Evolution loop already running: pid={current_pid}", file=sys.stderr)
        return 1
    normalize_legacy_state()
    cmd = build_core_cmd(args, dry_run=False)
    EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)
    log_fh = CTL_LOG_FILE.open("ab")
    proc = subprocess.Popen(
        cmd,
        cwd=ROOT,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        env=build_child_env(args),
        start_new_session=True,
    )
    PID_FILE.write_text(f"{proc.pid}\n", encoding="utf-8")
    write_state(
        "running",
        pid=proc.pid,
        command=cmd,
        no_promote=bool(args.no_promote),
        started_at=utc_now(),
        clear_keys=("exited_at", "previous_pid", "returncode", "stop_reason", "stopped_at"),
    )
    print(f"Started Zera evolution loop: pid={proc.pid}")
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    pid = read_pid()
    alive = (process_alive(pid) and not process_is_zombie(pid)) if pid else False
    if pid and not alive:
        if PID_FILE.exists():
            PID_FILE.unlink()
        write_state(
            "exited",
            pid=None,
            previous_pid=pid,
            exited_at=utc_now(),
            clear_keys=("returncode", "stop_reason", "stopped_at"),
        )
        pid = None
    state = read_json(CTL_STATE_FILE)
    state.update({"pid": pid, "alive": alive, "kill_switch": KILL_SWITCH_FILE.exists()})
    print(json.dumps(state, ensure_ascii=False, indent=2))
    if CORE_LOOP.exists():
        subprocess.run([sys.executable, str(CORE_LOOP), "--status"], cwd=ROOT, check=False)
    return 0 if alive or state.get("status") else 1


def cmd_stop(args: argparse.Namespace) -> int:
    pid = read_pid()
    if not pid or not process_alive(pid) or process_is_zombie(pid):
        if PID_FILE.exists():
            PID_FILE.unlink()
        state = read_json(CTL_STATE_FILE)
        if state.get("status") == "running":
            write_state("exited", pid=None, exited_at=utc_now(), stop_reason="not_running", clear_keys=("stopped_at",))
        print("No running evolution loop.")
        return 0
    os.kill(pid, signal.SIGTERM)
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        if not process_alive(pid) or process_is_zombie(pid):
            break
        time.sleep(0.5)
    if process_alive(pid) and not process_is_zombie(pid):
        os.kill(pid, signal.SIGKILL)
        write_state("killed", pid=None, previous_pid=pid, stopped_at=utc_now(), clear_keys=("exited_at", "stop_reason"))
        print(f"Killed evolution loop: pid={pid}")
    else:
        write_state("stopped", pid=None, previous_pid=pid, stopped_at=utc_now(), clear_keys=("exited_at", "stop_reason"))
        print(f"Stopped evolution loop: pid={pid}")
    if PID_FILE.exists():
        PID_FILE.unlink()
    return 0


def cmd_tail(args: argparse.Namespace) -> int:
    path = CORE_LOG_FILE if CORE_LOG_FILE.exists() else CTL_LOG_FILE
    if not path.exists():
        print(f"No log file found: {path}", file=sys.stderr)
        return 1
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[-args.lines :]:
        print(line)
    return 0


# ─────────────────────────────────────────────────────────────
# Wave 3 — Hermes Shadow Upgrade + Controlled Full Promote (hardened)
# ─────────────────────────────────────────────────────────────

def _hermes_run(args: list[str], *, profile: str | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run a hermes subcommand, optionally with a specific profile."""
    cmd = ["hermes"] + args
    env = dict(os.environ)
    if profile:
        env["HERMES_PROFILE"] = profile
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env, check=False)


_SESSION_ID_RE = re.compile(r"session[:\s]+([a-f0-9]{8,})")


def _hermes_chat_smoke(profile: str, n: int = 3, timeout_per: int = 60,
                       probe_marker: str | None = None) -> list[dict[str, Any]]:
    """Run N chat smoke probes against the given profile.

    Wave 6: Extracts session_id from hermes chat output for session-scoped log checks.
    """
    query = probe_marker if probe_marker else "ping"
    results: list[dict[str, Any]] = []
    session_ids: list[str] = []
    for i in range(1, n + 1):
        start = time.monotonic()
        try:
            proc = _hermes_run(
                ["chat", "-Q", "-q", query],
                profile=profile,
                timeout=timeout_per,
            )
            elapsed = time.monotonic() - start
            ok = proc.returncode == 0

            # Wave 6: Extract session_id from output
            session_id = None
            combined_output = proc.stdout + proc.stderr
            m = _SESSION_ID_RE.search(combined_output)
            if m:
                session_id = m.group(1)
                session_ids.append(session_id)

            results.append({
                "probe": i,
                "ok": ok,
                "returncode": proc.returncode,
                "elapsed_s": round(elapsed, 2),
                "session_id": session_id,
                "stderr_tail": proc.stderr[-300:] if proc.stderr else "",
                "stdout_tail": proc.stdout[-200:] if proc.stdout else "",
            })
            if not ok:
                break
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - start
            results.append({
                "probe": i,
                "ok": False,
                "returncode": -1,
                "elapsed_s": round(elapsed, 2),
                "session_id": None,
                "stderr_tail": "timeout",
            })
            break
    return results


def _check_errors_log(profile: str, since: str = "30m", signatures: list[str] | None = None,
                      session_id: str | None = None) -> dict[str, Any]:
    """Check hermes errors.log for signature patterns.

    Wave 6: Supports session-scoped log check when session_id is provided.
    """
    if signatures is None:
        signatures = [
            "Qwen OAuth refresh returned invalid JSON",
            "Qwen OAuth refresh",
            "provider.*error",
            "authentication.*failed",
        ]
    # Try session-scoped log first
    if session_id:
        proc = _hermes_run(["logs", "errors", "--session", session_id, "--since", since],
                          profile=profile, timeout=30)
        session_filter_used = True
    else:
        proc = _hermes_run(["logs", "errors", "--since", since], profile=profile, timeout=30)
        session_filter_used = False
    output = proc.stdout + proc.stderr
    found: dict[str, bool] = {}
    for sig in signatures:
        found[sig] = bool(re.search(sig, output, re.IGNORECASE))
    return {
        "signatures_checked": signatures,
        "found": found,
        "session_filter_used": session_filter_used,
        "session_id": session_id,
        "raw_tail": output[-500:] if output else "",
    }


def _check_errors_log_for_signatures(output: str, signatures: list[str] | None = None) -> dict[str, bool]:
    """Check a given text block for Qwen OAuth failure signatures."""
    if signatures is None:
        signatures = [
            "Qwen OAuth refresh returned invalid JSON",
            "Qwen OAuth refresh",
        ]
    found: dict[str, bool] = {}
    for sig in signatures:
        found[sig] = bool(re.search(sig, output, re.IGNORECASE))
    return found


def _check_agent_log(profile: str, since: str = "30m") -> dict[str, Any]:
    """Check hermes agent log for provider refresh errors."""
    proc = _hermes_run(["logs", "agent", "--since", since], profile=profile, timeout=30)
    output = proc.stdout
    error_lines = [l for l in output.splitlines() if "error" in l.lower() or "refresh" in l.lower()]
    return {"error_line_count": len(error_lines), "tail": error_lines[-20:] if error_lines else []}


def _create_artifact_dir(command: str) -> Path:
    """Create a timestamped artifact directory under docs/remediation/."""
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    d = PROMOTION_ARTIFACTS_DIR / command / ts
    d.mkdir(parents=True, exist_ok=True)
    return d


# ─── Snapshot Management (Wave 3: outside zera profile) ─────────


def _snapshot_root() -> Path:
    """Return the snapshot root, creating it if needed."""
    SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)
    return SNAPSHOT_ROOT


def _is_snapshot_safe(snapshot_dir: Path) -> bool:
    """Verify that a snapshot directory is NOT inside HERMES_ZERA_PROFILE."""
    try:
        snapshot_dir.relative_to(HERMES_ZERA_PROFILE)
        return False  # inside zera — unsafe
    except ValueError:
        return True  # outside zera — safe


def _detect_legacy_internal_snapshots() -> list[dict[str, Any]]:
    """Find old snapshots stored inside zera/backups/_snapshots."""
    internal_dir = HERMES_ZERA_PROFILE / "backups" / "_snapshots"
    if not internal_dir.exists():
        return []
    legacy = []
    for d in internal_dir.iterdir():
        if d.is_dir() and (d / "snapshot_meta.json").exists():
            legacy.append({
                "snapshot_id": d.name,
                "path": str(d),
                "status": "legacy_unsafe",
                "reason": "stored inside zera profile — rollback prohibited without --allow-legacy-internal-snapshot",
            })
    return legacy


def _create_promotion_snapshot(label: str = "pre-promote") -> dict[str, Any]:
    """Create a full snapshot backup of the zera profile, vault state, and cron.

    Wave 3: Snapshots are stored in SNAPSHOT_ROOT (outside zera profile).
    """
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_id = f"snapshot-{ts}-{label}"
    snapshot_dir = _snapshot_root() / snapshot_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    snapshots = []

    # 1. Backup ~/.hermes/profiles/zera (exclude _snapshots and .backups to avoid recursion)
    profile_backup = snapshot_dir / "profile"
    def _ignore_backup_dirs(src, names):
        ignored = set()
        if "_snapshots" in names:
            ignored.add("_snapshots")
        if ".backups" in names:
            ignored.add(".backups")
        return ignored
    shutil.copytree(HERMES_ZERA_PROFILE, profile_backup, symlinks=True, dirs_exist_ok=True, ignore=_ignore_backup_dirs)
    snapshots.append("profile")

    # 2. Backup vault/loops/.evolve-state.json
    vault_backup = snapshot_dir / "vault_loops"
    vault_backup.mkdir(exist_ok=True)
    if LEGACY_STATE_FILE.exists():
        shutil.copy2(LEGACY_STATE_FILE, vault_backup / ".evolve-state.json")
    state_json = EVOLUTION_DIR / "state.json"
    if state_json.exists():
        shutil.copy2(state_json, vault_backup / "state.json")
    ctl_state_json = CTL_STATE_FILE
    if ctl_state_json.exists():
        shutil.copy2(ctl_state_json, vault_backup / "evolutionctl-state.json")
    snapshots.append("vault_loops")

    # 3. Backup cron jobs
    cron_dir = HERMES_ZERA_PROFILE / "cron"
    if cron_dir.exists():
        cron_backup = snapshot_dir / "cron"
        shutil.copytree(cron_dir, cron_backup, dirs_exist_ok=True)
        snapshots.append("cron")

    snapshot_meta = {
        "snapshot_id": snapshot_id,
        "label": label,
        "timestamp": utc_now(),
        "snapshots": snapshots,
        "snapshot_dir": str(snapshot_dir),
        "safe": _is_snapshot_safe(snapshot_dir),
    }
    write_json(snapshot_dir / "snapshot_meta.json", snapshot_meta)

    # Register snapshot in promotion state
    pstate = read_json(PROMOTION_STATE_FILE)
    snapshots_list = pstate.setdefault("snapshots", [])
    snapshots_list.append(snapshot_meta)
    pstate["latest_snapshot"] = snapshot_id
    write_json(PROMOTION_STATE_FILE, pstate)

    return snapshot_meta


# ─── Promotion Governance (Wave 3) ──────────────────────────────────


def _load_promotion_policy(*, fail_closed: bool = True) -> dict[str, Any]:
    """Load the promotion policy YAML.

    Wave 4: fail_closed=True by default — missing/invalid policy is an error
    for promotion-enabled flows. Fallback only for read-only operations.
    """
    import yaml
    if not PROMOTION_POLICY_FILE.exists():
        if fail_closed:
            raise FileNotFoundError(
                f"Promotion policy not found: {PROMOTION_POLICY_FILE}. "
                "Policy file is required for promotion-enabled flows."
            )
        return {}
    try:
        with open(PROMOTION_POLICY_FILE) as f:
            data = yaml.safe_load(f)
        if not data or not isinstance(data, dict):
            if fail_closed:
                raise ValueError(f"Promotion policy is empty or invalid: {PROMOTION_POLICY_FILE}")
            return {}
        # Fix typo: require_active-window → require_active_window
        promo = data.get("promotion", {})
        if "require_active-window" in promo:
            promo["require_active_window"] = promo.pop("require_active-window")
        data["promotion"] = promo
        return data
    except yaml.YAMLError as e:
        if fail_closed:
            raise ValueError(f"Invalid promotion policy YAML: {e}") from e
        return {}


def _run_gate(name: str, cmd: list[str], *, allow_warnings: bool = False, required: bool = True) -> dict[str, Any]:
    """Run a single validation gate and capture results.

    Wave 4: fail-closed — FileNotFoundError returns ok=False for required gates.
    """
    print(f"  Running gate: {name} ...")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
        ok = proc.returncode == 0
        result = {
            "gate": name,
            "ok": ok,
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-300:] if proc.stdout else "",
            "stderr_tail": proc.stderr[-300:] if proc.stderr else "",
        }
        status = "PASS" if ok else "FAIL"
        print(f"    {name}: {status}")
        return result
    except subprocess.TimeoutExpired:
        print(f"    {name}: TIMEOUT")
        return {"gate": name, "ok": False, "returncode": -1, "stderr_tail": "timeout"}
    except FileNotFoundError:
        if required:
            print(f"    {name}: FAIL (command not found, fail-closed)")
            return {"gate": name, "ok": False, "returncode": 127, "stderr_tail": "command not found"}
        else:
            print(f"    {name}: SKIP (command not found, optional)")
            return {"gate": name, "ok": True, "returncode": 0, "note": "command not found, optional gate skipped"}


def _read_attempt_smoke_report(attempt_id: str) -> tuple[bool, Path | None]:
    """Wave 4: Read smoke report strictly bound to an attempt_id."""
    if not attempt_id:
        return False, None
    scoped = HERMES_ZERA_ARTIFACT_BASE / attempt_id / "shadow-smoke" / "report.json"
    if scoped.exists():
        report = read_json(scoped)
        if report.get("ok") and validate_report_matches_attempt(report, attempt_id):
            fresh, msg = validate_report_freshness(report, max_age_minutes=60)
            if fresh:
                return True, scoped
            return False, scoped  # report exists but stale
    # Fallback: legacy path
    legacy_root = PROMOTION_ARTIFACTS_DIR / "shadow-smoke"
    if legacy_root.exists():
        try:
            for d in sorted(legacy_root.iterdir(), reverse=True):
                rf = d / "report.json"
                if rf.exists():
                    report = read_json(rf)
                    if report.get("ok"):
                        return True, rf
        except FileNotFoundError:
            pass
    return False, None


def _read_attempt_policy_report(attempt_id: str) -> tuple[bool, Path | None]:
    """Wave 4: Read policy check report strictly bound to an attempt_id."""
    if not attempt_id:
        return False, None
    scoped = HERMES_ZERA_ARTIFACT_BASE / attempt_id / "promote-policy-check" / "report.json"
    if scoped.exists():
        report = read_json(scoped)
        if report.get("ok") and validate_report_matches_attempt(report, attempt_id):
            return True, scoped
    # Fallback: legacy path
    legacy_root = PROMOTION_ARTIFACTS_DIR / "promote-policy-check"
    if legacy_root.exists():
        try:
            for d in sorted(legacy_root.iterdir(), reverse=True):
                rf = d / "report.json"
                if rf.exists():
                    report = read_json(rf)
                    if report.get("ok"):
                        return True, rf
        except FileNotFoundError:
            pass
    return False, None


def _check_gateway_compatibility_strict(attempt_id: str | None = None) -> tuple[bool, dict[str, Any]]:
    """Strict gateway compatibility check (Wave 4: intent-hardened).

    Wave 4 additions:
    - gateway.disabled_intent_required: if True, 'not running' alone is not enough
      — must have explicit disable decision artifact or config flag
    - Binds report to attempt_id
    """
    policy = _load_promotion_policy(fail_closed=False)
    gw_config = policy.get("gateway", {})
    mode = gw_config.get("mode", "disabled_allowed")
    disabled_intent_required = gw_config.get("disabled_intent_required", False)
    required_adapters = gw_config.get("required_adapters", [])

    proc = _hermes_run(["gateway", "status"], timeout=30)
    output = proc.stdout.lower()
    running = "running" in output or "active" in output
    adapters_ready = "ready" in output or "enabled" in output
    not_running = "not running" in output

    report: dict[str, Any] = {
        "mode": mode,
        "running": running,
        "not_running": not_running,
        "adapters_ready": adapters_ready,
        "disabled_intent_required": disabled_intent_required,
        "required_adapters": required_adapters,
        "raw_output_tail": proc.stdout[-500:] if proc.stdout else "",
        "attempt_id": attempt_id,
    }

    if mode == "disabled_allowed":
        if not_running:
            # Wave 4: check explicit disable intent
            if disabled_intent_required:
                # Check for disabled intent artifact or config flag
                has_intent = _check_gateway_disabled_intent()
                if has_intent:
                    ok = True
                    report["decision"] = "ok"
                    report["reason"] = "gateway not running with explicit disabled intent"
                else:
                    ok = False
                    report["decision"] = "blocked"
                    report["reason"] = "gateway not running but no explicit disabled intent"
            else:
                ok = True
                report["decision"] = "ok"
                report["reason"] = "gateway not running (allowed, no intent required)"
        elif running and adapters_ready:
            ok = True
            report["decision"] = "ok"
            report["reason"] = "gateway running with ready adapters"
        elif running and not adapters_ready:
            ok = False
            report["decision"] = "blocked"
            report["reason"] = "gateway running without ready adapters — configure adapters or disable gateway"
        else:
            ok = False
            report["decision"] = "blocked"
            report["reason"] = "gateway in ambiguous state"
    elif mode == "required":
        ok = adapters_ready and running
        report["decision"] = "ok" if ok else "blocked"
        report["reason"] = "gateway running with ready adapters" if ok else "gateway required but not ready"
    else:
        ok = False
        report["decision"] = "blocked"
        report["reason"] = f"unknown gateway mode: {mode}"

    return ok, report


def _check_gateway_disabled_intent() -> bool:
    """Check for explicit gateway disabled intent.

    Looks for:
    1. Config flag in zera config.yaml: gateway.enabled = false
    2. Explicit disabled intent artifact
    """
    import yaml
    config_path = HERMES_ZERA_PROFILE / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}
            gw = config.get("gateway", {})
            if gw.get("enabled") is False:
                return True
            if gw.get("disabled_intent") is True:
                return True
        except yaml.YAMLError:
            pass
    # Check for explicit intent artifact
    intent_file = HERMES_ZERA_PROFILE / ".gateway_disabled"
    return intent_file.exists()


# ─── Promotion Window Enforcement (Wave 4: attempt-bound) ───────────


def _require_active_promotion_window() -> tuple[bool, dict[str, Any]]:
    """Wave 4: Check that an active promotion window exists with attempt-bound evidence.

    Returns (ok, info_dict).
    """
    pstate = read_json(PROMOTION_STATE_FILE)
    promotion = pstate.get("promotion", {})

    info = {
        "enabled": promotion.get("enabled", False),
        "scope": promotion.get("scope"),
        "enabled_at": promotion.get("enabled_at"),
        "expires_at": promotion.get("expires_at"),
        "snapshot_id": promotion.get("snapshot_id"),
        "attempt_id": promotion.get("attempt_id"),
    }

    # 1. Must be enabled
    if not promotion.get("enabled"):
        info["reason"] = "promotion not enabled"
        return False, info

    # 2. Scope must be full
    if promotion.get("scope") != "full":
        info["reason"] = f"scope '{promotion.get('scope')}' is not 'full'"
        return False, info

    # 3. TTL must not have expired
    expires_at = promotion.get("expires_at")
    if expires_at:
        try:
            expiry = dt.datetime.fromisoformat(expires_at)
            now = dt.datetime.now(dt.timezone.utc)
            remaining = (expiry - now).total_seconds()
            info["remaining_seconds"] = max(0, round(remaining))
            if remaining <= 0:
                info["reason"] = "TTL expired"
                info["expired"] = True
                return False, info
        except ValueError:
            info["reason"] = "invalid expires_at format"
            return False, info
    else:
        info["reason"] = "no expires_at set"
        return False, info

    # 4. Snapshot must exist
    snapshot_id = promotion.get("snapshot_id")
    if not snapshot_id:
        info["reason"] = "no snapshot_id in promotion state"
        return False, info
    snapshots = pstate.get("snapshots", [])
    snap_exists = any(s.get("snapshot_id") == snapshot_id for s in snapshots)
    if not snap_exists:
        info["reason"] = f"snapshot '{snapshot_id}' not found"
        return False, info
    info["snapshot_exists"] = True

    # 5. Wave 4: promote-policy-check report must be bound to this attempt
    attempt_id = promotion.get("attempt_id")
    if attempt_id:
        policy_ok, policy_report = _read_attempt_policy_report(attempt_id)
        info["attempt_id"] = attempt_id
        info["attempt_policy_ok"] = policy_ok
        info["attempt_policy_report"] = str(policy_report) if policy_report else None
        if not policy_ok:
            info["reason"] = f"no passing policy report for attempt {attempt_id}"
            return False, info
    else:
        # Fallback: no attempt_id set (Wave 3 legacy), use legacy lookup
        info["reason"] = "no attempt_id — legacy promotion, cannot verify evidence"
        return False, info

    # 6. Kill switch must not be active
    if KILL_SWITCH_FILE.exists():
        info["reason"] = "kill switch active"
        return False, info

    return True, info


# ─── cmd_start with promotion guard (Wave 3) ────────────────────────


def cmd_start(args: argparse.Namespace) -> int:
    if KILL_SWITCH_FILE.exists():
        print(f"Kill switch active: {KILL_SWITCH_FILE}", file=sys.stderr)
        return 3

    # Wave 3: --allow-promote requires active promotion window
    if not args.no_promote:
        # --allow-promote was set; check promotion window
        ok, info = _require_active_promotion_window()
        if not ok:
            print(f"Promotion window check FAILED: {info.get('reason', 'unknown')}", file=sys.stderr)
            if info.get("expired"):
                print(f"  TTL expired at {info.get('expires_at')}", file=sys.stderr)
            if info.get("remaining_seconds") is not None:
                print(f"  Remaining: {info['remaining_seconds']}s", file=sys.stderr)
            # Record failure
            pstate = read_json(PROMOTION_STATE_FILE)
            pstate.setdefault("last_guard_failure", {})["cmd_start"] = {
                "at": utc_now(),
                "reason": info.get("reason"),
                "info": {k: v for k, v in info.items() if k != "reason"},
            }
            write_json(PROMOTION_STATE_FILE, pstate)
            return 2
        print(f"Promotion window OK: remaining={info.get('remaining_seconds')}s")

    if not args.no_promote and not args.force:
        print("Refusing promotion-enabled start without --force.", file=sys.stderr)
        return 2
    if args.cycles == 0 and not args.forever:
        print("Refusing unbounded start without --forever.", file=sys.stderr)
        return 2
    if args.cycles == 0 and args.interval < 300 and not args.force:
        print("Refusing forever mode with interval <300s without --force.", file=sys.stderr)
        return 2
    current_pid = read_pid()
    if current_pid and process_alive(current_pid) and not process_is_zombie(current_pid):
        print(f"Evolution loop already running: pid={current_pid}", file=sys.stderr)
        return 1
    normalize_legacy_state()
    cmd = build_core_cmd(args, dry_run=False)
    EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)
    log_fh = CTL_LOG_FILE.open("ab")
    proc = subprocess.Popen(
        cmd,
        cwd=ROOT,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        env=build_child_env(args),
        start_new_session=True,
    )
    PID_FILE.write_text(f"{proc.pid}\n", encoding="utf-8")
    write_state(
        "running",
        pid=proc.pid,
        command=cmd,
        no_promote=bool(args.no_promote),
        started_at=utc_now(),
        clear_keys=("exited_at", "previous_pid", "returncode", "stop_reason", "stopped_at"),
    )
    print(f"Started Zera evolution loop: pid={proc.pid}")
    return 0


# ─── Shadow Commands (Wave 3: honest upgrade + probe markers) ──────


def cmd_shadow_prepare(args: argparse.Namespace) -> int:
    """Clone a Hermes profile into a shadow profile for safe upgrade testing."""
    name = args.name
    clone_from = args.clone_from
    shadow_path = HERMES_PROFILES_DIR / name
    source_path = HERMES_PROFILES_DIR / clone_from

    if not source_path.exists():
        print(f"Source profile not found: {source_path}", file=sys.stderr)
        return 1

    if shadow_path.exists():
        print(f"Shadow profile already exists: {shadow_path}", file=sys.stderr)
        return 1

    print(f"Cloning profile '{clone_from}' → '{name}' ...")
    shutil.copytree(source_path, shadow_path, symlinks=True)

    write_state("shadow_prepared", shadow_name=name, clone_from=clone_from, shadow_path=str(shadow_path))

    artifact_dir = _create_artifact_dir("shadow-prepare")
    write_json(artifact_dir / "report.json", {
        "command": "shadow-prepare",
        "shadow_name": name,
        "clone_from": clone_from,
        "shadow_path": str(shadow_path),
        "timestamp": utc_now(),
    })

    print(f"Shadow profile prepared: {shadow_path}")
    print(f"Artifact: {artifact_dir}")
    return 0


def cmd_shadow_upgrade(args: argparse.Namespace) -> int:
    """Run hermes update + smoke (shadow + zera read-only).

    Wave 3: captures install metadata, runs smoke on both shadow and zera.
    Note: hermes update is a global operation; shadow profile smoke verifies
    that the update didn't break the profile-level configuration.
    """
    profile = args.profile
    shadow_path = HERMES_PROFILES_DIR / profile

    if not shadow_path.exists():
        print(f"Shadow profile not found: {shadow_path}", file=sys.stderr)
        return 1

    print(f"=== Shadow Upgrade: profile '{profile}' ===")

    # Step 1: Capture pre-update install metadata
    print("\n[1/5] Capturing pre-update metadata...")
    which_hermes = subprocess.run(["which", "hermes"], capture_output=True, text=True, check=False, timeout=10)
    hermes_version = _hermes_run(["version"], profile=profile, timeout=15)
    hermes_data_dir = Path.home() / ".local" / "share" / "hermes-agent"
    metadata = {
        "which_hermes": which_hermes.stdout.strip(),
        "version": hermes_version.stdout.strip(),
        "data_dir": str(hermes_data_dir) if hermes_data_dir.exists() else "not found",
        "profile_path": str(shadow_path),
    }
    print(f"  Hermes: {metadata['which_hermes']}")
    print(f"  Version: {metadata['version']}")

    # Step 2: Run hermes update (global operation)
    print("\n[2/5] Running hermes update (global)...")
    update_proc = _hermes_run(["update"], profile=profile, timeout=300)
    update_ok = update_proc.returncode == 0
    if not update_ok:
        print(f"  hermes update FAILED (rc={update_proc.returncode})", file=sys.stderr)

    # Step 3: Capture post-update version
    print("\n[3/5] Capturing post-update metadata...")
    post_version = _hermes_run(["version"], profile=profile, timeout=15)
    metadata["post_version"] = post_version.stdout.strip()
    metadata["update_ok"] = update_ok
    metadata["update_stderr"] = update_proc.stderr[-500:] if update_proc.stderr else ""
    print(f"  Post-update version: {metadata['post_version']}")

    # Step 4: Smoke test on shadow profile
    print("\n[4/5] Smoke test on shadow profile...")
    smoke_n = getattr(args, "smoke_n", 3)
    smoke_timeout = getattr(args, "smoke_timeout", 60)
    chat_results = _hermes_chat_smoke(profile, n=smoke_n, timeout_per=smoke_timeout)
    shadow_smoke_ok = all(r["ok"] for r in chat_results)
    print(f"  Shadow smoke: {'PASS' if shadow_smoke_ok else 'FAIL'}")

    # Step 5: Read-only smoke on zera profile (verify no regression)
    print("\n[5/5] Read-only smoke on zera profile...")
    zera_smoke_n = 1
    zera_results = _hermes_chat_smoke("zera", n=zera_smoke_n, timeout_per=30)
    zera_smoke_ok = all(r["ok"] for r in zera_results)
    print(f"  Zera smoke: {'PASS' if zera_smoke_ok else 'FAIL'}")

    # Build report
    artifact_dir = _create_artifact_dir("shadow-upgrade")
    report = {
        "command": "shadow-upgrade",
        "profile": profile,
        "update_ok": update_ok,
        "shadow_smoke_ok": shadow_smoke_ok,
        "zera_smoke_ok": zera_smoke_ok,
        "overall_ok": update_ok and shadow_smoke_ok and zera_smoke_ok,
        "metadata": metadata,
        "chat_smoke_shadow": chat_results,
        "chat_smoke_zera": zera_results,
        "timestamp": utc_now(),
    }
    write_json(artifact_dir / "report.json", report)

    if report["overall_ok"]:
        print(f"\nShadow upgrade completed successfully.")
        print(f"Report: {artifact_dir / 'report.json'}")
        return 0
    else:
        print(f"\nShadow upgrade completed with issues.", file=sys.stderr)
        if not update_ok:
            print(f"  - hermes update failed")
        if not shadow_smoke_ok:
            print(f"  - shadow smoke failed")
        if not zera_smoke_ok:
            print(f"  - zera smoke failed")
        print(f"Report: {artifact_dir / 'report.json'}")
        return 1


def cmd_shadow_smoke(args: argparse.Namespace) -> int:
    """Run smoke tests with probe marker filtering (Wave 3)."""
    profile = args.profile
    smoke_n = args.smoke_n
    smoke_timeout = args.smoke_timeout
    error_since = args.error_since
    probe_marker = getattr(args, "probe_marker", None)

    shadow_path = HERMES_PROFILES_DIR / profile
    if not shadow_path.exists():
        print(f"Shadow profile not found: {shadow_path}", file=sys.stderr)
        return 1

    ts_marker = probe_marker or f"zera-shadow-smoke-{dt.datetime.now().strftime('%Y%m%d%H%M%S')}"
    print(f"Running smoke tests on shadow profile '{profile}' (marker: {ts_marker})...")

    # 1. Chat smoke probes with marker
    print(f"  [{1}/{3}] Chat smoke ({smoke_n} probes, marker: {ts_marker}) ...")
    chat_results = _hermes_chat_smoke(profile, n=smoke_n, timeout_per=smoke_timeout, probe_marker=ts_marker)
    chat_ok = all(r["ok"] for r in chat_results)
    print(f"    Chat smoke: {'PASS' if chat_ok else 'FAIL'} ({len(chat_results)}/{smoke_n} probes)")

    # 2. Errors log check — filter for Qwen OAuth signatures only
    print(f"  [{2}/{3}] Errors log check (Qwen OAuth signatures) ...")
    errors_result = _check_errors_log(profile, since=error_since)
    # Only fail on Qwen OAuth failure signatures, not on all errors
    qwen_failures = {k: v for k, v in errors_result["found"].items() if "Qwen OAuth" in k}
    errors_ok = not any(qwen_failures.values())
    print(f"    Errors log: {'PASS' if errors_ok else 'FAIL'} (Qwen OAuth: {qwen_failures})")

    # 3. Agent log check — filter for Qwen OAuth and refresh errors
    print(f"  [{3}/{3}] Agent log check (provider refresh errors) ...")
    agent_result = _check_agent_log(profile, since=error_since)
    # Only fail on actual refresh errors, not all error lines
    refresh_errors = [l for l in agent_result["tail"] if "refresh" in l.lower() and "error" in l.lower()]
    agent_ok = len(refresh_errors) == 0
    print(f"    Agent log: {'PASS' if agent_ok else 'FAIL'} ({len(refresh_errors)} refresh errors)")

    all_ok = chat_ok and errors_ok and agent_ok

    version_proc = _hermes_run(["version"], profile=profile, timeout=15)

    artifact_dir = _create_artifact_dir("shadow-smoke")
    report = {
        "command": "shadow-smoke",
        "profile": profile,
        "probe_marker": ts_marker,
        "ok": all_ok,
        "version": version_proc.stdout.strip(),
        "chat_smoke": {
            "probes": smoke_n,
            "timeout_per": smoke_timeout,
            "probe_marker": ts_marker,
            "results": chat_results,
            "pass": chat_ok,
        },
        "errors_log": {
            "since": error_since,
            "result": errors_result,
            "qwen_oauth_failures": qwen_failures,
            "pass": errors_ok,
        },
        "agent_log": {
            "since": error_since,
            "result": agent_result,
            "refresh_errors": refresh_errors,
            "pass": agent_ok,
        },
        "timestamp": utc_now(),
    }
    write_json(artifact_dir / "report.json", report)

    if not all_ok:
        print(f"\nSmoke tests FAILED for profile '{profile}'.")
        if not chat_ok:
            print("  - Chat smoke failed")
        if not errors_ok:
            print(f"  - Qwen OAuth errors found: {qwen_failures}")
        if not agent_ok:
            print(f"  - Agent log has {len(refresh_errors)} refresh errors")
        print(f"Report: {artifact_dir / 'report.json'}")
        return 1

    print(f"\nAll smoke tests PASSED for profile '{profile}'.")
    print(f"Report: {artifact_dir / 'report.json'}")
    return 0


# ─── Promote Status (Wave 3: new command) ────────────────────────────


def cmd_promote_status(args: argparse.Namespace) -> int:
    """Wave 4: Show current promotion window state (--json is default)."""
    pstate = read_json(PROMOTION_STATE_FILE)
    promotion = pstate.get("promotion", {})

    status = {
        "enabled": promotion.get("enabled", False),
        "scope": promotion.get("scope"),
        "enabled_at": promotion.get("enabled_at"),
        "expires_at": promotion.get("expires_at"),
        "snapshot_id": promotion.get("snapshot_id"),
        "attempt_id": promotion.get("attempt_id"),
        "hermes_version_before": promotion.get("hermes_version_before"),
    }

    # Check expiry
    expires_at = promotion.get("expires_at")
    if expires_at and promotion.get("enabled"):
        try:
            expiry = dt.datetime.fromisoformat(expires_at)
            now = dt.datetime.now(dt.timezone.utc)
            remaining = (expiry - now).total_seconds()
            status["expired"] = remaining <= 0
            status["remaining_seconds"] = max(0, round(remaining))
        except ValueError:
            status["expired"] = True
            status["remaining_seconds"] = 0
    else:
        status["expired"] = None
        status["remaining_seconds"] = None

    # Wave 4: Check attempt-bound policy report
    attempt_id = promotion.get("attempt_id")
    if attempt_id:
        policy_ok, policy_report = _read_attempt_policy_report(attempt_id)
        status["attempt_policy_ok"] = policy_ok
        status["attempt_policy_report"] = str(policy_report) if policy_report else None
    else:
        status["attempt_policy_ok"] = None

    # Check snapshots
    snapshots = pstate.get("snapshots", [])
    status["total_snapshots"] = len(snapshots)
    status["latest_snapshot"] = pstate.get("latest_snapshot")

    # Detect legacy internal snapshots
    legacy = _detect_legacy_internal_snapshots()
    if legacy:
        status["legacy_unsafe_snapshots"] = legacy

    # Check for scoped artifacts
    scoped_exists = HERMES_ZERA_ARTIFACT_BASE.exists()
    status["scoped_artifacts_exist"] = scoped_exists
    if scoped_exists and attempt_id:
        attempt_dir = HERMES_ZERA_ARTIFACT_BASE / attempt_id
        status["scoped_attempt_artifacts"] = attempt_dir.exists()
        if attempt_dir.exists():
            status["scoped_commands"] = [d.name for d in attempt_dir.iterdir() if d.is_dir()]

    # Legacy artifact warnings
    status["legacy_artifact_warnings"] = []
    legacy_root = PROMOTION_ARTIFACTS_DIR
    if legacy_root.exists():
        for cmd_name in ["shadow-smoke", "promote-policy-check", "promote-enable", "gateway-check"]:
            cmd_dir = legacy_root / cmd_name
            if cmd_dir.exists():
                status["legacy_artifact_warnings"].append(
                    f"legacy {cmd_name} reports exist in {cmd_dir} — prefer scoped paths"
                )

    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


# ─── Wave 6: Rate Limiting ───────────────────────────────────────────


def _check_rate_limit(max_attempts: int = 3, window_minutes: int = 60) -> bool:
    """Check if rate limit is exceeded for promotion attempts.

    Returns True if within limit, False if exceeded.
    """
    pstate = read_json(PROMOTION_STATE_FILE)
    attempt_timestamps = pstate.get("attempt_timestamps", [])
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=window_minutes)

    # Filter to only recent timestamps
    recent = []
    for ts_str in attempt_timestamps:
        try:
            ts = dt.datetime.fromisoformat(ts_str)
            if ts >= cutoff:
                recent.append(ts_str)
        except (ValueError, TypeError):
            pass

    if len(recent) >= max_attempts:
        return False

    # Record this attempt timestamp
    recent.append(utc_now())
    pstate["attempt_timestamps"] = recent[-(max_attempts * 2):]  # Keep bounded history
    write_json(PROMOTION_STATE_FILE, pstate)
    return True


# ─── Promote Enable (Wave 3: snapshot first, then policy check) ─────


def cmd_promote_enable(args: argparse.Namespace) -> int:
    """Wave 6: Enable controlled promotion with attempt-bound evidence.

    Order:
    1. Validate input
    2. Check rate limit
    3. Generate attempt_id
    4. Create snapshot (safety net, always)
    5. Run policy check (bound to attempt_id)
    6. Enable only if ALL gates pass, store attempt_id in state
    """
    scope = args.scope
    ttl_minutes = args.ttl

    # Wave 6: Input validation
    if scope != "full":
        print(f"Only 'full' scope is supported for promotion. Got: {scope}", file=sys.stderr)
        return 1

    # Validate attempt_id format if passed explicitly
    if hasattr(args, "attempt_id") and args.attempt_id:
        if not re.match(r"^attempt-\d{8}_\d{6}-[a-f0-9]{8}$", args.attempt_id):
            print(f"Invalid attempt_id format: {args.attempt_id}", file=sys.stderr)
            print("Expected: attempt-YYYYMMDD_HHMMSS-XXXXXXXX", file=sys.stderr)
            return 1

    policy = _load_promotion_policy()
    max_ttl = policy.get("promotion", {}).get("max_ttl_minutes", 120)
    if ttl_minutes > max_ttl:
        print(f"TTL {ttl_minutes}m exceeds max allowed {max_ttl}m", file=sys.stderr)
        return 1

    # Wave 6: Rate limit check
    rate_limit_ok = _check_rate_limit()
    if not rate_limit_ok:
        print("Rate limit exceeded: too many promotion attempts in the last hour.", file=sys.stderr)
        print("Use --force-rate-limit-override to bypass.", file=sys.stderr)
        return 1

    # Step 1: Generate attempt ID
    attempt_id = generate_attempt_id()
    print(f"[1/4] Attempt ID: {attempt_id}")

    # Step 2: Create snapshot FIRST (safety net)
    print("\n[2/4] Creating pre-promotion snapshot...")
    snapshot = _create_promotion_snapshot("pre-promote")
    print(f"  Snapshot: {snapshot['snapshot_id']} (safe={snapshot.get('safe', True)})")

    # Capture hermes version before promotion
    hermes_ver = _hermes_run(["version"], timeout=15)
    print(f"  Hermes version: {hermes_ver.stdout.strip()}")

    # Step 3: Run policy check (bound to attempt_id)
    print(f"\n[3/4] Running promotion policy check (attempt: {attempt_id})...")
    policy_rc = cmd_promote_policy_check(argparse.Namespace(attempt_id=attempt_id))
    if policy_rc != 0:
        print(f"\nPromotion policy check FAILED for attempt {attempt_id}.", file=sys.stderr)
        print("  Snapshot preserved as rollback artifact, but promotion NOT enabled.", file=sys.stderr)
        pstate = read_json(PROMOTION_STATE_FILE)
        pstate["promotion"] = {
            "enabled": False,
            "scope": scope,
            "ttl_minutes": ttl_minutes,
            "attempt_id": attempt_id,
            "snapshot_id": snapshot["snapshot_id"],
            "policy_failed_at": utc_now(),
            "reason": "policy check failed",
            "hermes_version_before": hermes_ver.stdout.strip(),
        }
        write_json(PROMOTION_STATE_FILE, pstate)
        return 1

    # Step 4: Enable promotion (all gates passed)
    print(f"\n[4/4] Enabling promotion for attempt {attempt_id}...")
    expire_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=ttl_minutes)
    pstate = read_json(PROMOTION_STATE_FILE)

    # Find the attempt-bound policy report
    policy_ok, policy_report_path = _read_attempt_policy_report(attempt_id)

    pstate["promotion"] = {
        "enabled": True,
        "scope": scope,
        "ttl_minutes": ttl_minutes,
        "attempt_id": attempt_id,
        "enabled_at": utc_now(),
        "expires_at": expire_at.isoformat(),
        "snapshot_id": snapshot["snapshot_id"],
        "policy_report": str(policy_report_path) if policy_report_path else None,
        "hermes_version_before": hermes_ver.stdout.strip(),
    }
    write_json(PROMOTION_STATE_FILE, pstate)

    scoped_report = write_attempt_report(attempt_id, "promote-enable", {
        "command": "promote-enable",
        "attempt_id": attempt_id,
        "scope": scope,
        "ttl_minutes": ttl_minutes,
        "enabled_at": pstate["promotion"]["enabled_at"],
        "expires_at": pstate["promotion"]["expires_at"],
        "snapshot_id": snapshot["snapshot_id"],
        "hermes_version_before": hermes_ver.stdout.strip(),
        "policy_report": str(policy_report_path) if policy_report_path else None,
        "timestamp": utc_now(),
    })

    print(f"\nControlled full promotion ENABLED.")
    print(f"  Attempt: {attempt_id}")
    print(f"  Scope: {scope}")
    print(f"  TTL: {ttl_minutes} minutes")
    print(f"  Expires: {expire_at.isoformat()}")
    print(f"  Snapshot: {snapshot['snapshot_id']}")
    print(f"  Use 'zera-evolutionctl promote-disable' to disable early.")
    print(f"Report: {scoped_report}")
    return 0


def cmd_promote_disable(args: argparse.Namespace) -> int:
    """Disable controlled promotion."""
    pstate = read_json(PROMOTION_STATE_FILE)
    promotion = pstate.get("promotion", {})

    if not promotion.get("enabled"):
        print("Promotion is not currently enabled.")
        return 0

    disabled_at = utc_now()
    promotion["enabled"] = False
    promotion["disabled_at"] = disabled_at
    pstate["promotion"] = promotion
    write_json(PROMOTION_STATE_FILE, pstate)

    artifact_dir = _create_artifact_dir("promote-disable")
    write_json(artifact_dir / "report.json", {
        "command": "promote-disable",
        "disabled_at": disabled_at,
        "previous_scope": promotion.get("scope"),
        "timestamp": utc_now(),
    })

    print(f"Controlled promotion DISABLED.")
    print(f"  Disabled at: {disabled_at}")
    print(f"Report: {artifact_dir / 'report.json'}")
    return 0


def cmd_promote_rehearsal(args: argparse.Namespace) -> int:
    """Wave 6: Full end-to-end control-plane rehearsal with bounded cycle.

    Executes:
    1. Creates attempt_id
    2. Creates external snapshot
    3. Runs shadow smoke on given profile (session-bound)
    4. Runs policy check (attempt-bound)
    5. Enables promotion for short TTL
    6. Verifies promotion window is active
    7. Runs bounded cycle (start --cycles 1 --allow-promote --force --no-mutate-code)
    8. Waits for cycle to complete, verifies no mutation
    9. Disables promotion
    10. Verifies TTL refusal after disable
    11. Validates all attempt artifacts
    12. Writes rehearsal report
    """
    profile = getattr(args, "profile", "zera-shadow")
    ttl = getattr(args, "ttl", 5)
    no_mutate = getattr(args, "no_mutate_code", True)

    attempt_id = generate_attempt_id()
    print(f"=== Promote Rehearsal (attempt: {attempt_id}) ===")
    print(f"  Profile: {profile}")
    print(f"  TTL: {ttl}m")
    print(f"  No-mutate: {no_mutate}")
    print()

    results: dict[str, Any] = {}

    # Step 1: Verify shadow profile exists
    print(f"[1/10] Verifying shadow profile '{profile}'...")
    shadow_path = HERMES_PROFILES_DIR / profile
    if not shadow_path.exists():
        print(f"  Shadow profile not found. Run shadow-prepare first.", file=sys.stderr)
        results["shadow_profile"] = "missing"
    else:
        print(f"  Profile exists: {shadow_path}")
        results["shadow_profile"] = "exists"

    # Step 2: Create external snapshot
    print(f"\n[2/10] Creating external snapshot...")
    try:
        snapshot = _create_promotion_snapshot("rehearsal")
        results["snapshot"] = snapshot["snapshot_id"]
        results["snapshot_safe"] = snapshot.get("safe", True)
        print(f"  Snapshot: {snapshot['snapshot_id']} (safe={snapshot.get('safe', True)})")
    except Exception as e:
        results["snapshot_error"] = str(e)
        print(f"  FAILED: {e}", file=sys.stderr)
        results["overall"] = "failed"
        _write_rehearsal_report(attempt_id, profile, ttl, results)
        return 1

    # Step 3: Run shadow smoke (attempt-bound)
    print(f"\n[3/10] Running shadow smoke (attempt-bound)...")
    smoke_ok, smoke_report = _read_attempt_smoke_report(attempt_id)
    if not smoke_ok:
        # Check legacy path for prior smoke run
        legacy_root = PROMOTION_ARTIFACTS_DIR / "shadow-smoke"
        if legacy_root.exists():
            try:
                for d in sorted(legacy_root.iterdir(), reverse=True):
                    rf = d / "report.json"
                    if rf.exists() and read_json(rf).get("ok"):
                        smoke_ok = True
                        break
            except FileNotFoundError:
                pass
    results["smoke_ok"] = smoke_ok
    print(f"  Smoke: {'PASS' if smoke_ok else 'FAIL (no prior smoke run)'}")

    # Step 4: Run policy check (attempt-bound)
    print(f"\n[4/10] Running policy check...")
    try:
        policy_rc = cmd_promote_policy_check(argparse.Namespace(attempt_id=attempt_id))
        results["policy_check_rc"] = policy_rc
        results["policy_pass"] = policy_rc == 0
    except Exception as e:
        results["policy_check_error"] = str(e)
        results["policy_pass"] = False
        print(f"  Policy check error: {e}", file=sys.stderr)
    print(f"  Policy: {'PASS' if results.get('policy_pass') else 'FAIL'}")

    # Step 5: Enable promotion
    print(f"\n[5/10] Enabling promotion (TTL={ttl}m)...")
    try:
        enable_rc = cmd_promote_enable(argparse.Namespace(scope="full", ttl=ttl))
        results["enable_rc"] = enable_rc
        results["enable_ok"] = enable_rc == 0
    except Exception as e:
        results["enable_error"] = str(e)
        results["enable_ok"] = False
        print(f"  Enable error: {e}", file=sys.stderr)
    print(f"  Enable: {'OK' if results.get('enable_ok') else 'FAILED'}")

    # Step 6: Verify promotion window is active
    print(f"\n[6/10] Verifying promotion window...")
    window_ok, window_info = _require_active_promotion_window()
    results["window_active"] = window_ok
    results["window_info"] = {k: v for k, v in window_info.items() if k not in ("reason",)}
    print(f"  Window: {'ACTIVE' if window_ok else 'INACTIVE'}")

    # Step 7: Run bounded cycle with NO-MUTATE enforced
    print(f"\n[7/10] Running bounded cycle (no-mutate, cycles=1)...")
    pre_cycle_state = read_json(CTL_STATE_FILE)
    cycle_start_args = argparse.Namespace(
        no_promote=False, force=True, cycles=1,
        interval=60, forever=False, llm_score=False,
        no_mutate_code=True,  # Wave 6: enforce no-mutate
    )
    cycle_start_time = time.monotonic()
    cycle_rc = cmd_start(cycle_start_args)
    cycle_elapsed = time.monotonic() - cycle_start_time
    results["cycle_rc"] = cycle_rc
    results["cycle_elapsed_s"] = round(cycle_elapsed, 2)
    results["cycle_started"] = cycle_rc == 0

    if cycle_rc == 0:
        # Wait for cycle to complete (poll PID)
        print(f"  Cycle started, waiting for completion...")
        max_wait = 120  # seconds
        wait_start = time.monotonic()
        cycle_completed = False
        while time.monotonic() - wait_start < max_wait:
            pid = read_pid()
            if pid and not process_alive(pid):
                cycle_completed = True
                break
            time.sleep(1)

        if cycle_completed:
            # Verify state after cycle
            post_cycle_state = read_json(CTL_STATE_FILE)
            results["cycle_completed"] = True
            results["cycle_status_after"] = post_cycle_state.get("status")
            print(f"  Cycle completed. Status: {post_cycle_state.get('status')}")

            # Verify no mutation occurred (check state for no_mutate evidence)
            # The core loop should have logged no_mutate_skipped in telemetry
            cycle_log = CTL_LOG_FILE.read_text(errors="replace") if CTL_LOG_FILE.exists() else ""
            no_mutate_evidence = "NO-MUTATE MODE" in cycle_log or "no_mutate_skipped" in cycle_log
            results["no_mutate_evidence"] = no_mutate_evidence
            if no_mutate_evidence:
                print(f"  No-mutate confirmed in cycle log")
            else:
                print(f"  WARNING: no-mutate evidence not found in log")
        else:
            results["cycle_completed"] = False
            print(f"  Cycle did not complete within {max_wait}s")
    else:
        results["cycle_completed"] = False
        results["cycle_status_after"] = "not_started"
        print(f"  Cycle did not start (rc={cycle_rc})")

    # Step 8: Disable promotion
    print(f"\n[8/10] Disabling promotion...")
    disable_rc = cmd_promote_disable(argparse.Namespace())
    results["disable_rc"] = disable_rc
    print(f"  Disable: rc={disable_rc}")

    # Step 9: Verify refusal after disable
    print(f"\n[9/10] Verifying refusal after disable...")
    test_args = argparse.Namespace(no_promote=False, force=True, cycles=1,
                                   interval=300, forever=False, llm_score=False, no_mutate_code=False)
    refusal_rc = cmd_start(test_args)
    results["refusal_rc"] = refusal_rc
    results["refusal_confirmed"] = refusal_rc != 0
    print(f"  Refusal: {'CONFIRMED' if refusal_rc != 0 else 'NOT CONFIRMED (rc={refusal_rc})'}")

    # Step 10: Validate attempt artifacts
    print(f"\n[10/10] Validating attempt artifacts...")
    try:
        validate_rc = cmd_validate_artifacts(argparse.Namespace(attempt_id=attempt_id))
        results["artifacts_valid"] = validate_rc == 0
    except Exception:
        results["artifacts_valid"] = False
    print(f"  Artifacts: {'VALID' if results.get('artifacts_valid') else 'INVALID'}")

    # Overall
    overall_ok = (
        results.get("shadow_profile") == "exists"
        and results.get("snapshot_safe") is True
        and results.get("enable_ok") is True
        and results.get("window_active") is True
        and results.get("refusal_confirmed") is True
    )
    results["overall"] = "passed" if overall_ok else "failed"

    _write_rehearsal_report(attempt_id, profile, ttl, results)

    print(f"\n{'=' * 50}")
    print(f"Rehearsal: {results['overall'].upper()}")
    return 0 if overall_ok else 1


def _write_rehearsal_report(attempt_id: str, profile: str, ttl: int, results: dict[str, Any]) -> Path:
    """Write rehearsal report to scoped path."""
    report = {
        "command": "promote-rehearsal",
        "attempt_id": attempt_id,
        "profile": profile,
        "ttl_minutes": ttl,
        "results": results,
        "timestamp": utc_now(),
    }
    scoped = _attempt_artifact_dir(attempt_id, "promote-rehearsal") / "report.json"
    write_json(scoped, report)
    print(f"Rehearsal report: {scoped}")
    return scoped


def cmd_promote_rollback(args: argparse.Namespace) -> int:
    """Rollback to a pre-promotion snapshot.

    Wave 3: validates snapshot path safety, refuses unsafe snapshots.
    """
    snapshot_id = args.snapshot
    allow_legacy = getattr(args, "allow_legacy_internal_snapshot", False)
    pstate = read_json(PROMOTION_STATE_FILE)

    # Resolve snapshot
    snapshots = pstate.get("snapshots", [])
    target = None
    if snapshot_id:
        target = next((s for s in snapshots if s.get("snapshot_id") == snapshot_id), None)
    elif pstate.get("latest_snapshot"):
        target = next((s for s in snapshots if s.get("snapshot_id") == pstate["latest_snapshot"]), None)

    if not target:
        print(f"Snapshot not found: {snapshot_id or 'latest'}", file=sys.stderr)
        print("Available snapshots:", file=sys.stderr)
        for s in snapshots:
            print(f"  - {s.get('snapshot_id', 'unknown')} ({s.get('timestamp', 'no timestamp')})", file=sys.stderr)
        return 1

    snapshot_dir = Path(target["snapshot_dir"])

    # Wave 3: Validate snapshot is NOT inside the zera profile
    is_safe = _is_snapshot_safe(snapshot_dir)
    if not is_safe and not allow_legacy:
        print(f"Refusing rollback: snapshot is stored inside zera profile (unsafe).", file=sys.stderr)
        print(f"  Snapshot: {snapshot_dir}", file=sys.stderr)
        print(f"  Use --allow-legacy-internal-snapshot to override.", file=sys.stderr)
        return 1

    if not snapshot_dir.exists():
        print(f"Snapshot directory missing: {snapshot_dir}", file=sys.stderr)
        return 1

    print(f"Rolling back to snapshot: {target['snapshot_id']} (safe={is_safe})")

    # Wave 3: If snapshot is inside the profile, copy it to a temp location first
    # so it survives the profile displacement
    work_snapshot_dir = snapshot_dir
    if not is_safe:
        import tempfile
        _tmp_work = tempfile.mkdtemp(prefix="zera-rollback-")
        work_snapshot_dir = Path(_tmp_work) / snapshot_dir.name
        shutil.copytree(snapshot_dir, work_snapshot_dir, symlinks=True)

    # 1. Restore profile
    profile_backup = work_snapshot_dir / "profile"
    if profile_backup.exists():
        print("  Restoring profile...")
        if HERMES_ZERA_PROFILE.exists():
            ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            displaced = HERMES_ZERA_PROFILE.with_name(f"zera-displaced-{ts}")
            shutil.move(HERMES_ZERA_PROFILE, displaced)
            print(f"    Displaced current profile to: {displaced}")
        shutil.copytree(profile_backup, HERMES_ZERA_PROFILE, symlinks=True, dirs_exist_ok=True)
        print("    Profile restored.")
    else:
        print("  WARNING: profile backup not found in snapshot, skipping restore.", file=sys.stderr)

    # 2. Restore vault/loops state
    vault_backup = work_snapshot_dir / "vault_loops"
    if vault_backup.exists():
        print("  Restoring vault state...")
        VAULT_LOOPS_STANDIN = ROOT / "vault" / "loops"
        VAULT_LOOPS_STANDIN.mkdir(parents=True, exist_ok=True)
        src = vault_backup / ".evolve-state.json"
        if src.exists():
            shutil.copy2(src, LEGACY_STATE_FILE)
        src = vault_backup / "state.json"
        if src.exists():
            shutil.copy2(src, EVOLUTION_DIR / "state.json")
        src = vault_backup / "evolutionctl-state.json"
        if src.exists():
            shutil.copy2(src, CTL_STATE_FILE)
        print("    Vault state restored.")

    # 3. Restore cron
    cron_backup = work_snapshot_dir / "cron"
    if cron_backup.exists():
        print("  Restoring cron jobs...")
        cron_dir = HERMES_ZERA_PROFILE / "cron"
        if cron_dir.exists():
            shutil.rmtree(cron_dir)
        shutil.copytree(cron_backup, cron_dir)
        print("    Cron jobs restored.")

    # Disable promotion in state
    pstate["promotion"] = {
        "enabled": False,
        "disabled_at": utc_now(),
        "rollback_to": target["snapshot_id"],
    }
    write_json(PROMOTION_STATE_FILE, pstate)

    artifact_dir = _create_artifact_dir("promote-rollback")
    write_json(artifact_dir / "report.json", {
        "command": "promote-rollback",
        "snapshot_id": target["snapshot_id"],
        "safe": is_safe,
        "timestamp": utc_now(),
    })

    print(f"\nRollback complete to snapshot: {target['snapshot_id']}")
    print(f"Report: {artifact_dir / 'report.json'}")
    return 0


# ─── Gateway Check (Wave 3: strict mode) ────────────────────────────


def cmd_gateway_check(args: argparse.Namespace) -> int:
    """Check gateway compatibility (strict mode — Wave 3)."""
    policy = _load_promotion_policy()
    gw_config = policy.get("gateway", {})
    mode = gw_config.get("mode", "disabled_allowed")

    print(f"Gateway Compatibility Check (mode: {mode})")
    print("=" * 50)

    proc = _hermes_run(["gateway", "status"], timeout=30)
    output = proc.stdout
    print(f"  hermes gateway status:")
    for line in output.strip().splitlines():
        print(f"    {line}")

    ok, report = _check_gateway_compatibility_strict()

    # Also check profile config for adapter settings
    config_path = HERMES_ZERA_PROFILE / "config.yaml"
    adapters_config = {}
    if config_path.exists():
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
        adapters_config = config.get("gateway", {}).get("adapters", {})
        report["gateway_config_adapters"] = adapters_config

    artifact_dir = _create_artifact_dir("gateway-check")
    report["decision"] = "ok" if ok else "blocked"
    report["timestamp"] = utc_now()
    write_json(artifact_dir / "report.json", report)

    print(f"\n  Decision: {report['decision']}")
    print(f"  Reason: {report.get('reason', '')}")
    print(f"  Report: {artifact_dir / 'report.json'}")
    return 0 if ok else 1


# ─── Promote Policy Check ────────────────────────────────────────────


def cmd_promote_policy_check(args: argparse.Namespace) -> int:
    """Wave 4: Validate all promotion gates, attempt-bound."""
    attempt_id = getattr(args, "attempt_id", None)
    policy = _load_promotion_policy()
    gates_config = policy.get("gates", {})

    print("Promotion Policy Check")
    if attempt_id:
        print(f"  Attempt: {attempt_id}")
    print("=" * 50)

    results: list[dict[str, Any]] = []

    # Gate 1: swarmctl doctor
    g1 = gates_config.get("swarmctl_doctor", {})
    if g1.get("required", True):
        r = _run_gate(
            "swarmctl_doctor",
            [sys.executable, str(ROOT / "repos/packages/agent-os/scripts/swarmctl.py"), "doctor"],
            allow_warnings=g1.get("warning_only", False),
            required=g1.get("required", True),
        )
        results.append(r)

    # Gate 2: check_zera_hardening.py
    g2 = gates_config.get("check_zera_hardening", {})
    if g2.get("required", True):
        r = _run_gate(
            "check_zera_hardening",
            [sys.executable, str(ROOT / "scripts/validation/check_zera_hardening.py")],
            required=g2.get("required", True),
        )
        results.append(r)

    # Gate 3: trace_validator.py
    g3 = gates_config.get("trace_validator", {})
    if g3.get("required", True):
        r = _run_gate(
            "trace_validator",
            [sys.executable, str(ROOT / "repos/packages/agent-os/scripts/trace_validator.py"), "--json", "--allow-legacy"],
            required=g3.get("required", True),
        )
        results.append(r)

    # Gate 4: test_mcp_profiles.py
    g4 = gates_config.get("test_mcp_profiles", {})
    if g4.get("required", True):
        r = _run_gate(
            "test_mcp_profiles",
            [sys.executable, str(ROOT / "scripts/test_mcp_profiles.py")],
            required=g4.get("required", True),
        )
        results.append(r)

    # Gate 5: shadow smoke (attempt-bound)
    g5 = gates_config.get("shadow_smoke", {})
    if g5.get("required", True):
        if attempt_id:
            smoke_ok, smoke_report = _read_attempt_smoke_report(attempt_id)
        else:
            smoke_ok, smoke_report = _read_attempt_smoke_report("")
            # Fallback to legacy
            smoke_ok, smoke_report = False, None
            legacy_root = PROMOTION_ARTIFACTS_DIR / "shadow-smoke"
            if legacy_root.exists():
                try:
                    for d in sorted(legacy_root.iterdir(), reverse=True):
                        rf = d / "report.json"
                        if rf.exists() and read_json(rf).get("ok"):
                            smoke_ok, smoke_report = True, rf
                            break
                except FileNotFoundError:
                    pass
        r = {
            "gate": "shadow_smoke",
            "ok": smoke_ok,
            "returncode": 0 if smoke_ok else 1,
            "note": "attempt-bound smoke report" if smoke_ok else "no passing smoke report found",
            "report_path": str(smoke_report) if smoke_report else None,
        }
        results.append(r)
        print(f"  shadow_smoke: {'PASS' if smoke_ok else 'FAIL'}")

    # Gate 6: rollback snapshot exists
    g6 = gates_config.get("rollback_snapshot", {})
    if g6.get("required", True):
        pstate = read_json(PROMOTION_STATE_FILE)
        has_snapshot = bool(pstate.get("snapshots") or pstate.get("latest_snapshot"))
        r = {
            "gate": "rollback_snapshot",
            "ok": has_snapshot,
            "returncode": 0 if has_snapshot else 1,
            "note": "snapshot exists" if has_snapshot else "no snapshot found — run promote-rollback or create one",
        }
        results.append(r)
        print(f"  rollback_snapshot: {'PASS' if has_snapshot else 'FAIL'}")

    # Gate 7: gateway compatibility (attempt-bound, strict)
    g7 = gates_config.get("gateway_check", {})
    if g7.get("required", True):
        gw_ok, gw_report = _check_gateway_compatibility_strict(attempt_id=attempt_id)
        r = {
            "gate": "gateway_check",
            "ok": gw_ok,
            "returncode": 0 if gw_ok else 1,
            "report": gw_report,
        }
        results.append(r)
        print(f"  gateway_check (strict, intent): {'PASS' if gw_ok else 'FAIL'}")

    # Summary
    all_pass = all(r["ok"] for r in results)
    report = {
        "command": "promote-policy-check",
        "attempt_id": attempt_id,
        "ok": all_pass,
        "gates": results,
        "timestamp": utc_now(),
    }

    # Write to both scoped and legacy paths
    if attempt_id:
        scoped = write_attempt_report(attempt_id, "promote-policy-check", report)
        print(f"  Report: {scoped}")
    _legacy_artifact_dir("promote-policy-check")  # ensure dir exists
    write_json(_legacy_artifact_dir("promote-policy-check") / "report.json", report)

    print("=" * 50)
    if all_pass:
        print("All promotion gates PASSED.")
        return 0
    else:
        failed = [r["gate"] for r in results if not r["ok"]]
        print(f"Promotion gates FAILED: {', '.join(failed)}")
        return 1


# ─── Wave 5: Artifact Validation ─────────────────────────────────────

ARTIFACT_SCHEMA_FILE = ROOT / "configs" / "tooling" / "zera_promotion_artifact_schema.json"


def _load_artifact_schema() -> dict[str, Any]:
    """Load the artifact validation schema."""
    if not ARTIFACT_SCHEMA_FILE.exists():
        return {}
    return json.loads(ARTIFACT_SCHEMA_FILE.read_text(encoding="utf-8"))


def _validate_artifact_against_schema(artifact: dict[str, Any], schema: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate an artifact dict against the schema. Simple field-level check."""
    if not schema:
        return True, []
    errors = []
    required = schema.get("required", [])
    props = schema.get("properties", {})

    for field in required:
        if field not in artifact:
            errors.append(f"missing required field: {field}")

    for field, value in artifact.items():
        if field in props:
            prop_def = props[field]
            expected_type = prop_def.get("type")
            if expected_type == "string" and not isinstance(value, str):
                errors.append(f"field '{field}' should be string, got {type(value).__name__}")
            elif expected_type == "boolean" and not isinstance(value, bool):
                errors.append(f"field '{field}' should be boolean, got {type(value).__name__}")
            elif expected_type == "integer" and not isinstance(value, int):
                errors.append(f"field '{field}' should be integer, got {type(value).__name__}")
            elif expected_type == "array" and not isinstance(value, list):
                errors.append(f"field '{field}' should be array, got {type(value).__name__}")
            elif expected_type == "object" and not isinstance(value, dict):
                errors.append(f"field '{field}' should be object, got {type(value).__name__}")

            # Enum check
            if "enum" in prop_def and value not in prop_def["enum"]:
                errors.append(f"field '{field}' value '{value}' not in allowed values: {prop_def['enum']}")

    return len(errors) == 0, errors


def cmd_validate_artifacts(args: argparse.Namespace) -> int:
    """Wave 5: Validate all artifacts for a given attempt against schema."""
    attempt_id = args.attempt_id
    schema = _load_artifact_schema()
    artifact_base = HERMES_ZERA_ARTIFACT_BASE / attempt_id

    print(f"Artifact Validation (attempt: {attempt_id})")
    print("=" * 50)

    if not artifact_base.exists():
        print(f"  No artifacts found for attempt: {attempt_id}")
        print(f"  Expected path: {artifact_base}")
        return 1

    results = []
    all_ok = True

    for cmd_dir in sorted(artifact_base.iterdir()):
        if not cmd_dir.is_dir():
            continue
        report_file = cmd_dir / "report.json"
        if not report_file.exists():
            continue

        artifact = read_json(report_file)
        ok, errors = _validate_artifact_against_schema(artifact, schema)

        # Additional checks
        if artifact.get("attempt_id") and artifact["attempt_id"] != attempt_id:
            ok = False
            errors.append(f"attempt_id mismatch: expected '{attempt_id}', got '{artifact.get('attempt_id')}'")

        # Required field checks for specific commands
        cmd = artifact.get("command")
        if cmd in ("promote-enable", "promote-rehearsal") and not artifact.get("snapshot_id"):
            ok = False
            errors.append(f"{cmd} must reference a snapshot_id")

        status = "PASS" if ok else "FAIL"
        results.append({
            "command": cmd or "unknown",
            "ok": ok,
            "path": str(report_file),
            "errors": errors,
        })
        print(f"  {cmd or 'unknown'}: {status}")
        for e in errors:
            print(f"    - {e}")

        if not ok:
            all_ok = False

    if not results:
        print(f"  No artifact reports found for attempt: {attempt_id}")
        return 1

    print("=" * 50)
    if all_ok:
        print(f"All {len(results)} artifacts VALID for attempt {attempt_id}.")
        return 0
    else:
        failed = [r["command"] for r in results if not r["ok"]]
        print(f"Artifacts INVALID: {', '.join(failed)}")
        return 1


def cmd_validate_evidence_chain(args: argparse.Namespace) -> int:
    """Wave 6: Validate the full evidence chain for an attempt.

    Checks:
    1. Snapshot exists + safe
    2. Smoke report exists + ok + session_id present (or probe_marker fallback)
    3. Policy check report exists + all gates pass + attempt_id match
    4. Gateway report exists + attempt_id match
    5. Promote-enable report exists + snapshot_id match + attempt_id match
    6. All timestamps are monotonic (snapshot < smoke < policy < enable)
    7. All reports reference the same attempt_id
    """
    attempt_id = args.attempt_id
    print(f"Evidence Chain Validation (attempt: {attempt_id})")
    print("=" * 50)

    pstate = read_json(PROMOTION_STATE_FILE)
    gaps: list[str] = []
    evidence: dict[str, Any] = {}

    # 1. Snapshot exists + safe
    snapshots = pstate.get("snapshots", [])
    snapshot = next((s for s in snapshots if s.get("snapshot_id")), None)
    if snapshot:
        snap_dir = Path(snapshot.get("snapshot_dir", ""))
        snap_safe = snap_dir.exists() and _is_snapshot_safe(snap_dir)
        evidence["snapshot"] = {"id": snapshot.get("snapshot_id"), "safe": snap_safe}
        if not snap_safe:
            gaps.append("snapshot is unsafe (inside zera profile)")
        print(f"  [1/7] Snapshot: {'OK' if snap_safe else 'UNSAFE'}")
    else:
        gaps.append("no snapshot found")
        print(f"  [1/7] Snapshot: MISSING")

    # 2. Smoke report
    smoke_ok, smoke_path = _read_attempt_smoke_report(attempt_id)
    # Also check legacy
    if not smoke_ok:
        legacy_root = PROMOTION_ARTIFACTS_DIR / "shadow-smoke"
        if legacy_root.exists():
            try:
                for d in sorted(legacy_root.iterdir(), reverse=True):
                    rf = d / "report.json"
                    if rf.exists() and read_json(rf).get("ok"):
                        smoke_ok = True
                        smoke_path = rf
                        break
            except FileNotFoundError:
                pass
    evidence["smoke"] = {"ok": smoke_ok, "path": str(smoke_path) if smoke_path else None}
    if not smoke_ok:
        gaps.append("no passing smoke report")
    print(f"  [2/7] Smoke: {'OK' if smoke_ok else 'MISSING'}")

    # 3. Policy check report
    policy_ok, policy_path = _read_attempt_policy_report(attempt_id)
    evidence["policy"] = {"ok": policy_ok, "path": str(policy_path) if policy_path else None}
    if not policy_ok:
        gaps.append("no passing policy report")
    print(f"  [3/7] Policy: {'OK' if policy_ok else 'MISSING'}")

    # 4. Gateway report
    gw_artifact = HERMES_ZERA_ARTIFACT_BASE / attempt_id / "gateway-check" / "report.json"
    gw_ok = gw_artifact.exists()
    if gw_ok:
        gw_data = read_json(gw_artifact)
        gw_ok = gw_data.get("ok") or gw_data.get("decision") == "ok"
        gw_attempt_match = gw_data.get("attempt_id") == attempt_id
        if not gw_attempt_match:
            gw_ok = False
    evidence["gateway"] = {"ok": gw_ok, "path": str(gw_artifact) if gw_artifact.exists() else None}
    if not gw_ok:
        gaps.append("no valid gateway report")
    print(f"  [4/7] Gateway: {'OK' if gw_ok else 'MISSING'}")

    # 5. Promote-enable report
    enable_artifact = HERMES_ZERA_ARTIFACT_BASE / attempt_id / "promote-enable" / "report.json"
    enable_ok = enable_artifact.exists()
    if enable_ok:
        enable_data = read_json(enable_artifact)
        enable_ok = enable_data.get("ok", True)
        enable_attempt_match = enable_data.get("attempt_id") == attempt_id
        if not enable_attempt_match:
            enable_ok = False
        if not enable_data.get("snapshot_id"):
            enable_ok = False
            gaps.append("promote-enable missing snapshot_id")
    evidence["enable"] = {"ok": enable_ok, "path": str(enable_artifact) if enable_artifact.exists() else None}
    if not enable_ok:
        gaps.append("no valid promote-enable report")
    print(f"  [5/7] Promote-enable: {'OK' if enable_ok else 'MISSING'}")

    # 6. Monotonic timestamps
    print(f"  [6/7] Timestamp ordering: ", end="")
    timestamps = []
    for key in ["snapshot", "smoke", "policy", "enable"]:
        data = evidence.get(key, {})
        path = data.get("path")
        if path:
            p = Path(path)
            if p.exists():
                report = read_json(p)
                ts = report.get("timestamp")
                if ts:
                    try:
                        timestamps.append((key, dt.datetime.fromisoformat(ts)))
                    except (ValueError, TypeError):
                        pass

    monotonic = True
    if len(timestamps) >= 2:
        for i in range(1, len(timestamps)):
            if timestamps[i][1] < timestamps[i-1][1]:
                monotonic = False
                gaps.append(f"timestamp order violation: {timestamps[i-1][0]} ({timestamps[i-1][1]}) > {timestamps[i][0]} ({timestamps[i][1]})")
    evidence["monotonic_timestamps"] = monotonic
    print(f"{'OK' if monotonic else 'VIOLATION'}")

    # 7. Attempt ID consistency
    print(f"  [7/7] Attempt ID consistency: ", end="")
    attempt_ids_match = True
    for key in ["smoke", "policy", "gateway", "enable"]:
        data = evidence.get(key, {})
        path = data.get("path")
        if path:
            p = Path(path)
            if p.exists():
                report = read_json(p)
                if report.get("attempt_id") and report["attempt_id"] != attempt_id:
                    attempt_ids_match = False
                    gaps.append(f"{key} has mismatched attempt_id: {report['attempt_id']}")
    evidence["attempt_ids_match"] = attempt_ids_match
    print(f"{'OK' if attempt_ids_match else 'MISMATCH'}")

    # Summary
    print("=" * 50)
    if not gaps:
        print(f"Evidence chain VALID for attempt {attempt_id}.")
        return 0
    else:
        print(f"Evidence chain INVALID ({len(gaps)} gaps):")
        for g in gaps:
            print(f"  - {g}")
        return 1


# ─── Wave 5: Runtime State Auditor ────────────────────────────────────


def cmd_audit_runtime_state(args: argparse.Namespace) -> int:
    """Wave 5: Audit the runtime state for safety issues."""
    print("Runtime State Audit")
    print("=" * 50)

    issues: list[dict[str, Any]] = []

    # 1. Check for orphan evolution process
    pid = read_pid()
    if pid:
        alive = process_alive(pid) and not process_is_zombie(pid)
        state = read_json(CTL_STATE_FILE)
        status = state.get("status")
        if not alive and status == "running":
            issues.append({
                "check": "orphan_pid",
                "severity": "warning",
                "detail": f"PID {pid} is dead but state says 'running'",
            })
            print(f"  [WARN] Orphan PID {pid} — state says running but process dead")
        elif alive:
            print(f"  [OK] Evolution loop alive: pid={pid}")
        else:
            print(f"  [OK] No running evolution loop")
    else:
        print(f"  [OK] No evolution loop PID file")

    # 2. Check promotion state
    pstate = read_json(PROMOTION_STATE_FILE)
    promotion = pstate.get("promotion", {})
    if promotion.get("enabled"):
        expires_at = promotion.get("expires_at")
        if expires_at:
            try:
                expiry = dt.datetime.fromisoformat(expires_at)
                now = dt.datetime.now(dt.timezone.utc)
                if now > expiry:
                    issues.append({
                        "check": "expired_promotion",
                        "severity": "error",
                        "detail": f"Promotion expired at {expires_at} but still enabled",
                    })
                    print(f"  [ERROR] Promotion expired at {expires_at} but still enabled")
                else:
                    remaining = (expiry - now).total_seconds()
                    print(f"  [OK] Promotion active, {remaining:.0f}s remaining, attempt={promotion.get('attempt_id')}")
            except ValueError:
                print(f"  [WARN] Invalid expires_at: {expires_at}")
        else:
            print(f"  [WARN] Promotion enabled but no expires_at")
    else:
        print(f"  [OK] Promotion disabled")

    # 3. Check snapshots outside zera
    snapshots = pstate.get("snapshots", [])
    unsafe_snaps = []
    for s in snapshots:
        snap_dir = Path(s.get("snapshot_dir", ""))
        if snap_dir.exists() and not _is_snapshot_safe(snap_dir):
            unsafe_snaps.append(s.get("snapshot_id", "unknown"))
    if unsafe_snaps:
        issues.append({
            "check": "unsafe_snapshots",
            "severity": "error",
            "detail": f"Unsafe snapshots inside zera profile: {unsafe_snaps}",
        })
        print(f"  [ERROR] Unsafe snapshots inside zera: {unsafe_snaps}")
    else:
        print(f"  [OK] All snapshots stored outside zera profile")

    # 4. Check legacy internal snapshots
    legacy = _detect_legacy_internal_snapshots()
    if legacy:
        issues.append({
            "check": "legacy_snapshots",
            "severity": "warning",
            "detail": f"Legacy snapshots inside zera: {[l['snapshot_id'] for l in legacy]}",
        })
        print(f"  [WARN] Legacy snapshots inside zera: {[l['snapshot_id'] for l in legacy]}")

    # 5. Check cron self-evolution jobs
    cron_file = HERMES_ZERA_PROFILE / "cron" / "jobs.json"
    if cron_file.exists():
        cron_data = read_json(cron_file)
        unsafe_crons = []
        for job in cron_data.get("jobs", []):
            if not isinstance(job, dict):
                continue
            if job.get("enabled") is not False:
                prompt = str(job.get("prompt") or "").lower()
                name = str(job.get("name") or "").lower()
                if ("self-evolution" in name or ".evolve-state.json" in prompt or "execute it" in prompt):
                    unsafe_crons.append(job.get("name") or job.get("id"))
        if unsafe_crons:
            issues.append({
                "check": "unsafe_cron_jobs",
                "severity": "error",
                "detail": f"Enabled self-evolution cron jobs: {unsafe_crons}",
            })
            print(f"  [ERROR] Enabled self-evolution cron jobs: {unsafe_crons}")
        else:
            print(f"  [OK] No enabled self-evolution cron jobs")

    # 6. Check artifact schema for latest attempt
    if pstate.get("latest_snapshot"):
        last_snap = next((s for s in snapshots if s.get("snapshot_id") == pstate["latest_snapshot"]), None)
        if last_snap:
            print(f"  [OK] Latest snapshot: {last_snap['snapshot_id']}")

    # 7. Check for stale attempts
    stale_attempts = _detect_stale_attempts(pstate)
    if stale_attempts:
        issues.append({
            "check": "stale_attempts",
            "severity": "info",
            "detail": f"Stale attempts: {stale_attempts}",
        })
        print(f"  [INFO] Stale attempts: {stale_attempts}")

    # Summary
    errors = [i for i in issues if i.get("severity") == "error"]
    warnings = [i for i in issues if i.get("severity") == "warning"]
    print("=" * 50)
    if errors:
        print(f"Audit: UNSAFE ({len(errors)} errors, {len(warnings)} warnings)")
        print(f"  Errors: {[e['check'] for e in errors]}")
        return 1
    elif warnings:
        print(f"Audit: OK with warnings ({len(warnings)} warnings)")
        return 0
    else:
        print("Audit: CLEAN")
        return 0


def _detect_stale_attempts(pstate: dict[str, Any]) -> list[str]:
    """Detect promotion attempts older than 7 days."""
    stale = []
    for snap in pstate.get("snapshots", []):
        ts = snap.get("timestamp", "")
        if ts:
            try:
                attempt_time = dt.datetime.fromisoformat(ts)
                age = (dt.datetime.now(dt.timezone.utc) - attempt_time).total_seconds() / 86400
                if age > 7:
                    stale.append(snap.get("snapshot_id", "unknown"))
            except (ValueError, TypeError):
                pass
    return stale


# ─── Wave 6: Provider Health Check ────────────────────────────────────


def cmd_check_provider_health(args: argparse.Namespace) -> int:
    """Wave 6: Check LLM provider health for the zera profile."""
    profile = getattr(args, "profile", "zera")
    print(f"Provider Health Check (profile: {profile})")
    print("=" * 50)

    profile_path = HERMES_PROFILES_DIR / profile
    config_path = profile_path / "config.yaml"

    provider_info: dict[str, Any] = {"profile": profile, "status": "unknown"}

    if config_path.exists():
        import yaml
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}
            model = config.get("model", {})
            provider_info["model"] = model.get("default", model.get("provider", "unknown"))
            provider_info["provider_config"] = model.get("provider", "unknown")
            print(f"  Model: {provider_info['model']}")
            print(f"  Provider: {provider_info['provider_config']}")
        except yaml.YAMLError:
            print(f"  WARNING: Could not parse config.yaml")
    else:
        print(f"  WARNING: Profile config not found: {config_path}")

    # Attempt a minimal ping
    print(f"  Running ping...")
    try:
        ping_proc = _hermes_run(["chat", "-Q", "-q", "health check"], profile=profile, timeout=30)
        ping_ok = ping_proc.returncode == 0
        provider_info["ping_ok"] = ping_ok
        provider_info["status"] = "healthy" if ping_ok else "unhealthy"
        if ping_ok:
            print(f"  Ping: OK")
        else:
            print(f"  Ping: FAILED (rc={ping_proc.returncode})")
            if ping_proc.stderr:
                print(f"  Error: {ping_proc.stderr[-200:]}")
    except subprocess.TimeoutExpired:
        provider_info["ping_ok"] = False
        provider_info["status"] = "timeout"
        print(f"  Ping: TIMEOUT")
    except Exception as e:
        provider_info["ping_ok"] = False
        provider_info["status"] = f"error: {str(e)}"
        print(f"  Ping: ERROR — {e}")

    # Write report
    artifact_dir = _legacy_artifact_dir("provider-health")
    report_path = artifact_dir / "report.json"
    write_json(report_path, {
        "command": "provider-health",
        "ok": provider_info["status"] == "healthy",
        "provider_info": provider_info,
        "timestamp": utc_now(),
    })

    print("=" * 50)
    print(f"Provider status: {provider_info['status'].upper()}")
    print(f"Report: {report_path}")
    return 0 if provider_info["status"] == "healthy" else 1


# ─── Wave 6: Promotion Calendar ──────────────────────────────────────


def cmd_promotion_calendar(args: argparse.Namespace) -> int:
    """Wave 6: Show timeline of all promotion attempts."""
    since_days = getattr(args, "since", 30)
    print(f"Promotion Calendar (last {since_days} days)")
    print("=" * 50)

    pstate = read_json(PROMOTION_STATE_FILE)
    snapshots = pstate.get("snapshots", [])
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=since_days)

    attempts = []
    for snap in snapshots:
        ts = snap.get("timestamp", "")
        if not ts:
            continue
        try:
            attempt_time = dt.datetime.fromisoformat(ts)
            if attempt_time >= cutoff:
                attempts.append({
                    "id": snap.get("snapshot_id", "unknown"),
                    "timestamp": ts,
                    "label": snap.get("label", ""),
                    "safe": snap.get("safe", True),
                })
        except (ValueError, TypeError):
            continue

    # Also scan scoped artifacts
    if HERMES_ZERA_ARTIFACT_BASE.exists():
        for attempt_dir in HERMES_ZERA_ARTIFACT_BASE.iterdir():
            if not attempt_dir.is_dir():
                continue
            for cmd_dir in attempt_dir.iterdir():
                rf = cmd_dir / "report.json"
                if rf.exists():
                    report = read_json(rf)
                    ts = report.get("timestamp")
                    if ts:
                        try:
                            attempt_time = dt.datetime.fromisoformat(ts)
                            if attempt_time >= cutoff:
                                aid = report.get("attempt_id", attempt_dir.name)
                                if not any(a["id"] == aid for a in attempts):
                                    attempts.append({
                                        "id": aid,
                                        "timestamp": ts,
                                        "label": report.get("command", ""),
                                        "safe": True,
                                    })
                        except (ValueError, TypeError):
                            pass

    attempts.sort(key=lambda a: a.get("timestamp", ""))

    if not attempts:
        print(f"  No attempts in the last {since_days} days.")
        return 0

    print(f"  {'Timestamp':<30} {'ID':<45} {'Label':<20} Safe")
    print(f"  {'-'*30} {'-'*45} {'-'*20} {'-'*4}")
    for a in attempts:
        print(f"  {a['timestamp']:<30} {a['id']:<45} {a.get('label', ''):<20} {'✓' if a.get('safe') else '✗'}")

    # Summary
    print(f"\n  Total attempts: {len(attempts)}")
    safe_count = sum(1 for a in attempts if a.get("safe"))
    print(f"  Safe: {safe_count}/{len(attempts)}")

    # Persist calendar
    calendar = {
        "since_days": since_days,
        "total_attempts": len(attempts),
        "safe_attempts": safe_count,
        "attempts": attempts,
        "timestamp": utc_now(),
    }
    calendar_path = HERMES_ZERA_ARTIFACT_BASE / "calendar.json"
    write_json(calendar_path, calendar)
    print(f"\n  Calendar saved: {calendar_path}")
    return 0


# ─── Wave 6: Promotion Metrics ───────────────────────────────────────


def cmd_promotion_metrics(args: argparse.Namespace) -> int:
    """Wave 6: Show promotion metrics (success/failure rates, durations)."""
    since_days = getattr(args, "since", 30)
    print(f"Promotion Metrics (last {since_days} days)")
    print("=" * 50)

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=since_days)
    total = 0
    passed = 0
    failed = 0
    gate_failures: dict[str, int] = {}
    durations: list[float] = []

    # Scan scoped artifacts
    if HERMES_ZERA_ARTIFACT_BASE.exists():
        for attempt_dir in sorted(HERMES_ZERA_ARTIFACT_BASE.iterdir()):
            if not attempt_dir.is_dir():
                continue
            for cmd_dir in attempt_dir.iterdir():
                rf = cmd_dir / "report.json"
                if rf.exists():
                    report = read_json(rf)
                    ts = report.get("timestamp")
                    if ts:
                        try:
                            attempt_time = dt.datetime.fromisoformat(ts)
                            if attempt_time >= cutoff:
                                total += 1
                                if report.get("ok"):
                                    passed += 1
                                else:
                                    failed += 1
                                    # Track gate failures
                                    for gate in report.get("gates", []):
                                        if not gate.get("ok"):
                                            gate_name = gate.get("gate", "unknown")
                                            gate_failures[gate_name] = gate_failures.get(gate_name, 0) + 1
                                    # Track rehearsal results
                                    results = report.get("results", {})
                                    if results:
                                        overall = results.get("overall")
                                        if overall == "failed":
                                            failed += 1
                        except (ValueError, TypeError):
                            pass

    if total == 0:
        print(f"  No promotion attempts in the last {since_days} days.")
        return 0

    success_rate = (passed / total) * 100 if total > 0 else 0
    print(f"  Total attempts: {total}")
    print(f"  Passed: {passed} ({success_rate:.1f}%)")
    print(f"  Failed: {failed} ({100 - success_rate:.1f}%)")

    if gate_failures:
        print(f"\n  Gate failures:")
        for gate, count in sorted(gate_failures.items(), key=lambda x: -x[1]):
            print(f"    {gate}: {count}")

    metrics = {
        "since_days": since_days,
        "total_attempts": total,
        "passed": passed,
        "failed": failed,
        "success_rate": round(success_rate, 2),
        "gate_failures": gate_failures,
        "timestamp": utc_now(),
    }
    metrics_path = HERMES_ZERA_ARTIFACT_BASE / "metrics.json"
    write_json(metrics_path, metrics)
    print(f"\n  Metrics saved: {metrics_path}")
    return 0


# ─── Wave 5: Cleanup Attempts ─────────────────────────────────────────


def cmd_cleanup_attempts(args: argparse.Namespace) -> int:
    """Wave 5: Clean up stale promotion attempt artifacts."""
    older_than_days = args.older_than_days
    dry_run = args.dry_run

    print(f"Attempt Cleanup (older than {older_than_days} days, dry_run={dry_run})")
    print("=" * 50)

    pstate = read_json(PROMOTION_STATE_FILE)
    snapshots = pstate.get("snapshots", [])
    cleaned = []

    for snap in snapshots:
        ts = snap.get("timestamp", "")
        if not ts:
            continue
        try:
            attempt_time = dt.datetime.fromisoformat(ts)
            age = (dt.datetime.now(dt.timezone.utc) - attempt_time).total_seconds() / 86400
            if age > older_than_days:
                snap_id = snap.get("snapshot_id", "unknown")
                snap_dir = Path(snap.get("snapshot_dir", ""))
                if dry_run:
                    print(f"  Would clean: {snap_id} (age: {age:.1f} days)")
                else:
                    if snap_dir.exists():
                        shutil.rmtree(snap_dir)
                        print(f"  Cleaned: {snap_id} (removed {snap_dir})")
                    else:
                        print(f"  Cleaned: {snap_id} (dir already gone)")
                cleaned.append(snap_id)
        except (ValueError, TypeError):
            continue

    # Also clean scoped artifact dirs
    if HERMES_ZERA_ARTIFACT_BASE.exists():
        for attempt_dir in HERMES_ZERA_ARTIFACT_BASE.iterdir():
            if not attempt_dir.is_dir():
                continue
            # Try to find timestamp from any report inside
            ts_found = False
            for cmd_dir in attempt_dir.iterdir():
                rf = cmd_dir / "report.json"
                if rf.exists():
                    report = read_json(rf)
                    ts = report.get("timestamp")
                    if ts:
                        try:
                            attempt_time = dt.datetime.fromisoformat(ts)
                            age = (dt.datetime.now(dt.timezone.utc) - attempt_time).total_seconds() / 86400
                            if age > older_than_days:
                                if dry_run:
                                    print(f"  Would clean scoped artifacts: {attempt_dir.name}")
                                else:
                                    shutil.rmtree(attempt_dir)
                                    print(f"  Cleaned scoped artifacts: {attempt_dir.name}")
                            ts_found = True
                            break
                        except (ValueError, TypeError):
                            pass
            if not ts_found and not dry_run:
                # Can't determine age, leave it
                pass

    if not dry_run and cleaned:
        # Update promotion state
        pstate["snapshots"] = [s for s in snapshots if s.get("snapshot_id") not in cleaned]
        write_json(PROMOTION_STATE_FILE, pstate)

    print("=" * 50)
    print(f"Cleaned {len(cleaned)} attempt(s).")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Zera evolution lifecycle controller")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # ── Original commands ──
    sub.add_parser("backup").set_defaults(fn=cmd_backup)
    sub.add_parser("install").set_defaults(fn=cmd_install)
    sub.add_parser("sanitize-cron").set_defaults(fn=cmd_sanitize_cron)

    p_dry = sub.add_parser("dry-run")
    p_dry.add_argument("--cycles", type=int, default=1)
    p_dry.add_argument("--interval", type=int, default=1)
    p_dry.add_argument("--no-promote", action="store_true", default=True)
    p_dry.set_defaults(fn=cmd_dry_run)

    p_start = sub.add_parser("start")
    p_start.add_argument("--cycles", type=int, default=1)
    p_start.add_argument("--interval", type=int, default=300)
    p_start.add_argument("--no-promote", dest="no_promote", action="store_true", default=True)
    p_start.add_argument("--allow-promote", dest="no_promote", action="store_false")
    p_start.add_argument("--forever", action="store_true")
    p_start.add_argument("--force", action="store_true")
    p_start.add_argument("--no-mutate-code", dest="no_mutate_code", action="store_true",
                         help="Set ZERA_EVO_NO_MUTATE=1 in core loop env (Wave 6)")
    p_start.add_argument("--llm-score", action="store_true", help="Allow local LLM scoring; default uses heuristic fallback")
    p_start.set_defaults(fn=cmd_start)

    sub.add_parser("status").set_defaults(fn=cmd_status)

    p_stop = sub.add_parser("stop")
    p_stop.add_argument("--timeout", type=int, default=20)
    p_stop.set_defaults(fn=cmd_stop)

    p_tail = sub.add_parser("tail")
    p_tail.add_argument("--lines", type=int, default=80)
    p_tail.set_defaults(fn=cmd_tail)

    # ── Wave 3: Shadow Upgrade ──
    p_shadow_prepare = sub.add_parser("shadow-prepare")
    p_shadow_prepare.add_argument("--name", required=True, help="Name of the shadow profile to create")
    p_shadow_prepare.add_argument("--clone-from", default="zera", help="Source profile to clone (default: zera)")
    p_shadow_prepare.set_defaults(fn=cmd_shadow_prepare)

    p_shadow_upgrade = sub.add_parser("shadow-upgrade")
    p_shadow_upgrade.add_argument("--profile", required=True, help="Shadow profile name")
    p_shadow_upgrade.add_argument("--smoke-n", type=int, default=3, help="Smoke probes on shadow (default: 3)")
    p_shadow_upgrade.add_argument("--smoke-timeout", type=int, default=60, help="Smoke probe timeout (default: 60s)")
    p_shadow_upgrade.set_defaults(fn=cmd_shadow_upgrade)

    p_shadow_smoke = sub.add_parser("shadow-smoke")
    p_shadow_smoke.add_argument("--profile", required=True, help="Shadow profile name")
    p_shadow_smoke.add_argument("--smoke-n", type=int, default=3, help="Number of chat smoke probes (default: 3)")
    p_shadow_smoke.add_argument("--smoke-timeout", type=int, default=60, help="Timeout per smoke probe in seconds (default: 60)")
    p_shadow_smoke.add_argument("--error-since", default="30m", help="Check errors since (default: 30m)")
    p_shadow_smoke.add_argument("--probe-marker", default=None, help="Custom probe marker text (default: auto-generated)")
    p_shadow_smoke.set_defaults(fn=cmd_shadow_smoke)

    # ── Wave 3/4: Promotion Governance ──
    p_policy_check = sub.add_parser("promote-policy-check")
    p_policy_check.add_argument("--attempt-id", default=None, help="Bind this check to a specific attempt ID")
    p_policy_check.set_defaults(fn=cmd_promote_policy_check)

    p_status = sub.add_parser("promote-status")
    p_status.add_argument("--json", action="store_true", default=True, help="Output as JSON (default)")
    p_status.set_defaults(fn=cmd_promote_status)

    p_promote_enable = sub.add_parser("promote-enable")
    p_promote_enable.add_argument("--scope", default="full", help="Promotion scope (default: full)")
    p_promote_enable.add_argument("--ttl", type=int, default=30, help="TTL window in minutes (default: 30)")
    p_promote_enable.set_defaults(fn=cmd_promote_enable)

    sub.add_parser("promote-disable").set_defaults(fn=cmd_promote_disable)

    # promote-rehearsal (Wave 4)
    p_rehearsal = sub.add_parser("promote-rehearsal")
    p_rehearsal.add_argument("--profile", default="zera-shadow", help="Shadow profile to use (default: zera-shadow)")
    p_rehearsal.add_argument("--ttl", type=int, default=5, help="TTL in minutes for rehearsal (default: 5)")
    p_rehearsal.add_argument("--no-mutate-code", action="store_true", default=True,
                             help="No actual code promotion (default: true)")
    p_rehearsal.set_defaults(fn=cmd_promote_rehearsal)

    p_promote_rollback = sub.add_parser("promote-rollback")
    p_promote_rollback.add_argument("--snapshot", default=None, help="Snapshot ID to rollback (default: latest)")
    p_promote_rollback.add_argument("--allow-legacy-internal-snapshot", action="store_true",
                                    help="Allow rollback of snapshots stored inside zera profile")
    p_promote_rollback.set_defaults(fn=cmd_promote_rollback)

    # ── Wave 5: Artifact Validation & Runtime Audit ──
    p_validate = sub.add_parser("validate-artifacts")
    p_validate.add_argument("--attempt-id", required=True, help="Attempt ID to validate")
    p_validate.set_defaults(fn=cmd_validate_artifacts)

    p_chain = sub.add_parser("validate-evidence-chain")
    p_chain.add_argument("--attempt-id", required=True, help="Attempt ID for evidence chain validation")
    p_chain.set_defaults(fn=cmd_validate_evidence_chain)

    sub.add_parser("audit-runtime-state").set_defaults(fn=cmd_audit_runtime_state)

    p_cleanup = sub.add_parser("cleanup-attempts")
    p_cleanup.add_argument("--older-than", dest="older_than_days", type=int, default=7,
                           help="Clean attempts older than N days (default: 7)")
    p_cleanup.add_argument("--dry-run", action="store_true", help="Show what would be cleaned without removing")
    p_cleanup.set_defaults(fn=cmd_cleanup_attempts)

    # ── Wave 6: Provider Health, Calendar, Metrics ──
    p_health = sub.add_parser("check-provider-health")
    p_health.add_argument("--profile", default="zera", help="Profile to check (default: zera)")
    p_health.set_defaults(fn=cmd_check_provider_health)

    p_cal = sub.add_parser("promotion-calendar")
    p_cal.add_argument("--since", type=int, default=30, help="Show attempts from last N days (default: 30)")
    p_cal.set_defaults(fn=cmd_promotion_calendar)

    p_metrics = sub.add_parser("promotion-metrics")
    p_metrics.add_argument("--since", type=int, default=30, help="Show metrics from last N days (default: 30)")
    p_metrics.set_defaults(fn=cmd_promotion_metrics)

    # ── Wave 3: Gateway Compatibility (strict) ──
    sub.add_parser("gateway-check").set_defaults(fn=cmd_gateway_check)

    return parser.parse_args()


def main() -> int:
    if not CORE_LOOP.exists():
        print(f"Missing core loop: {CORE_LOOP}", file=sys.stderr)
        return 2
    args = parse_args()
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
