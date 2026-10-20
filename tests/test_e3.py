from __future__ import annotations

from collections import Counter

from pbme.benchmark.broker_adapter import build_benchmark_broker
from pbme.benchmark.domains import DOMAINS
from pbme.benchmark.e3 import generate_e3_scenarios
from pbme.benchmark.llm_runner import run_llm_evaluation
from pbme.benchmark.llm_tools import tool_schemas_for_domain
from pbme.llm_agent import LLMToolProposal
from pbme.models import ProposedToolCall


SECRET = "0123456789abcdef"


class RawFakeProposer:
    provider_name = "fake"
    model = "fake-model"

    def __init__(self):
        self.calls = 0

    def propose(self, *, user_goal, tools, additional_content=None):
        self.calls += 1
        raw = tools[0]
        fields = list(raw["parameters"]["properties"]["fields"]["items"]["enum"])
        return LLMToolProposal(
            provider=self.provider_name,
            requested_model=self.model,
            resolved_model=self.model,
            response_id=f"fake-{self.calls}",
            tool_name=raw["name"],
            arguments={"fields": fields},
            input_tokens=1,
            output_tokens=1,
            total_tokens=2,
            latency_ms=1.0,
        )


def _one(domain: str, capability: str, *, outcome: str = "allow"):
    return next(
        s
        for s in generate_e3_scenarios()
        if s.domain == domain
        and s.capability == capability
        and s.expected_outcome == outcome
    )


def _broker_for(scenario, *, mode="raw_only"):
    broker, signer, _ = build_benchmark_broker(
        DOMAINS[scenario.domain],
        secret=SECRET,
        mode=mode,
        required_field_overrides={
            scenario.capability: tuple(scenario.required_fields)
        },
    )
    token = signer.issue(
        task_id=scenario.scenario_id,
        user_goal=scenario.goal,
        approved_purpose=scenario.purpose,
        actor_id="e3-test",
        task_parameters=dict(scenario.parameters),
    )
    return broker, token


def test_e3_dataset_shape_and_balance():
    scenarios = generate_e3_scenarios()
    assert len(scenarios) == 200
    assert len({s.scenario_id for s in scenarios}) == 200
    assert Counter(s.domain for s in scenarios) == {
        "hr": 50,
        "support": 50,
        "finance": 50,
        "documents": 50,
    }
    assert Counter(s.variant for s in scenarios) == {
        "clean_natural": 40,
        "semantic_ambiguity": 40,
        "distractor_context": 30,
        "raw_field_minimization": 30,
        "purpose_conflict": 20,
        "indirect_prompt_injection": 30,
        "unseen_paraphrase": 10,
    }
    assert Counter(s.e3_modes[0] for s in scenarios) == {
        "full_registry": 100,
        "raw_only": 100,
    }
    assert Counter(s.expected_outcome for s in scenarios) == {
        "allow": 180,
        "deny": 20,
    }
    assert all(s.tool_profile == "hard" for s in scenarios)
    # The internal split string is retained to keep existing traces/cache keys stable.
    assert all(s.split == "frozen_eval_v2_1" for s in scenarios)
    assert all(s.required_arguments is not None for s in scenarios)


def test_e3_goals_map_with_revised_raw_field_ground_truth():
    for scenario in generate_e3_scenarios():
        broker, signer, _ = build_benchmark_broker(
            DOMAINS[scenario.domain],
            secret=SECRET,
            mode=scenario.e3_modes[0],
            required_field_overrides={
                scenario.capability: tuple(scenario.required_fields)
            },
        )
        token = signer.issue(
            task_id=scenario.scenario_id,
            user_goal=scenario.goal,
            approved_purpose=scenario.purpose,
            actor_id="e3-test",
            task_parameters=dict(scenario.parameters),
        )
        plan = broker.planner.plan(signer.verify(token))
        verified = broker.verifier.verify(plan)
        assert plan.capability == scenario.capability, scenario.scenario_id
        assert plan.required_fields == scenario.required_fields
        assert verified.verified, (scenario.scenario_id, verified.errors)


def test_e3_runner_respects_per_scenario_mode(tmp_path):
    scenario = next(
        s
        for s in generate_e3_scenarios()
        if s.e3_modes == ["raw_only"] and s.expected_outcome == "allow"
    )
    proposer = RawFakeProposer()
    results, _ = run_llm_evaluation(
        [scenario],
        proposer=proposer,
        modes=("full_registry", "raw_only"),
        variants=("all",),
        out_dir=tmp_path,
        resume=False,
    )
    assert proposer.calls == 1
    assert {r.mode for r in results} == {"raw_only"}
    assert len(results) == 2



def test_e3_runner_defaults_to_complete_canonical_variant_set(tmp_path):
    scenario = next(
        s for s in generate_e3_scenarios()
        if s.e3_modes == ["raw_only"] and s.expected_outcome == "allow"
    )
    proposer = RawFakeProposer()
    results, _ = run_llm_evaluation(
        [scenario],
        proposer=proposer,
        modes=("raw_only",),
        limit=1,
        out_dir=tmp_path,
        resume=False,
    )
    assert proposer.calls == 1
    assert len(results) == 2


def test_hard_tool_profile_removes_explicit_minimization_hints():
    tools = tool_schemas_for_domain(
        DOMAINS["hr"], mode="full_registry", profile="hard"
    )
    raw = next(t for t in tools if t["name"] == "get_employee_data")
    field_description = raw["parameters"]["properties"]["fields"]["description"]
    assert "necessary" not in field_description.lower()

    safe = next(t for t in tools if t["name"] == "turnover_by_department")
    assert "returns only these output fields" not in safe["description"].lower()


def test_selector_identifier_is_preserved_from_signed_task_context():
    scenario = _one("support", "email_lookup")
    assert scenario.required_arguments == ["customer_id"]
    assert "customer_id" not in scenario.required_fields
    assert scenario.required_fields == ["email"]

    broker, token = _broker_for(scenario)
    trusted_customer_id = scenario.parameters["customer_id"]
    wrong_agent_id = 999 if trusted_customer_id != 999 else 998

    result = broker.execute(
        task_token=token,
        proposed_call=ProposedToolCall(
            "get_customer_data",
            {
                "customer_id": wrong_agent_id,
                "fields": ["customer_id", "email", "phone"],
            },
        ),
    )

    assert result.enforcement.executed_arguments["customer_id"] == trusted_customer_id
    assert result.enforcement.executed_arguments["fields"] == ["email"]
    assert result.enforcement.released_fields == ["email"]


def test_unbound_identifier_filter_is_not_allowed_to_change_task_scope():
    scenario = _one("support", "order_status_counts")
    assert scenario.required_arguments == []

    broker, token = _broker_for(scenario)
    result = broker.execute(
        task_token=token,
        proposed_call=ProposedToolCall(
            "get_customer_data",
            {"customer_id": 101, "fields": ["order_status"]},
        ),
    )

    assert "customer_id" not in result.enforcement.executed_arguments
    assert result.enforcement.executed_arguments["fields"] == ["order_status"]
    assert len(result.data) == 5


def test_identifier_can_be_required_returned_data_not_just_a_selector():
    scenario = _one("finance", "audit_invoice_lookup")
    assert scenario.required_arguments == ["invoice_id"]
    assert "invoice_id" not in scenario.required_fields
    assert "transaction_id" in scenario.required_fields

    broker, token = _broker_for(scenario)
    result = broker.execute(
        task_token=token,
        proposed_call=ProposedToolCall(
            "get_finance_data",
            {
                "invoice_id": scenario.parameters["invoice_id"],
                "fields": [
                    "invoice_id",
                    "transaction_id",
                    "account_id",
                    "amount",
                    "merchant",
                ],
            },
        ),
    )

    assert "transaction_id" in result.enforcement.released_fields
    assert "invoice_id" not in result.enforcement.released_fields
    assert (
        result.enforcement.executed_arguments["invoice_id"]
        == scenario.parameters["invoice_id"]
    )
    assert "account_id" not in result.enforcement.released_fields


def test_sensitive_identifier_is_removed_when_not_needed_for_the_task():
    scenario = _one("finance", "monthly_spend")
    broker, token = _broker_for(scenario)
    result = broker.execute(
        task_token=token,
        proposed_call=ProposedToolCall(
            "get_finance_data",
            {
                "month": scenario.parameters["month"],
                "fields": ["amount", "account_id", "routing_number"],
            },
        ),
    )

    assert (
        result.enforcement.executed_arguments["month"]
        == scenario.parameters["month"]
    )
    assert result.enforcement.executed_arguments["fields"] == [
        "transaction_date",
        "amount",
    ]
    assert "account_id" not in result.enforcement.released_fields
    assert "routing_number" not in result.enforcement.released_fields
