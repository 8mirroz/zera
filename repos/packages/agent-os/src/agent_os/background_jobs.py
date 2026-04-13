from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .yaml_compat import parse_simple_yaml


@dataclass
class BackgroundJobSpec:
    job_type: str
    cadence_minutes: int
    daily_cap: int
    retry_limit: int
    concurrency_limit: int
    quiet_hours: str
    stop_condition: str
    escalation_rule: str
    user_suppressible: bool
    staleness_minutes: int
    budget_profile: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_type": self.job_type,
            "cadence_minutes": self.cadence_minutes,
            "daily_cap": self.daily_cap,
            "retry_limit": self.retry_limit,
            "concurrency_limit": self.concurrency_limit,
            "quiet_hours": self.quiet_hours,
            "stop_condition": self.stop_condition,
            "escalation_rule": self.escalation_rule,
            "user_suppressible": self.user_suppressible,
            "staleness_minutes": self.staleness_minutes,
            "budget_profile": self.budget_profile,
        }


class BackgroundJobRegistry:
    """Config-backed registry for governed background jobs and scheduler profiles."""

    def __init__(self, repo_root: Path, config_path: Path | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.config_path = config_path or (self.repo_root / "configs/tooling/background_jobs.yaml")
        self.config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {"jobs": {}, "scheduler_profiles": {}}
        return parse_simple_yaml(self.config_path.read_text(encoding="utf-8"))

    def get_scheduler_profile(self, name: str | None) -> dict[str, Any]:
        profiles = self.config.get("scheduler_profiles", {})
        if not isinstance(profiles, dict):
            return {}
        profile = profiles.get(str(name or "").strip(), {})
        return dict(profile) if isinstance(profile, dict) else {}

    def get_job(self, job_type: str) -> BackgroundJobSpec | None:
        jobs = self.config.get("jobs", {})
        if not isinstance(jobs, dict):
            return None
        key = str(job_type or "").strip()
        if key not in jobs:
            return None
        row = jobs.get(key, {})
        if not isinstance(row, dict):
            return None
        return BackgroundJobSpec(
            job_type=key,
            cadence_minutes=int(row.get("cadence_minutes", 1440)),
            daily_cap=int(row.get("daily_cap", 1)),
            retry_limit=int(row.get("retry_limit", 1)),
            concurrency_limit=int(row.get("concurrency_limit", 1)),
            quiet_hours=str(row.get("quiet_hours") or "22:00-08:00"),
            stop_condition=str(row.get("stop_condition") or "manual_stop"),
            escalation_rule=str(row.get("escalation_rule") or "notify_operator"),
            user_suppressible=bool(row.get("user_suppressible", True)),
            staleness_minutes=int(row.get("staleness_minutes", 1440)),
            budget_profile=str(row.get("budget_profile") or "").strip() or None,
        )

    def materialize(self, job_types: list[str], *, scheduler_profile: str | None = None) -> list[dict[str, Any]]:
        profile = self.get_scheduler_profile(scheduler_profile)
        out: list[dict[str, Any]] = []
        for job_type in job_types:
            spec = self.get_job(job_type)
            if spec is None:
                continue
            row = spec.to_dict()
            row["scheduler_profile"] = scheduler_profile
            row["scheduler_policy"] = profile
            out.append(row)
        return out

    @staticmethod
    def in_quiet_hours(quiet_hours: str | None, *, now: datetime | None = None) -> bool:
        parsed = BackgroundJobRegistry._parse_quiet_hours(quiet_hours)
        if parsed is None:
            return False
        start_minutes, end_minutes = parsed
        current = now or datetime.now(tz=timezone.utc)
        minute_of_day = (current.hour * 60) + current.minute
        if start_minutes <= end_minutes:
            return start_minutes <= minute_of_day < end_minutes
        return minute_of_day >= start_minutes or minute_of_day < end_minutes

    @staticmethod
    def next_allowed_time(quiet_hours: str | None, *, now: datetime | None = None) -> datetime:
        current = now or datetime.now(tz=timezone.utc)
        parsed = BackgroundJobRegistry._parse_quiet_hours(quiet_hours)
        if parsed is None:
            return current
        start_minutes, end_minutes = parsed
        base = current.replace(second=0, microsecond=0)
        if not BackgroundJobRegistry.in_quiet_hours(quiet_hours, now=current):
            return base

        end_hour = end_minutes // 60
        end_minute = end_minutes % 60
        candidate = base.replace(hour=end_hour, minute=end_minute)
        if start_minutes > end_minutes and ((current.hour * 60) + current.minute) >= start_minutes:
            candidate = candidate + timedelta(days=1)
        if candidate <= current:
            candidate = candidate + timedelta(days=1)
        return candidate

    @staticmethod
    def _parse_quiet_hours(quiet_hours: str | None) -> tuple[int, int] | None:
        raw = str(quiet_hours or "").strip()
        if not raw or "-" not in raw:
            return None
        try:
            start_raw, end_raw = raw.split("-", 1)
            start_h, start_m = [int(part) for part in start_raw.split(":", 1)]
            end_h, end_m = [int(part) for part in end_raw.split(":", 1)]
        except Exception:
            return None
        return (start_h * 60) + start_m, (end_h * 60) + end_m
