# PBME v0.1

PBME is a research prototype for **purpose-bound minimum-data enforcement**
in tool-using AI agents.

The agent is not trusted to decide its own access scope.

PBME verifies a host-signed task context, determines the information
actually needed to satisfy the task, chooses the lowest-exposure compatible
tool, narrows tool arguments before execution, filters the response, and
records evidence explaining the decision.

## Core idea

```text
User
  |
  v
Host creates signed task context
  |
  v
Agent proposes tool call
  |
  v
+----------------------------------+
| PBME                           |
|                                  |
| 1. verify trusted task context   |
| 2. map goal -> capability        |
| 3. derive minimum information    |
| 4. score compatible tools        |
| 5. choose lowest exposure tool   |
| 6. rewrite arguments             |
| 7. enforce governance policy     |
+----------------+-----------------+
                 |
                 v
             Tool / MCP
                 |
                 v
             Backend
                 |
                 v
+----------------------------------+
| Response filter                  |
| - strip undeclared fields        |
| - strip unauthorized fields      |
+----------------+-----------------+
                 |
                 v
               Agent
```

## Example

User goal:

```text
Which department had the highest turnover in 2026?
```

The agent proposes:

```json
{
  "tool": "get_employee_data",
  "arguments": {
    "fields": [
      "employee_id",
      "name",
      "ssn",
      "salary",
      "department",
      "termination_date"
    ],
    "year": 2026
  }
}
```

PBME sees that the same task can be satisfied by an aggregate tool:

```text
turnover_by_department(year=2026)
```

Instead of returning raw employee rows, it returns only:

```json
[
  {"department": "Engineering", "turnover_count": 1},
  {"department": "Finance", "turnover_count": 1},
  {"department": "Sales", "turnover_count": 1}
]
```

No name, SSN, salary, email, or employee identifier reaches the model.

If the aggregate tool is unavailable, PBME falls back to projection:

```json
{
  "fields": ["department", "termination_date"],
  "year": 2026
}
```

## Security model

PBME separates three questions:

1. **Necessity** — what information is required?
2. **Authorization** — is that information permitted for this purpose?
3. **Enforcement** — how do we ensure only that information crosses the tool boundary?

The semantic planner is advisory. The deterministic verifier and governance
engine are authoritative.

## Modules

```text
src/pbme/
  models.py            shared data models
  context.py           HMAC-signed trusted task context
  catalog.py           data classification / purpose rules
  ontology.py          verified task capability specifications
  registry.py          tool registry and metadata
  planner.py           goal -> capability planner
  llm_planner.py       pluggable structured LLM planner interface
  verifier.py          deterministic necessity-plan verifier
  scorer.py            tool/data exposure scoring
  rewriter.py          minimum-argument construction
  response_filter.py   defense-in-depth output filtering
  audit.py             structured audit evidence
  broker.py            end-to-end PBME enforcement broker
  hr_backend.py        SQLite demonstration backend
  hr_setup.py          HR governance + tool registry
  mcp_server.py        protected MCP v2 server
  downstream_mcp.py    optional MCP v2 discovery/call adapter
  evaluation.py        original small research evaluation
  benchmark/            500-scenario policy + broker validation harness
    broker_adapter.py   maps benchmark domains into real broker components
    broker_runner.py    end-to-end PBMEBroker validation
    reporting.py        domain/variant/ablation reports
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pbme-demo
pytest
pbme-eval
```

For MCP:

```bash
pip install -e ".[all]"
pbme-mcp
```

The protected MCP server uses Streamable HTTP.

## Important production note

The included task token uses HMAC so the research prototype can demonstrate
that the agent cannot freely change its task or purpose. Production deployments
should replace this with the organization's identity / authorization layer,
short-lived credentials, key rotation, audience binding, replay controls, and
central policy management.



## Evaluation harness

PBME now separates **policy simulation** from **real broker validation**.

### E1 — controlled policy simulation

```bash
pbme-benchmark generate
pbme-benchmark run --repeats 3
```

This executes:

```text
500 scenarios × 6 systems × 3 repeats = 9,000 episodes
```

across HR, customer support, finance, and enterprise-document domains.

Paper-facing outputs include:

```text
benchmark/results/
  episodes.csv
  episodes.jsonl
  summary.json
  reports/
    domain_breakdown.csv
    variant_breakdown.csv
    domain_variant_breakdown.csv
    ablation_breakdown.csv
```

### E2 — actual PBMEBroker validation

```bash
pbme-benchmark broker-run --repeats 3
```

The broker runner executes signed task context -> planner -> verifier ->
governance -> tool optimizer -> request rewriter -> actual SQLite backend ->
response filter -> audit log.

Default E2 size:

```text
full_registry: 1,500 episodes
raw_only:     1,200 episodes
total:        2,700 episodes
```

`full_registry` validates tool minimization. `raw_only` forces field
minimization. During both, the backend intentionally over-returns an undeclared
field so the actual response filter is tested rather than assumed.

Outputs are under `benchmark/broker_results/`.

### Current reproducible synthetic results

The included generated artifacts are **controlled synthetic results, not an
LLM-agent evaluation**. In the current 9,000-episode E1 run, PBME-Full
maintained 100% task/policy success in the deterministic scenarios, reduced
mean exposure cost from 30.688 (permissive) to 4.192, and had zero adversarial
forbidden-field disclosures. Static masking achieved lower exposure than the
permissive baselines but reduced task success to 55.4%, illustrating the cost
of sensitivity-only filtering without task necessity.

In the current 2,700-episode E2 run, the actual broker achieved 100% policy
accuracy, simulator policy agreement, selected-tool agreement, released-field
agreement, response-filter accuracy, and audit completeness. Raw-only episodes
also achieved 100% verified field-rewrite accuracy. These values validate the
implementation against this synthetic ground truth; they are not claims about
real enterprise or LLM behavior.

## Validation status

Validated in this build:

- configurable multi-domain capability verification
- signed task context including host-bound task parameters
- deterministic necessity planning
- purpose enforcement and deny auditing
- tool minimization and record-granularity penalty
- field minimization
- intentional backend over-return filtering
- audit generation
- 500-scenario / 9,000-episode policy simulation
- 2,700-episode real-broker integration validation
- domain, variant, and PBME-Field vs PBME-Full ablation reports
- 19 automated tests

The MCP adapter is written for the MCP Python SDK v2 API. The build environment
used for this archive does not have the external `mcp` package installed, so
the MCP transport itself was not runtime-launched here. The core enforcement,
benchmark backends, and real broker pipeline were executed locally.

## Research question

> Can an enforcement layer automatically reduce agent-visible information to
> the minimum needed for a host-authorized task while preserving task success?

See `docs/RESEARCH_DESIGN.md`.
