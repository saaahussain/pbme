from __future__ import annotations

from collections.abc import Mapping

from .catalog import GovernanceCatalog
from .models import CapabilitySpec, NecessityPlan, VerifiedPlan
from .ontology import CAPABILITIES
from .registry import ToolRegistry


class PlanVerifier:
    """Deterministically verifies a candidate necessity plan.

    The trusted capability ontology is injectable. This is important for
    validating the *real* broker across multiple domains rather than hard-wiring
    verification to the demonstration HR ontology.
    """

    def __init__(
        self,
        catalog: GovernanceCatalog,
        registry: ToolRegistry,
        capabilities: Mapping[str, CapabilitySpec] | None = None,
    ):
        self.catalog = catalog
        self.registry = registry
        self.capabilities = dict(capabilities or CAPABILITIES)

    def verify(self, plan: NecessityPlan) -> VerifiedPlan:
        errors: list[str] = []
        cap = self.capabilities.get(plan.capability)

        if cap is None:
            errors.append(f"Unknown capability: {plan.capability}")
            return VerifiedPlan(plan=plan, verified=False, errors=errors)

        expected_required = list(cap.required_raw_fields)
        expected_safe_output = list(cap.safe_output_fields)

        if plan.required_fields != expected_required:
            errors.append(
                "Required-field set does not match trusted capability ontology"
            )

        if plan.safe_output_fields != expected_safe_output:
            errors.append(
                "Safe-output set does not match trusted capability ontology"
            )

        unknown = [
            f for f in set(plan.required_fields + plan.safe_output_fields)
            if f not in self.catalog.fields
        ]
        if unknown:
            errors.append(f"Unclassified fields in plan: {sorted(unknown)}")

        if not self.registry.for_capability(plan.capability):
            errors.append(
                f"No registered tool can satisfy capability '{plan.capability}'"
            )

        for param in cap.required_parameters:
            if param not in plan.parameters:
                errors.append(f"Missing required parameter: {param}")

        return VerifiedPlan(
            plan=plan,
            verified=(len(errors) == 0),
            errors=errors,
        )
