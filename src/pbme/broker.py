from __future__ import annotations

from collections.abc import Mapping

from .audit import JsonlAuditLog
from .catalog import GovernanceCatalog
from .context import TaskContextSigner
from .models import (
    BrokerResult,
    CandidateTool,
    CapabilitySpec,
    Decision,
    EnforcementRecord,
    ProposedToolCall,
    TaskContext,
)
from .ontology import CAPABILITIES
from .planner import PlanningError
from .registry import ToolRegistry
from .response_filter import ResponseFilter
from .rewriter import RequestRewriter
from .scorer import ExposureScorer
from .verifier import PlanVerifier


class PBMEDenied(PermissionError):
    """Raised when PBME denies a tool request.

    `record` is populated whenever a trusted task context was verified, allowing
    evaluation and production logging to inspect the exact deny decision.
    """

    def __init__(
        self,
        message: str,
        record: EnforcementRecord | None = None,
    ):
        super().__init__(message)
        self.record = record


class PBMEBroker:
    def __init__(
        self,
        *,
        signer: TaskContextSigner,
        catalog: GovernanceCatalog,
        registry: ToolRegistry,
        planner,
        audit: JsonlAuditLog | None = None,
        capabilities: Mapping[str, CapabilitySpec] | None = None,
        raw_record_penalty: float = 2.0,
    ):
        self.signer = signer
        self.catalog = catalog
        self.registry = registry
        self.planner = planner
        self.audit = audit or JsonlAuditLog()
        self.capabilities = dict(capabilities or CAPABILITIES)
        self.raw_record_penalty = float(raw_record_penalty)
        self.verifier = PlanVerifier(
            catalog,
            registry,
            capabilities=self.capabilities,
        )
        self.scorer = ExposureScorer(catalog)
        self.rewriter = RequestRewriter()
        self.filter = ResponseFilter()

    def _policy_check(
        self,
        fields: list[str],
        purpose: str,
    ) -> tuple[bool, list[str]]:
        errors = [
            f"{field}: purpose '{purpose}' not allowed"
            for field in fields
            if not self.catalog.purpose_allows(field, purpose)
        ]
        return (not errors, errors)

    def _candidate(
        self,
        *,
        tool,
        proposed: ProposedToolCall,
        plan,
        purpose: str,
    ) -> CandidateTool:
        args = self.rewriter.build(
            selected_tool=tool,
            proposed=proposed,
            plan=plan,
        )

        if tool.raw_record_tool:
            released = list(plan.required_fields)
        else:
            released = list(tool.output_fields)

        policy_allowed, policy_errors = self._policy_check(released, purpose)

        # Raw record tools receive an explicit granularity penalty because a
        # row-level dataset can reveal substantially more than an aggregate
        # result even when both expose similarly classified field names.
        exposure = self.scorer.fields_cost(released)
        if tool.raw_record_tool:
            exposure += self.raw_record_penalty

        return CandidateTool(
            tool=tool,
            call_arguments=args,
            released_fields=released,
            exposure_score=round(exposure, 4),
            policy_allowed=policy_allowed,
            policy_errors=policy_errors,
        )

    def _proposed_fields(
        self,
        proposed_call: ProposedToolCall,
    ) -> list[str]:
        proposed_tool = self.registry.get(proposed_call.tool_name)
        fields = list(
            proposed_call.arguments.get(
                proposed_tool.field_argument or "fields",
                proposed_tool.output_fields,
            )
        )
        # Unknown fields are not included in exposure calculations, but they are
        # never forwarded by RequestRewriter because only registered arguments
        # and verified required fields can cross the boundary.
        return [
            f for f in fields
            if isinstance(f, str) and f in self.catalog.fields
        ]

    def _deny(
        self,
        *,
        message: str,
        context: TaskContext,
        proposed_call: ProposedToolCall,
        proposed_fields: list[str],
        rationale: list[str],
        planner_name: str,
    ) -> None:
        before = self.scorer.fields_cost(proposed_fields)
        record = EnforcementRecord(
            decision=Decision.DENY,
            context=context,
            proposed_call=proposed_call,
            selected_tool=None,
            executed_arguments={},
            released_fields=[],
            removed_fields=sorted(set(proposed_fields)),
            exposure_before=before,
            exposure_after=0.0,
            rationale=rationale,
            planner=planner_name,
        )
        self.audit.record(record)
        raise PBMEDenied(message, record=record)

    def execute(
        self,
        *,
        task_token: str,
        proposed_call: ProposedToolCall,
    ) -> BrokerResult:
        context = self.signer.verify(task_token)
        proposed_fields = self._proposed_fields(proposed_call)

        try:
            plan = self.planner.plan(context)
        except PlanningError as exc:
            self._deny(
                message=f"Task requires human approval: {exc}",
                context=context,
                proposed_call=proposed_call,
                proposed_fields=proposed_fields,
                rationale=[f"Planning failed: {exc}"],
                planner_name=getattr(self.planner, "name", "unknown"),
            )
            raise AssertionError("unreachable")

        verified = self.verifier.verify(plan)
        if not verified.verified:
            self._deny(
                message=(
                    "Necessity plan failed verification: "
                    + "; ".join(verified.errors)
                ),
                context=context,
                proposed_call=proposed_call,
                proposed_fields=proposed_fields,
                rationale=[
                    "Necessity plan verification failed",
                    *verified.errors,
                ],
                planner_name=plan.planner,
            )

        exposure_before = self.scorer.fields_cost(proposed_fields)

        candidates = [
            self._candidate(
                tool=tool,
                proposed=proposed_call,
                plan=plan,
                purpose=context.approved_purpose,
            )
            for tool in self.registry.for_capability(plan.capability)
        ]
        allowed = [c for c in candidates if c.policy_allowed]
        if not allowed:
            details = sorted({
                err for candidate in candidates
                for err in candidate.policy_errors
            })
            self._deny(
                message=(
                    "No policy-compliant tool can satisfy the task: "
                    + "; ".join(details)
                ),
                context=context,
                proposed_call=proposed_call,
                proposed_fields=proposed_fields,
                rationale=[
                    f"Mapped task to verified capability '{plan.capability}'",
                    f"Approved purpose: {context.approved_purpose}",
                    *details,
                ],
                planner_name=plan.planner,
            )

        selected = min(
            allowed,
            key=lambda c: (
                c.exposure_score,
                c.tool.raw_record_tool,
                c.tool.name,
            ),
        )

        if selected.tool.executor is None:
            raise RuntimeError(
                f"Selected tool has no executor: {selected.tool.name}"
            )

        raw = selected.tool.executor(**selected.call_arguments)
        safe = self.filter.filter(raw, selected.released_fields)

        proposed_name = proposed_call.tool_name
        if selected.tool.name != proposed_name:
            decision = Decision.REROUTE
        elif selected.call_arguments != proposed_call.arguments:
            decision = Decision.TRANSFORM
        else:
            decision = Decision.ALLOW

        removed_fields = sorted(
            set(proposed_fields) - set(selected.released_fields)
        )
        record = EnforcementRecord(
            decision=decision,
            context=context,
            proposed_call=proposed_call,
            selected_tool=selected.tool.name,
            executed_arguments=selected.call_arguments,
            released_fields=selected.released_fields,
            removed_fields=removed_fields,
            exposure_before=exposure_before,
            exposure_after=selected.exposure_score,
            rationale=[
                f"Mapped task to verified capability '{plan.capability}'",
                f"Required raw fields: {', '.join(plan.required_fields)}",
                f"Selected lowest-exposure compatible tool '{selected.tool.name}'",
                f"Approved purpose: {context.approved_purpose}",
            ],
            planner=plan.planner,
        )
        self.audit.record(record)
        return BrokerResult(data=safe, enforcement=record)
