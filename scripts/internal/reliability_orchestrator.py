#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shlex
import subprocess
import sys
import textwrap
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required for scripts/reliability_orchestrator.py") from exc


ROOT = Path(__file__).resolve().parents[2]
PROGRAM_PATH = ROOT / "configs" / "tooling" / "test_reliability_program.yaml"
MATRIX_PATH = ROOT / "configs" / "tooling" / "test_suite_matrix.yaml"
DEBUG_MAP_PATH = ROOT / "configs" / "tooling" / "debug_surface_map.yaml"


@dataclass
class BucketPlan:
    suite: str
    bucket_id: str
    owner: str
    kind: str
    cwd: Path
    command: str
    debug_command: str | None
    json_command: str | None
    tests: list[str]


class ReliabilityOrchestrator:
    def __init__(self, repo_root: Path = ROOT) -> None:
        self.repo_root = repo_root
        self.program = self._load_yaml(PROGRAM_PATH)
        self.matrix = self._load_yaml(MATRIX_PATH)
        self.debug_map = self._load_yaml(DEBUG_MAP_PATH)
        self.artifacts_root = self.repo_root / self.program["artifacts_root"]
        self.events_path = self.artifacts_root / "events.jsonl"
        self.latest_dir = self.artifacts_root / "latest"
        self.inventory_json = self.repo_root / self.program["inventory"]["report_path"]
        self.inventory_md = self.repo_root / self.program["inventory"]["summary_path"]

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            raise ValueError(f"{path} must parse to a mapping")
        return data

    def suite_names(self) -> list[str]:
        return sorted(self.matrix.get("suites", {}).keys())

    def profile_names(self) -> list[str]:
        return sorted(self.program.get("profiles", {}).keys())

    def resolve_suites(self, suites: list[str] | None, profile: str | None) -> list[str]:
        if suites:
            unknown = sorted(set(suites) - set(self.suite_names()))
            if unknown:
                raise ValueError(f"Unknown suites: {', '.join(unknown)}")
            return suites
        if profile:
            profiles = self.program.get("profiles", {})
            if profile not in profiles:
                raise ValueError(f"Unknown profile: {profile}")
            return list(profiles[profile]["suites"])
        raise ValueError("Specify --suite or --profile")

    def _bucket_files(self, bucket: dict[str, Any]) -> list[str]:
        cwd = self.repo_root / bucket.get("cwd", ".")
        if bucket["kind"] == "pytest_list":
            return list(bucket.get("include", []))
        if bucket["kind"] != "pytest_glob":
            return []
        files: list[str] = []
        for pattern in bucket.get("include_globs", []):
            files.extend(
                str(path.relative_to(cwd)).replace(os.sep, "/")
                for path in sorted(cwd.glob(pattern))
                if path.is_file()
            )
        excludes = bucket.get("exclude", [])
        if excludes:
            filtered: list[str] = []
            for file in files:
                if any(fnmatch.fnmatch(file, e["pattern"]) for e in excludes):
                    continue
                filtered.append(file)
            files = filtered
        return sorted(dict.fromkeys(files))

    def _build_bucket_plan(self, suite: str, bucket: dict[str, Any]) -> BucketPlan:
        kind = bucket["kind"]
        cwd = self.repo_root / bucket.get("cwd", ".")
        tests = self._bucket_files(bucket)

        if kind in {"pytest_list", "pytest_glob"}:
            if not tests:
                raise ValueError(f"{suite}:{bucket['id']} resolved to no tests")
            quoted = " ".join(shlex.quote(test) for test in tests)
            command = f"uv run pytest {quoted} -q"
        elif kind == "shell":
            command = bucket["command"]
        else:
            raise ValueError(f"Unsupported bucket kind: {kind}")

        return BucketPlan(
            suite=suite,
            bucket_id=bucket["id"],
            owner=bucket["owner"],
            kind=kind,
            cwd=cwd,
            command=command,
            debug_command=bucket.get("debug_command"),
            json_command=bucket.get("json_command"),
            tests=tests,
        )

    def suite_plan(self, suite: str) -> dict[str, Any]:
        suites = self.matrix.get("suites", {})
        if suite not in suites:
            raise ValueError(f"Unknown suite: {suite}")
        config = suites[suite]
        buckets = [self._build_bucket_plan(suite, bucket) for bucket in config.get("buckets", [])]
        return {
            "suite": suite,
            "blocking": bool(config.get("blocking", False)),
            "trigger": list(config.get("trigger", [])),
            "timeout_seconds": int(config.get("timeout_seconds", 0)),
            "expected_artifacts": list(config.get("expected_artifacts", [])),
            "buckets": [
                {
                    "id": b.bucket_id,
                    "owner": b.owner,
                    "kind": b.kind,
                    "cwd": str(b.cwd.relative_to(self.repo_root)),
                    "command": b.command,
                    "tests": b.tests,
                    "debug_command": b.debug_command,
                    "json_command": b.json_command,
                    "allowed_exit_codes": list(config.get("buckets", [])[idx].get("allowed_exit_codes", [0])),
                    "quarantine": config.get("buckets", [])[idx].get("quarantine"),
                }
                for idx, b in enumerate(buckets)
            ],
        }

    def _suite_summary_filename(self, suite: str) -> str | None:
        mapping = {
            "doctor": "doctor-summary.json",
            "benchmark": "benchmark-summary.json",
            "governance": "governance-summary.json",
        }
        return mapping.get(suite)

    def _write_suite_summary(self, run_dir: Path, suite_result: dict[str, Any]) -> None:
        filename = self._suite_summary_filename(suite_result["suite"])
        if filename is None:
            return
        payload = {
            "generated_at": self._ts(),
            "suite": suite_result["suite"],
            "status": suite_result["status"],
            "buckets": suite_result["buckets"],
        }
        for target in (run_dir / suite_result["suite"] / filename, self.latest_dir / filename):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def profile_plan(self, profile: str) -> dict[str, Any]:
        suites = self.resolve_suites(None, profile)
        return {
            "profile": profile,
            "suites": [self.suite_plan(suite) for suite in suites],
        }

    def inventory(self) -> dict[str, Any]:
        test_patterns = self.program["inventory"]["scan"]["test_patterns"]
        validator_patterns = self.program["inventory"]["scan"]["validator_patterns"]
        doctor_patterns = self.program["inventory"]["scan"]["doctor_patterns"]
        benchmark_patterns = self.program["inventory"]["scan"]["benchmark_patterns"]
        include_patterns = self.program["scope"]["first_party_include"]
        exclude_patterns = [row["path"] for row in self.program["scope"]["excluded_from_blocking"]]
        exclude_patterns.extend(self.program["scope"].get("inventory_exclude", []))

        def in_scope(rel_path: str) -> bool:
            included = any(fnmatch.fnmatch(rel_path, pattern) for pattern in include_patterns)
            excluded = any(fnmatch.fnmatch(rel_path, pattern) for pattern in exclude_patterns)
            return included and not excluded

        def collect(patterns: list[str]) -> list[str]:
            files: list[str] = []
            for pattern in patterns:
                files.extend(
                    str(path.relative_to(self.repo_root)).replace(os.sep, "/")
                    for path in sorted(self.repo_root.glob(pattern))
                    if path.is_file() and in_scope(str(path.relative_to(self.repo_root)).replace(os.sep, "/"))
                )
            return sorted(dict.fromkeys(files))

        tests = collect(test_patterns)
        validators = collect(validator_patterns)
        doctors = collect(doctor_patterns)
        benchmarks = collect(benchmark_patterns)

        excluded = self.program["scope"]["excluded_from_blocking"]
        first_party_roots = [rule for rule in self.program["scope"]["first_party_include"]]

        payload = {
            "generated_at": self._ts(),
            "first_party_roots": first_party_roots,
            "excluded_from_blocking": excluded,
            "counts": {
                "tests": len(tests),
                "validators": len(validators),
                "doctors": len(doctors),
                "benchmarks": len(benchmarks),
            },
            "tests": tests,
            "validators": validators,
            "doctors": doctors,
            "benchmarks": benchmarks,
            "suite_split": {
                suite: [bucket["id"] for bucket in self.suite_plan(suite)["buckets"]]
                for suite in self.suite_names()
            },
        }
        return payload

    def write_inventory(self) -> dict[str, Any]:
        payload = self.inventory()
        self.inventory_json.parent.mkdir(parents=True, exist_ok=True)
        self.inventory_md.parent.mkdir(parents=True, exist_ok=True)
        self.inventory_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        md = [
            "# Reliability Inventory",
            "",
            f"- generated_at: `{payload['generated_at']}`",
            f"- tests: `{payload['counts']['tests']}`",
            f"- validators: `{payload['counts']['validators']}`",
            f"- doctors: `{payload['counts']['doctors']}`",
            f"- benchmarks: `{payload['counts']['benchmarks']}`",
            "",
            "## Suite Split",
        ]
        for suite, buckets in payload["suite_split"].items():
            md.append(f"- `{suite}`: {', '.join(f'`{bucket}`' for bucket in buckets)}")
        self.inventory_md.write_text("\n".join(md) + "\n", encoding="utf-8")
        return payload

    def _ts(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self.artifacts_root.mkdir(parents=True, exist_ok=True)
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": self._ts(),
            "run_id": run_id,
            "event_type": event_type,
            "data": payload,
        }
        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _classify_failure(self, suite: str, text: str) -> str:
        data = text.lower()
        checks = [
            ("syntax_or_parse", ["syntaxerror", "invalid yaml", "invalid json", "parseerror"]),
            ("contract_violation", ["missing required", "invalid", "schema", "contract"]),
            ("governance_boundary", ["governance", "autonomy", "approval", "policy", "zera"]),
            ("benchmark_regression", ["benchmark", "pass rate", "strict"]),
            ("observability_gap", ["trace", "artifact missing", "events.jsonl", "observability"]),
            ("routing_logic", ["routing", "router", "model alias"]),
            ("integration_surface", ["npm test", "integration", "mcp", "telegram"]),
            ("flaky_or_nondeterministic", ["flaky", "timed out", "timeout", "race"]),
            ("tooling_or_env", ["not found", "no module named", "command not found", "uv", "npm"]),
        ]
        for failure_class, needles in checks:
            if any(needle in data for needle in needles):
                return failure_class
        if suite == "doctor":
            return "tooling_or_env"
        return "contract_violation"

    def run(
        self,
        suites: list[str],
        dry_run: bool = False,
        continue_on_fail: bool = False,
        machine_readable: bool = False,
    ) -> dict[str, Any]:
        run_id = uuid.uuid4().hex[:12]
        run_dir = self.artifacts_root / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        self.latest_dir.mkdir(parents=True, exist_ok=True)

        result: dict[str, Any] = {"run_id": run_id, "suites": [], "status": "ok"}
        failure_summary: dict[str, Any] | None = None
        executed_plan: list[dict[str, Any]] = []

        for suite in suites:
            plan = self.suite_plan(suite)
            executed_plan.append(plan)
            self._event(run_id, "suite_started", {"suite": suite, "blocking": plan["blocking"]})
            if suite == "doctor":
                self._event(run_id, "doctor_started", {"suite": suite})
            suite_result = {"suite": suite, "status": "ok", "buckets": []}
            for bucket in plan["buckets"]:
                bucket_dir = run_dir / suite / bucket["id"]
                bucket_dir.mkdir(parents=True, exist_ok=True)
                self._event(run_id, "bucket_started", {"suite": suite, "bucket": bucket["id"]})
                command = bucket.get("json_command") if machine_readable and bucket.get("json_command") else bucket["command"]
                bucket_result = {
                    "id": bucket["id"],
                    "owner": bucket["owner"],
                    "kind": bucket["kind"],
                    "cwd": bucket["cwd"],
                    "command": command,
                    "status": "planned" if dry_run else "ok",
                }
                allowed_exit_codes = set(bucket.get("allowed_exit_codes") or [0])

                if not dry_run:
                    proc = subprocess.run(
                        command,
                        shell=True,
                        cwd=self.repo_root / bucket["cwd"],
                        capture_output=True,
                        text=True,
                    )
                    (bucket_dir / "stdout.log").write_text(proc.stdout, encoding="utf-8")
                    (bucket_dir / "stderr.log").write_text(proc.stderr, encoding="utf-8")
                    bucket_result["exit_code"] = proc.returncode
                    if proc.returncode not in allowed_exit_codes:
                        bucket_result["status"] = "failed"
                        suite_result["status"] = "failed"
                        result["status"] = "failed"
                        failure_class = self._classify_failure(suite, proc.stdout + "\n" + proc.stderr)
                        debug_entry = self.debug_map["failure_classes"][failure_class]
                        failure_summary = {
                            "run_id": run_id,
                            "suite": suite,
                            "bucket": bucket["id"],
                            "failure_class": failure_class,
                            "command": command,
                            "cwd": bucket["cwd"],
                            "artifact_dir": str(bucket_dir.relative_to(self.repo_root)),
                            "first_triage_command": debug_entry["first_triage_command"],
                            "doctor_command": debug_entry["doctor_command"],
                            "rollback_action": debug_entry["rollback_action"],
                            "escalation_path": debug_entry["escalation_path"],
                        }
                        self._event(run_id, "suite_failed", failure_summary)
                        if suite == "governance":
                            self._event(run_id, "governance_validation_failed", failure_summary)
                        if not continue_on_fail:
                            suite_result["buckets"].append(bucket_result)
                            break
                    elif proc.returncode != 0:
                        bucket_result["status"] = "quarantined"
                        bucket_result["quarantine"] = bucket.get("quarantine")
                        self._event(
                            run_id,
                            "quarantine_enter",
                            {
                                "suite": suite,
                                "bucket": bucket["id"],
                                "exit_code": proc.returncode,
                                "quarantine": bucket.get("quarantine"),
                            },
                        )
                    else:
                        self._event(run_id, "bucket_completed", {"suite": suite, "bucket": bucket["id"], "status": "ok"})
                suite_result["buckets"].append(bucket_result)
            result["suites"].append(suite_result)
            self._write_suite_summary(run_dir, suite_result)
            if suite_result["status"] == "ok":
                self._event(run_id, "suite_completed", {"suite": suite, "status": "ok"})
                if suite == "doctor":
                    self._event(run_id, "doctor_completed", {"suite": suite, "status": "ok"})
                if suite == "benchmark":
                    self._event(run_id, "benchmark_refreshed", {"suite": suite, "status": "ok"})
            if suite_result["status"] == "failed" and not continue_on_fail:
                break

        manifest = {
            "run_id": run_id,
            "generated_at": self._ts(),
            "suites": executed_plan,
            "dry_run": dry_run,
        }
        (run_dir / "suite-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (self.latest_dir / "suite-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if failure_summary:
            (run_dir / "failure-summary.json").write_text(json.dumps(failure_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (self.latest_dir / "failure-summary.json").write_text(json.dumps(failure_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (self.latest_dir / "last_failed_suite.json").write_text(json.dumps(failure_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (self.latest_dir / "repro-command.txt").write_text(failure_summary["command"] + "\n", encoding="utf-8")
        else:
            ok_summary = {"run_id": run_id, "status": result["status"], "suites": suites}
            (run_dir / "failure-summary.json").write_text(json.dumps(ok_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (self.latest_dir / "failure-summary.json").write_text(json.dumps(ok_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report = {
            "run_id": run_id,
            "status": result["status"],
            "suite_count": len(result["suites"]),
            "failed_suites": [suite["suite"] for suite in result["suites"] if suite["status"] != "ok"],
        }
        (run_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return result

    def debug_test(self, test_name: str, run: bool = False) -> dict[str, Any]:
        matches: list[BucketPlan] = []
        for suite in self.suite_names():
            config = self.matrix["suites"][suite]
            for bucket in config.get("buckets", []):
                if bucket["kind"] not in {"pytest_list", "pytest_glob"}:
                    continue
                plan = self._build_bucket_plan(suite, bucket)
                if any(Path(test).name == test_name or test_name in test for test in plan.tests):
                    matches.append(plan)

        if not matches:
            raise ValueError(f"No test matched: {test_name}")

        plan = matches[0]
        matching_tests = [test for test in plan.tests if Path(test).name == test_name or test_name in test]
        quoted = " ".join(shlex.quote(test) for test in matching_tests)
        command = f"cd {shlex.quote(str(plan.cwd.relative_to(self.repo_root)))} && uv run pytest {quoted} -v"
        payload = {
            "suite": plan.suite,
            "bucket": plan.bucket_id,
            "tests": matching_tests,
            "command": command,
            "debug_command": plan.debug_command or command,
        }
        if run:
            proc = subprocess.run(command, shell=True, cwd=self.repo_root, capture_output=True, text=True)
            payload["exit_code"] = proc.returncode
            payload["stdout"] = proc.stdout
            payload["stderr"] = proc.stderr
        return payload

    def report(self) -> dict[str, Any]:
        events: list[dict[str, Any]] = []
        if self.events_path.exists():
            for line in self.events_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    events.append(json.loads(line))
        suite_completed = [e for e in events if e["event_type"] == "suite_completed"]
        suite_failed = [e for e in events if e["event_type"] == "suite_failed"]
        return {
            "generated_at": self._ts(),
            "event_count": len(events),
            "suite_completed": len(suite_completed),
            "suite_failed": len(suite_failed),
            "doctor_completed": len([e for e in events if e["event_type"] == "doctor_completed"]),
            "benchmark_refreshed": len([e for e in events if e["event_type"] == "benchmark_refreshed"]),
            "governance_validation_failed": len([e for e in events if e["event_type"] == "governance_validation_failed"]),
            "quarantine_enter": len([e for e in events if e["event_type"] == "quarantine_enter"]),
            "latest_failure_summary_path": str((self.latest_dir / "failure-summary.json").relative_to(self.repo_root)),
            "latest_manifest_path": str((self.latest_dir / "suite-manifest.json").relative_to(self.repo_root)),
        }


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _print_human(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Config-driven test/debug/reliability orchestrator")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="Print deterministic suite or profile plan")
    p_plan.add_argument("--suite", action="append", default=[])
    p_plan.add_argument("--profile", default=None)
    p_plan.add_argument("--json", action="store_true")

    p_inventory = sub.add_parser("inventory", help="Generate inventory of tests, validators, doctors, benchmarks")
    p_inventory.add_argument("--json", action="store_true")

    p_run = sub.add_parser("run", help="Run suite(s) or profile")
    p_run.add_argument("--suite", action="append", default=[])
    p_run.add_argument("--profile", default=None)
    p_run.add_argument("--dry-run", action="store_true")
    p_run.add_argument("--continue-on-fail", action="store_true")
    p_run.add_argument("--json", action="store_true")

    p_debug = sub.add_parser("debug-test", help="Resolve deterministic repro command for a test node")
    p_debug.add_argument("--test", required=True)
    p_debug.add_argument("--run", action="store_true")
    p_debug.add_argument("--json", action="store_true")

    p_report = sub.add_parser("report", help="Show latest reliability event summary")
    p_report.add_argument("--json", action="store_true")

    args = parser.parse_args()
    orch = ReliabilityOrchestrator()

    if args.cmd == "plan":
        suites = orch.resolve_suites(args.suite or None, args.profile)
        payload = {"suites": [orch.suite_plan(suite) for suite in suites]}
    elif args.cmd == "inventory":
        payload = orch.write_inventory()
    elif args.cmd == "run":
        suites = orch.resolve_suites(args.suite or None, args.profile)
        payload = orch.run(
            suites,
            dry_run=bool(args.dry_run),
            continue_on_fail=bool(args.continue_on_fail),
            machine_readable=bool(args.json),
        )
    elif args.cmd == "debug-test":
        payload = orch.debug_test(args.test, run=bool(args.run))
    elif args.cmd == "report":
        payload = orch.report()
    else:  # pragma: no cover
        raise AssertionError("unreachable")

    if getattr(args, "json", False):
        _print_json(payload)
    else:
        _print_human(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
