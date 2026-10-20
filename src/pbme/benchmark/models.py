from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class BenchmarkScenario:
    scenario_id: str
    base_task_id: str
    domain: str
    capability: str
    goal: str
    purpose: str
    variant: str
    proposed_tool: str
    proposed_arguments: dict[str, Any]
    required_fields: list[str]
    safe_output_fields: list[str]
    optional_fields: list[str]
    forbidden_fields: list[str]
    preferred_tool: str
    allowed_tools: list[str]
    parameters: dict[str, Any]
    expected_answer: Any
    expected_outcome: str = "allow"
    attack_instruction: str | None = None
    difficulty: str = "standard"
    e3_modes: list[str] | None = None
    tool_profile: str = "standard"
    split: str = "legacy"
    # Names of task-bound tool arguments whose values are authorized by the
    # trusted task context. This makes selector IDs (customer_id, invoice_id,
    # document_id, etc.) explicit without treating identifiers as globally
    # unnecessary output data. Older benchmark files may omit this field; in
    # that case callers should fall back to parameters.keys().
    required_arguments: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunResult:
    scenario_id: str
    base_task_id: str
    domain: str
    capability: str
    variant: str
    system: str
    repeat: int
    decision: str
    selected_tool: str | None
    task_success: bool
    policy_success: bool
    denied: bool
    false_denial: bool
    attack_success: bool
    requested_fields: list[str]
    released_fields: list[str]
    unnecessary_released_fields: list[str]
    forbidden_released_fields: list[str]
    exposure_cost: float
    data_minimization_ratio: float
    unnecessary_data_access_rate: float
    tool_minimized: bool
    latency_ms: float
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
