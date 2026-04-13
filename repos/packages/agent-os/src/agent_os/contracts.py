from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ModelRouteInput:
    task_type: str
    complexity: str
    token_budget: int
    cost_budget: float
    preferred_models: list[str] = field(default_factory=list)
    version: str = "2.0"


@dataclass
class ModelRouteOutput:
    task_type: str
    complexity: str
    model_tier: str
    primary_model: str
    fallback_chain: list[str]
    max_input_tokens: int
    max_output_tokens: int
    route_reason: str
    provider_topology: str
    routing_source: str = "legacy"
    orchestration_path: str | None = None
    telemetry: dict[str, Any] = field(default_factory=dict)
    runtime_provider: str | None = None
    runtime_profile: str | None = None
    channel: str | None = None
    persona_id: str | None = None
    memory_policy: str | None = None
    runtime_reason: str | None = None
    runtime_fallback_chain: list[str] = field(default_factory=list)
    autonomy_mode: str | None = None
    approval_policy: str | None = None
    background_profile: str | None = None
    scheduler_profile: str | None = None
    persona_version: str | None = None
    operator_visibility: str | None = None
    cost_budget_usd: float | None = None
    max_actions: int | None = None
    stop_token: str | None = None
    proof_required: bool | None = None
    source_tier: str | None = None
    requests_capability_promotion: bool | None = None
    source_tier_policy: dict[str, Any] = field(default_factory=dict)
    version: str = "2.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentInput:
    run_id: str
    objective: str
    plan_steps: list[str]
    route_decision: dict[str, Any]


@dataclass
class AgentOutput:
    status: str
    diff_summary: str
    test_report: dict[str, Any]
    artifacts: list[str]
    next_action: str
    response_text: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolInput:
    tool_name: str
    args: list[str]
    mode: str
    correlation_id: str


@dataclass
class ToolOutput:
    status: str
    stdout: str
    stderr: str
    artifacts: list[str]
    exit_code: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RetrieverInput:
    query: str
    sources: list[str]
    max_chunks: int
    freshness: str
    correlation_id: str | None = None


@dataclass
class RetrieverOutput:
    chunks: list[dict[str, Any]]
    citations: list[str]
    retrieval_ms: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryStoreInput:
    op: str
    key: str
    payload: dict[str, Any]
    correlation_id: str | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryStoreOutput:
    result: dict[str, Any]
    memory_ids: list[str]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CodeEditorInput:
    repo_path: str
    target_files: list[str]
    edit_intent: str
    verify_commands: list[str]


@dataclass
class CodeEditorOutput:
    patch: str
    files_changed: list[str]
    verification: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
