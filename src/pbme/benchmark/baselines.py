from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pbme.models import Sensitivity

from .domains import DomainSpec, DomainRuntime
from .models import BenchmarkScenario


@dataclass
class SystemOutput:
    decision: str
    selected_tool: str | None
    data: Any
    released_fields: list[str]
    requested_fields: list[str]
    tool_minimized: bool
    error: str | None = None


def _requested_fields(spec: DomainSpec, scenario: BenchmarkScenario) -> list[str]:
    if scenario.proposed_tool == spec.raw_tool:
        return list(
            scenario.proposed_arguments.get("fields", spec.all_fields)
        )
    cap = spec.capabilities[scenario.capability]
    return list(cap.safe_output_fields)


def _output_fields(data: Any) -> list[str]:
    if isinstance(data, list):
        keys = set()
        for item in data:
            if isinstance(item, dict):
                keys.update(item)
        return sorted(keys)
    if isinstance(data, dict):
        return sorted(data)
    return []


def _filter_data(data: Any, allowed: set[str]):
    if isinstance(data, list):
        return [_filter_data(x, allowed) for x in data]
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k in allowed}
    return data


def _purpose_allows(spec: DomainSpec, fields: list[str], purpose: str) -> bool:
    for field in fields:
        policy = spec.field_policies.get(field)
        if policy is None or purpose not in policy.allowed_purposes:
            return False
    return True


class BenchmarkSystem:
    name = "base"

    def run(
        self,
        spec: DomainSpec,
        runtime: DomainRuntime,
        scenario: BenchmarkScenario,
    ) -> SystemOutput:
        raise NotImplementedError


class PermissiveSystem(BenchmarkSystem):
    name = "permissive"

    def run(self, spec, runtime, scenario):
        requested = _requested_fields(spec, scenario)
        try:
            data = runtime.execute(
                scenario.proposed_tool,
                dict(scenario.proposed_arguments),
            )
            return SystemOutput(
                "allow", scenario.proposed_tool, data,
                _output_fields(data), requested, False
            )
        except Exception as exc:
            return SystemOutput(
                "error", scenario.proposed_tool, None, [],
                requested, False, str(exc)
            )


class RBACOnlySystem(BenchmarkSystem):
    name = "rbac_only"

    # Deliberately coarse: role grants tool access, not field-level necessity.
    DOMAIN_PURPOSES = {
        "hr": {"hr_operations", "workforce_analytics", "payroll", "compensation_analysis"},
        "support": {"customer_support", "sales_analytics", "fraud_review"},
        "finance": {"expense_analytics", "audit"},
        "documents": {"document_search", "legal_review"},
    }

    def run(self, spec, runtime, scenario):
        requested = _requested_fields(spec, scenario)
        if scenario.purpose not in self.DOMAIN_PURPOSES[spec.name]:
            return SystemOutput("deny", None, None, [], requested, False)
        try:
            data = runtime.execute(
                scenario.proposed_tool,
                dict(scenario.proposed_arguments),
            )
            return SystemOutput(
                "allow", scenario.proposed_tool, data,
                _output_fields(data), requested, False
            )
        except Exception as exc:
            return SystemOutput(
                "error", scenario.proposed_tool, None, [],
                requested, False, str(exc)
            )


class StaticMaskingSystem(BenchmarkSystem):
    name = "static_masking"

    def run(self, spec, runtime, scenario):
        requested = _requested_fields(spec, scenario)
        try:
            raw = runtime.execute(
                scenario.proposed_tool,
                dict(scenario.proposed_arguments),
            )
            # Remove restricted and direct-identifier fields after retrieval.
            allowed = {
                f for f in _output_fields(raw)
                if (
                    spec.field_policies[f].sensitivity != Sensitivity.RESTRICTED
                    and not spec.field_policies[f].direct_identifier
                )
            }
            data = _filter_data(raw, allowed)
            return SystemOutput(
                "transform", scenario.proposed_tool, data,
                _output_fields(data), requested, False
            )
        except Exception as exc:
            return SystemOutput(
                "error", scenario.proposed_tool, None, [],
                requested, False, str(exc)
            )


class ARESLikeSystem(BenchmarkSystem):
    name = "ares_like"

    def run(self, spec, runtime, scenario):
        requested = _requested_fields(spec, scenario)

        # Action-level guard: if requested resource scope violates purpose,
        # block the whole action. It does not rewrite to a minimum subset.
        if not _purpose_allows(spec, requested, scenario.purpose):
            return SystemOutput(
                "deny", None, None, [], requested, False
            )

        try:
            data = runtime.execute(
                scenario.proposed_tool,
                dict(scenario.proposed_arguments),
            )
            return SystemOutput(
                "allow", scenario.proposed_tool, data,
                _output_fields(data), requested, False
            )
        except Exception as exc:
            return SystemOutput(
                "error", scenario.proposed_tool, None, [],
                requested, False, str(exc)
            )


class PBMEFieldSystem(BenchmarkSystem):
    name = "pbme_field"

    def run(self, spec, runtime, scenario):
        requested = _requested_fields(spec, scenario)
        cap = spec.capabilities[scenario.capability]

        if not _purpose_allows(spec, list(cap.required_fields), scenario.purpose):
            return SystemOutput("deny", None, None, [], requested, False)

        try:
            if scenario.proposed_tool == spec.raw_tool:
                args = dict(scenario.parameters)
                args["fields"] = list(cap.required_fields)
                data = runtime.execute(spec.raw_tool, args)
                decision = (
                    "allow"
                    if args == scenario.proposed_arguments
                    else "transform"
                )
                return SystemOutput(
                    decision, spec.raw_tool, data,
                    _output_fields(data), requested, False
                )

            data = runtime.execute(
                scenario.proposed_tool,
                dict(scenario.proposed_arguments),
            )
            return SystemOutput(
                "allow", scenario.proposed_tool, data,
                _output_fields(data), requested, False
            )
        except Exception as exc:
            return SystemOutput(
                "error", scenario.proposed_tool, None, [],
                requested, False, str(exc)
            )


class PBMEFullSystem(BenchmarkSystem):
    name = "pbme_full"

    def run(self, spec, runtime, scenario):
        requested = _requested_fields(spec, scenario)
        cap = spec.capabilities[scenario.capability]

        if not _purpose_allows(spec, list(cap.safe_output_fields), scenario.purpose):
            # If the safe output itself is not authorized, deny.
            return SystemOutput("deny", None, None, [], requested, False)

        try:
            selected = cap.preferred_tool
            data = runtime.execute(selected, dict(scenario.parameters))
            released = _output_fields(data)
            return SystemOutput(
                "reroute" if selected != scenario.proposed_tool else "allow",
                selected,
                data,
                released,
                requested,
                selected != scenario.proposed_tool,
            )
        except Exception as exc:
            return SystemOutput(
                "error", cap.preferred_tool, None, [],
                requested, False, str(exc)
            )


SYSTEMS = {
    cls.name: cls()
    for cls in (
        PermissiveSystem,
        RBACOnlySystem,
        StaticMaskingSystem,
        ARESLikeSystem,
        PBMEFieldSystem,
        PBMEFullSystem,
    )
}
