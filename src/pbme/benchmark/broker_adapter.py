from __future__ import annotations

import re
import string
from collections.abc import Mapping
from typing import Any

from pbme.audit import JsonlAuditLog
from pbme.broker import PBMEBroker
from pbme.catalog import GovernanceCatalog
from pbme.context import TaskContextSigner
from pbme.models import (
    CapabilitySpec,
    NecessityPlan,
    TaskContext,
    ToolSpec,
)
from pbme.planner import PlanningError
from pbme.registry import ToolRegistry

from .domains import DomainRuntime, DomainSpec


WORD_RE = re.compile(r"[a-z0-9_]+")
STOPWORDS = {
    "a", "an", "and", "are", "by", "for", "had", "how", "in", "is",
    "list", "many", "of", "show", "the", "there", "to", "was", "what",
    "which", "with",
}


def _tokens(text: str) -> set[str]:
    return {
        token for token in WORD_RE.findall(text.lower())
        if token not in STOPWORDS and not token.isdigit()
    }


def _placeholders(template: str) -> set[str]:
    return {
        name
        for _, name, _, _ in string.Formatter().parse(template)
        if name
    }


def capability_specs_for_domain(
    spec: DomainSpec,
) -> dict[str, CapabilitySpec]:
    result: dict[str, CapabilitySpec] = {}
    for name, cap in spec.capabilities.items():
        trigger_terms = set(_tokens(name.replace("_", " ")))
        required_parameters: set[str] = set()
        for template in cap.goal_templates:
            trigger_terms.update(_tokens(template))
            required_parameters.update(_placeholders(template))
        result[name] = CapabilitySpec(
            name=name,
            description=" / ".join(cap.goal_templates),
            trigger_terms=frozenset(trigger_terms),
            required_raw_fields=tuple(cap.required_fields),
            safe_output_fields=tuple(cap.safe_output_fields),
            required_parameters=tuple(sorted(required_parameters)),
            supports_year="year" in required_parameters,
            supports_department="department" in {
                key for params in cap.parameter_sets for key in params
            },
        )
    return result


class BenchmarkInformationPlanner:
    """Deterministic planner used by the *real broker* validation.

    It sees only the signed task context. It does not receive the benchmark's
    ground-truth capability label. Exact generated-goal matching is attempted
    first, followed by conservative trigger-term matching.
    """

    name = "benchmark-deterministic"

    def __init__(
        self,
        domain: DomainSpec,
        capabilities: Mapping[str, CapabilitySpec],
    ):
        self.domain = domain
        self.capabilities = dict(capabilities)

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(WORD_RE.findall(text.lower()))

    @staticmethod
    def _render(template: str, parameters: dict[str, Any]) -> str | None:
        try:
            return template.format(**parameters)
        except KeyError:
            return None

    def _exact_match(self, context: TaskContext) -> str | None:
        normalized_goal = self._normalize(context.user_goal)
        matches: list[str] = []
        for name, cap in self.domain.capabilities.items():
            for template in cap.goal_templates:
                rendered = self._render(template, context.task_parameters)
                if rendered and self._normalize(rendered) == normalized_goal:
                    matches.append(name)
                    break
        matches = sorted(set(matches))
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise PlanningError(
                "Ambiguous exact benchmark capability: "
                + ", ".join(matches)
            )
        return None

    def _semantic_match(self, context: TaskContext) -> str:
        tokens = _tokens(context.user_goal)
        scored: list[tuple[int, str]] = []
        for name, cap in self.capabilities.items():
            score = len(tokens.intersection(cap.trigger_terms))
            if score:
                scored.append((score, name))
        if not scored:
            raise PlanningError("No benchmark capability matches the user goal")
        scored.sort(reverse=True)
        top_score = scored[0][0]
        ties = sorted(name for score, name in scored if score == top_score)
        if len(ties) != 1:
            raise PlanningError(
                "Ambiguous benchmark capability: " + ", ".join(ties)
            )
        return ties[0]

    def plan(self, context: TaskContext) -> NecessityPlan:
        name = self._exact_match(context) or self._semantic_match(context)
        cap = self.capabilities[name]
        reasons = {
            field: f"Verified benchmark capability '{name}' requires '{field}'"
            for field in cap.required_raw_fields
        }
        return NecessityPlan(
            capability=name,
            required_fields=list(cap.required_raw_fields),
            safe_output_fields=list(cap.safe_output_fields),
            parameters=dict(context.task_parameters),
            reasons=reasons,
            confidence=0.99,
            planner=self.name,
        )


def _parameter_names(spec: DomainSpec, capability_name: str) -> set[str]:
    cap = spec.capabilities[capability_name]
    return {key for params in cap.parameter_sets for key in params}


def _inject_field(data: Any, field: str | None) -> Any:
    if not field:
        return data
    if isinstance(data, list):
        return [_inject_field(item, field) for item in data]
    if isinstance(data, dict):
        result = dict(data)
        result[field] = "__PBME_INTENTIONAL_OVER_RETURN__"
        return result
    return data


def build_benchmark_broker(
    spec: DomainSpec,
    *,
    secret: str,
    mode: str = "full_registry",
    injected_over_return_field: str | None = None,
) -> tuple[PBMEBroker, TaskContextSigner, DomainRuntime]:
    if mode not in {"full_registry", "raw_only"}:
        raise ValueError(f"Unknown broker validation mode: {mode}")

    runtime = DomainRuntime(spec)
    catalog = GovernanceCatalog(spec.field_policies)
    registry = ToolRegistry()
    capabilities = capability_specs_for_domain(spec)

    all_parameter_names = {
        key
        for capability_name in spec.capabilities
        for key in _parameter_names(spec, capability_name)
    }

    def raw_executor(**kwargs):
        data = runtime.execute(spec.raw_tool, dict(kwargs))
        return _inject_field(data, injected_over_return_field)

    registry.register(
        ToolSpec(
            name=spec.raw_tool,
            description=f"Raw projected records for benchmark domain {spec.name}",
            accepted_arguments=frozenset({"fields", *all_parameter_names}),
            output_fields=tuple(spec.all_fields),
            capabilities=frozenset(spec.capabilities),
            raw_record_tool=True,
            supports_projection=True,
            field_argument="fields",
            executor=raw_executor,
            source="benchmark-real-broker",
        )
    )

    if mode == "full_registry":
        for capability_name, cap in spec.capabilities.items():
            accepted = frozenset(_parameter_names(spec, capability_name))
            tool_name = cap.preferred_tool

            def make_executor(name: str):
                def executor(**kwargs):
                    data = runtime.execute(name, dict(kwargs))
                    return _inject_field(data, injected_over_return_field)
                return executor

            registry.register(
                ToolSpec(
                    name=tool_name,
                    description=(
                        f"Minimum-exposure benchmark tool for {capability_name}"
                    ),
                    accepted_arguments=accepted,
                    output_fields=tuple(cap.safe_output_fields),
                    capabilities=frozenset({capability_name}),
                    raw_record_tool=False,
                    executor=make_executor(tool_name),
                    source="benchmark-real-broker",
                )
            )

    signer = TaskContextSigner(secret)
    planner = BenchmarkInformationPlanner(spec, capabilities)
    audit = JsonlAuditLog()
    broker = PBMEBroker(
        signer=signer,
        catalog=catalog,
        registry=registry,
        planner=planner,
        audit=audit,
        capabilities=capabilities,
    )
    return broker, signer, runtime
