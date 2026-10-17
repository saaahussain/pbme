# Changelog

## v0.1.0 — PBME public release

PBME (*Purpose-Bound Minimum-data Enforcement*) is the public research codebase.

Added in response to the evaluation/reviewer gap between policy simulation and
actual implementation validation:

- configurable capability registry in `DeterministicInformationPlanner`,
  `PlanVerifier`, and `PBMEBroker`
- signed `task_parameters` in `TaskContext`
- auditable deny decisions (`PBMEDenied.record`)
- explicit raw-record granularity penalty in tool optimization
- benchmark-to-broker adapter for all four domains
- `broker-run` validation CLI
- full-registry tool-minimization validation
- raw-only field-rewrite validation
- intentional backend over-return fault injection
- response-filter accuracy measurement
- simulator/broker policy, decision, tool, and field agreement metrics
- audit-completeness metric
- domain, variant, domain×variant reports
- PBME-Field vs PBME-Full ablation report
- `safe_output_fields` ground truth for correct UDAR measurement
- bounded DMR for aggregate-tool rerouting
- 19 automated tests
- regenerated 9,000-episode policy-simulation artifacts
- generated 2,700-episode real-broker integration artifacts

The large benchmark remains synthetic. No LLM-in-the-loop claims are made by
these artifacts.
