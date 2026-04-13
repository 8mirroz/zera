from __future__ import annotations


class AgentOSError(RuntimeError):
    """Base error for Agent OS integration modules."""


class RouteNotFoundError(AgentOSError):
    code = "ROUTE_NOT_FOUND"


class BudgetExceededError(AgentOSError):
    code = "BUDGET_EXCEEDED"


class ModelRouterError(AgentOSError):
    """Base error for routing operations."""


class ProviderUnavailableError(AgentOSError):
    code = "PROVIDER_UNAVAILABLE"


class ToolExecutionError(AgentOSError):
    code = "NON_ZERO_EXIT"


class ToolTimeoutError(AgentOSError):
    code = "TIMEOUT"


class ToolNotFoundError(AgentOSError):
    code = "TOOL_NOT_FOUND"


class PermissionDeniedError(AgentOSError):
    code = "PERMISSION_DENIED"


class RuntimeProviderUnavailableError(AgentOSError):
    code = "RUNTIME_PROVIDER_UNAVAILABLE"


class RuntimeProviderExecutionError(AgentOSError):
    code = "RUNTIME_PROVIDER_EXECUTION_FAILED"
