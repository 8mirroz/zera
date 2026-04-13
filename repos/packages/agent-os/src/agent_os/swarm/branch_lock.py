from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BranchLockRequest:
    lane_id: str
    branch: str
    scope: str


@dataclass(frozen=True)
class BranchLockCollision:
    lane_ids: tuple[str, str]
    branch: str
    scopes: tuple[str, str]
    reason: str


def _normalize_scope(scope: str) -> str:
    return "/".join(part for part in str(scope).strip("/").split("/") if part)


def _is_nested_scope(left: str, right: str) -> bool:
    return left == right or left.startswith(f"{right}/") or right.startswith(f"{left}/")


def detect_branch_lock_collisions(requests: list[BranchLockRequest]) -> list[BranchLockCollision]:
    collisions: list[BranchLockCollision] = []
    for idx, left in enumerate(requests):
        for right in requests[idx + 1 :]:
            if left.branch != right.branch:
                continue
            left_scope = _normalize_scope(left.scope)
            right_scope = _normalize_scope(right.scope)
            if _is_nested_scope(left_scope, right_scope):
                collisions.append(
                    BranchLockCollision(
                        lane_ids=(left.lane_id, right.lane_id),
                        branch=left.branch,
                        scopes=(left_scope, right_scope),
                        reason="nested_scope_same_branch",
                    )
                )
    return collisions
