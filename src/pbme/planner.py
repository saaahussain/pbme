from __future__ import annotations

import re
from collections.abc import Mapping

from .models import CapabilitySpec, NecessityPlan, TaskContext
from .ontology import CAPABILITIES


WORD_RE = re.compile(r"[a-z0-9_]+")
YEAR_RE = re.compile(r"\b(20\d{2})\b")


class PlanningError(ValueError):
    pass


class DeterministicInformationPlanner:
    """Maps natural-language goals to a verified capability.

    The capability registry is configurable so the same planner/verifier/broker
    pipeline can be exercised across multiple benchmark domains. The default
    remains the built-in HR ontology for backwards compatibility.
    """

    name = "deterministic"

    def __init__(
        self,
        capabilities: Mapping[str, CapabilitySpec] | None = None,
    ):
        self.capabilities = dict(capabilities or CAPABILITIES)

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(WORD_RE.findall(text.lower()))

    def plan(self, context: TaskContext) -> NecessityPlan:
        tokens = self._tokens(context.user_goal)

        scored: list[tuple[int, str]] = []
        for name, capability in self.capabilities.items():
            overlap = len(tokens.intersection(capability.trigger_terms))
            if overlap:
                scored.append((overlap, name))

        if not scored:
            raise PlanningError("No verified capability matches the user goal")

        scored.sort(reverse=True)
        top_score, top_name = scored[0]

        ties = [name for score, name in scored if score == top_score]
        if len(ties) > 1:
            raise PlanningError(
                "Ambiguous task capability: " + ", ".join(sorted(ties))
            )

        cap = self.capabilities[top_name]
        parameters: dict[str, object] = dict(context.task_parameters)

        # Backwards-compatible extraction for human text that contains a year
        # but whose trusted host did not separately bind the parameter.
        if cap.supports_year and "year" not in parameters:
            year_match = YEAR_RE.search(context.user_goal)
            if year_match:
                parameters["year"] = int(year_match.group(1))

        reasons = {
            field: f"Verified capability '{cap.name}' requires '{field}'"
            for field in cap.required_raw_fields
        }

        confidence = min(0.99, 0.65 + 0.08 * top_score)
        return NecessityPlan(
            capability=cap.name,
            required_fields=list(cap.required_raw_fields),
            safe_output_fields=list(cap.safe_output_fields),
            parameters=parameters,
            reasons=reasons,
            confidence=confidence,
            planner=self.name,
        )
