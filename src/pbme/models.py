from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class Sensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class Decision(str, Enum):
    ALLOW = "allow"
    TRANSFORM = "transform"
    REROUTE = "reroute"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass(frozen=True)
class FieldPolicy:
    name: str
    description: str
    sensitivity: Sensitivity
    allowed_purposes: frozenset[str]
    pii: bool = False
    direct_identifier: bool = False


@dataclass(frozen=True)
class TaskContext:
    task_id: str
    user_goal: str
    approved_purpose: str
    actor_id: str
    issued_at: int
    expires_at: int
    audience: str = "pbme"
    destination: str = "internal"
    task_parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CapabilitySpec:
    name: str
    description: str
    trigger_terms: frozenset[str]
    required_raw_fields: tuple[str, ...]
    safe_output_fields: tuple[str, ...]
    required_parameters: tuple[str, ...] = ()
    supports_year: bool = False
    supports_department: bool = False


@dataclass
class ToolSpec:
    name: str
    description: str
    accepted_arguments: frozenset[str]
    output_fields: tuple[str, ...]
    capabilities: frozenset[str]
    raw_record_tool: bool
    supports_projection: bool = False
    field_argument: str | None = None
    executor: Callable[..., Any] | None = None
    source: str = "local"


@dataclass(frozen=True)
class ProposedToolCall:
    tool_name: str
    arguments: dict[str, Any]


@dataclass
class NecessityPlan:
    capability: str
    required_fields: list[str]
    safe_output_fields: list[str]
    parameters: dict[str, Any]
    reasons: dict[str, str]
    confidence: float
    planner: str


@dataclass
class VerifiedPlan:
    plan: NecessityPlan
    verified: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class CandidateTool:
    tool: ToolSpec
    call_arguments: dict[str, Any]
    released_fields: list[str]
    exposure_score: float
    policy_allowed: bool
    policy_errors: list[str] = field(default_factory=list)


@dataclass
class EnforcementRecord:
    decision: Decision
    context: TaskContext
    proposed_call: ProposedToolCall
    selected_tool: str | None
    executed_arguments: dict[str, Any]
    released_fields: list[str]
    removed_fields: list[str]
    exposure_before: float
    exposure_after: float
    rationale: list[str]
    planner: str


@dataclass
class BrokerResult:
    data: Any
    enforcement: EnforcementRecord
