"""Example showing how an external semantic model plugs into PBME.

The fake model intentionally returns only a capability and parameters.
Authoritative fields still come from PBME's trusted ontology.
"""

from pbme.llm_planner import StructuredLLMPlanner


def fake_model(prompt: str):
    return {
        "capability": "turnover_by_department",
        "parameters": {"year": 2026},
        "confidence": 0.97,
        "reasons": ["Turnover grouped by department is requested"],
    }


planner = StructuredLLMPlanner(fake_model)
