from __future__ import annotations

from typing import Any

from .background_job_planner import build_background_objective
from .background_jobs import BackgroundJobRegistry
from .background_scheduler import BackgroundJobQueue
from .observability import emit_event


def enqueue_background_jobs_from_output(
    *,
    repo_root,
    run_id: str,
    runtime_provider: str,
    runtime_profile: str | None,
    route_decision: dict[str, Any],
    output_meta: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    meta = output_meta if isinstance(output_meta, dict) else {}
    job_types = meta.get("background_jobs", [])
    if not isinstance(job_types, list) or bool(route_decision.get("suppress_background_jobs")):
        return []

    selected_mode = str(meta.get("selected_mode") or route_decision.get("mode") or "plan")
    scheduler_profile = str(route_decision.get("scheduler_profile") or "")
    registry = BackgroundJobRegistry(repo_root)
    queue = BackgroundJobQueue(repo_root)
    scheduled: list[dict[str, Any]] = []

    for job in registry.materialize([str(item) for item in job_types], scheduler_profile=scheduler_profile or None):
        objective = build_background_objective(job["job_type"], route_decision=route_decision, selected_mode=selected_mode)
        queue_item, enqueued = queue.enqueue(
            job_type=job["job_type"],
            objective=objective,
            runtime_provider=runtime_provider,
            runtime_profile=str(runtime_profile or ""),
            persona_id=str(route_decision.get("persona_id") or ""),
            scheduler_profile=scheduler_profile or None,
            idempotency_key=f"{route_decision.get('persona_id') or 'default'}:{job['job_type']}:{selected_mode}",
            budget_limit={"profile": job.get("budget_profile")},
            stop_token=str(route_decision.get("stop_token") or "") or None,
            quiet_hours_policy=str(job.get("quiet_hours") or "") or None,
            escalation_policy=str(job.get("escalation_rule") or "") or None,
            payload={
                "source_run_id": run_id,
                "job_spec": job,
                "route_decision": {
                    "task_type": route_decision.get("task_type"),
                    "complexity": route_decision.get("complexity"),
                    "approval_policy": route_decision.get("approval_policy"),
                    "autonomy_mode": route_decision.get("autonomy_mode"),
                },
            },
            delay_seconds=0,
            max_attempts=int(job.get("retry_limit", 1)) + 1,
        )
        emit_event(
            "background_job_started",
            {
                "run_id": run_id,
                "component": "agent",
                "status": "ok",
                "message": f"Background job scheduled: {job['job_type']}",
                "runtime_provider": runtime_provider,
                "runtime_profile": runtime_profile,
                "persona_id": route_decision.get("persona_id"),
                "mode": selected_mode,
                "background_job_type": job["job_type"],
                "data": {
                    **job,
                    "objective": objective,
                    "queue_id": queue_item.id,
                    "queue_state": "enqueued" if enqueued else "duplicate_suppressed",
                },
            },
        )
        if enqueued and route_decision.get("proof_required"):
            emit_event(
                "proof_of_action_recorded",
                {
                    "run_id": run_id,
                    "component": "agent",
                    "status": "ok",
                    "message": f"Proof recorded for background job '{job['job_type']}'",
                    "runtime_provider": runtime_provider,
                    "runtime_profile": runtime_profile,
                    "persona_id": route_decision.get("persona_id"),
                    "mode": selected_mode,
                    "data": {
                        "queue_id": queue_item.id,
                        "job_type": job["job_type"],
                        "proof": {
                            "objective": objective,
                            "queued_at": queue_item.queued_at,
                        },
                    },
                },
            )
        emit_event(
            "background_job_completed",
            {
                "run_id": run_id,
                "component": "agent",
                "status": "completed",
                "message": f"Background job accepted into scheduler shadow queue: {job['job_type']}",
                "runtime_provider": runtime_provider,
                "runtime_profile": runtime_profile,
                "persona_id": route_decision.get("persona_id"),
                "mode": selected_mode,
                "background_job_type": job["job_type"],
                "data": {
                    **job,
                    "objective": objective,
                    "queue_id": queue_item.id,
                    "scheduler_state": "enqueued" if enqueued else "duplicate_suppressed",
                },
            },
        )
        scheduled.append(
            {
                "job_type": job["job_type"],
                "objective": objective,
                "queue_id": queue_item.id,
                "enqueued": enqueued,
            }
        )
    return scheduled
