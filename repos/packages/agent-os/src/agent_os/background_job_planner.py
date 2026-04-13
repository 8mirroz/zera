from __future__ import annotations

from typing import Any


def should_schedule_harness_gardening(background_profile: str | None, route: dict[str, Any]) -> bool:
    if background_profile != "worker-maintenance":
        return False
    task_type = str(route.get("task_type") or "").strip().upper()
    complexity = str(route.get("complexity") or "").strip().upper()
    return task_type in {"T4", "T5"} or complexity in {"C4", "C5"}


def select_background_jobs(background_profile: str | None, mode: str, route: dict[str, Any]) -> list[str]:
    if background_profile == "zera-companion":
        jobs = ["goal_review", "memory_consolidation", "self_reflection"]
        if mode in {"love", "plan"}:
            jobs.append("rhythm_check_in")
        return jobs
    if background_profile == "worker-maintenance":
        jobs = ["memory_consolidation", "pending_task_follow_up"]
        if should_schedule_harness_gardening(background_profile, route):
            jobs.append("harness_gardening")
        return jobs
    return []


def build_background_objective(job_type: str, *, route_decision: dict[str, Any], selected_mode: str) -> str:
    persona_id = str(route_decision.get("persona_id") or "agent")
    if job_type == "goal_review":
        return f"Run a concise goal review for {persona_id} in {selected_mode} mode and produce one practical next action."
    if job_type == "memory_consolidation":
        return f"Consolidate recent memory for {persona_id} without writing speculative facts."
    if job_type == "self_reflection":
        return f"Write an operational self-reflection for {persona_id} focused on actionability and boundaries."
    if job_type == "rhythm_check_in":
        return f"Prepare a low-pressure rhythm check-in for {persona_id} with one optional follow-up."
    if job_type == "pending_task_follow_up":
        return f"Follow up on pending tasks for {persona_id} and surface the highest-value next step."
    if job_type == "harness_gardening":
        return f"Run a read-only harness gardening sweep for {persona_id} and refresh benchmark/harness evidence."
    return f"Execute bounded background job '{job_type}' for {persona_id}."
