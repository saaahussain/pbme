# Reproducible Results Snapshot

> These are controlled synthetic evaluation results produced by this repository. They are not an LLM-in-the-loop or real-enterprise benchmark.

## E1 — Controlled policy simulation

500 scenarios × 6 systems × 3 repeats = **9,000 episodes**.

| System | Task success | Policy success | Mean exposure | UDAR | ASR | FDR | TMR | Mean latency (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Permissive | 0.800 | 0.800 | 30.688 | 0.472 | 0.950 | 0.000 | 0.000 | 0.0428 |
| RBAC-only | 0.980 | 0.980 | 22.378 | 0.331 | 0.950 | 0.000 | 0.000 | 0.0325 |
| Static masking | 0.554 | 0.800 | 5.670 | 0.398 | 0.050 | 0.000 | 0.000 | 0.0488 |
| ARES-like | 0.660 | 0.660 | 4.858 | 0.044 | 0.100 | 0.425 | 0.000 | 0.0156 |
| PBME-Field | 1.000 | 1.000 | 4.918 | 0.000 | 0.000 | 0.000 | 0.000 | 0.0275 |
| PBME-Full | 1.000 | 1.000 | 4.192 | 0.000 | 0.000 | 0.000 | 1.000 | 0.0372 |

PBME-Full reduced mean exposure cost by **86.34%** relative to permissive execution in this synthetic benchmark.
Compared with PBME-Field, tool minimization reduced mean exposure by an additional **14.76%** while preserving the same deterministic task success.

## E2 — Actual PBMEBroker integration validation

Full-registry mode: **1,500 episodes**. Raw-only mode: **1,200 episodes**. Total: **2,700 episodes**.

| Mode | Episodes | Task success | Policy accuracy | Simulator policy agreement | Tool agreement | Field agreement | Field rewrite | Response filter | Audit completeness | Mean latency (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| full_registry | 1500 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | N/A | 1.000 | 1.000 | 0.1810 |
| raw_only | 1200 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.1457 |

## Interpretation

- E1 supports controlled claims about relative policy behavior under fixed synthetic ground truth.
- E2 supports the claim that the implemented broker realizes the simulated PBME policy in these environments.
- Neither evaluation shows how a real LLM chooses tools or behaves under naturalistic prompt injection. That is a separate E3 experiment.
- In-process latency values are useful for regression comparison only; they are not production MCP/network latency.
