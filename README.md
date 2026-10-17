# PBME — Purpose-Bound Minimum-Data Enforcement

PBME is a research prototype for enforcing **minimum-data access in tool-using AI agents**.

Modern AI agents can call databases, APIs, MCP tools, retrieval systems, and enterprise services. Traditional access control answers:

> Is this user or agent allowed to access this resource?

PBME asks an additional question:

> What is the minimum information required to complete this specific authorized task?

An agent may be authorized to access an employee database, for example, while a particular task requires only department-level turnover statistics. PBME attempts to prevent unrelated employee names, salaries, identifiers, or other sensitive fields from reaching the model.

PBME is designed as a runtime governance layer between an AI agent and the tools it invokes.

---

## What PBME does

PBME combines:

- **purpose binding** — task purpose is established by a trusted host rather than declared by the agent;
- **task-necessity verification** — required information is checked against a trusted capability specification;
- **field minimization** — over-broad tool requests are narrowed before execution;
- **tool minimization** — when multiple tools can satisfy the task, PBME can choose the lower-exposure capability;
- **response filtering** — undeclared or unauthorized fields are removed before reaching the agent;
- **auditable enforcement** — allow, transform, reroute, and deny decisions are recorded.

The LLM or semantic planner is not treated as the final authorization authority. The deterministic verifier and governance policy remain authoritative.

---



## Why PBME?

Existing agent-security approaches commonly focus on whether a tool invocation or resource action should be allowed.

PBME focuses on a complementary problem:

> Even when an action is authorized, how much information should the agent actually see?

For example:

```text
User task:
Which department had the highest turnover in 2026?
```

An agent might request:

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

PBME can determine that the task does not require employee identity or salary information.

If an aggregate capability exists, PBME can reroute the request to:

```text
turnover_by_department(year=2026)
```

If no safer specialized tool exists, PBME can instead rewrite the raw request to:

```json
{
  "fields": [
    "department",
    "termination_date"
  ],
  "year": 2026
}
```

The objective is to reduce information exposure **before sensitive data enters the agent context whenever possible**.

---



## Architecture

```text
Trusted Host
     |
     v
Signed Task Context
     |
     v
AI Agent
     |
     | proposed tool call
     v
+--------------------------------------+
|                 PBME                 |
|                                      |
|  Task Verification                   |
|  Necessity Planner                   |
|  Deterministic Plan Verifier         |
|  Governance Policy                   |
|  Tool Optimizer                      |
|  Request Rewriter                    |
+-------------------+------------------+
                    |
                    v
             MCP / REST / Tool
                    |
                    v
              Enterprise Backend
                    |
                    v
             Response Filter
                    |
                    v
                 Agent
```

PBME can sit at structured tool boundaries such as MCP, REST APIs, database wrappers, or other function-calling interfaces.

---



## Current evaluation

PBME currently contains two separate evaluation tracks.

### E1 — Controlled policy simulation

```text
500 scenarios
× 6 security configurations
× 3 deterministic repetitions
= 9,000 episodes
```

The benchmark spans four synthetic enterprise-style domains:

- Human Resources
- Customer Support
- Finance
- Enterprise Documents

Each base task is evaluated using five variants:

- clean request;
- over-broad fields;
- safer-tool available;
- wrong purpose;
- adversarial field smuggling.

Six configurations are compared:

- Permissive
- RBAC-only
- Static Masking
- ARES-like action guard
- PBME-Field
- PBME-Full



### E1 result snapshot


| System         | Task Success | Policy Success | Mean Exposure | UDAR      | ASR       | FDR       | TMR       |
| -------------- | ------------ | -------------- | ------------- | --------- | --------- | --------- | --------- |
| Permissive     | 0.800        | 0.800          | 30.688        | 0.472     | 0.950     | 0.000     | 0.000     |
| RBAC-only      | 0.980        | 0.980          | 22.378        | 0.331     | 0.950     | 0.000     | 0.000     |
| Static Masking | 0.554        | 0.800          | 5.670         | 0.398     | 0.050     | 0.000     | 0.000     |
| ARES-like      | 0.660        | 0.660          | 4.858         | 0.044     | 0.100     | 0.425     | 0.000     |
| PBME-Field     | 1.000        | 1.000          | 4.918         | 0.000     | 0.000     | 0.000     | 0.000     |
| **PBME-Full**  | **1.000**    | **1.000**      | **4.192**     | **0.000** | **0.000** | **0.000** | **1.000** |


In this controlled benchmark, PBME-Full reduced mean synthetic exposure cost from:

```text
30.688 → 4.192
```

which corresponds to an **86.34% reduction** relative to permissive execution.

PBME-Field achieved a mean exposure cost of 4.918, while PBME-Full reduced this further to 4.192 through tool minimization.

Static masking reduced exposure but lowered task success to **55.4%**, illustrating that sensitivity-only filtering can remove information that is actually necessary for a task.

These are **controlled synthetic benchmark results** and should not be interpreted as measurements of real-world LLM-agent behavior.

---



## E2 — Actual PBMEBroker validation

The second evaluation executes the actual PBME enforcement pipeline:

```text
Signed Task Context
        |
        v
PBMEBroker
        |
        v
Planner
        |
        v
Plan Verifier
        |
        v
Governance Policy
        |
        v
Tool Optimizer
        |
        v
Request Rewriter
        |
        v
SQLite Backend
        |
        v
Response Filter
        |
        v
Audit Log
```

Two configurations are tested:

```text
Full registry: 1,500 episodes
Raw only:     1,200 episodes
Total:        2,700 episodes
```

The full-registry configuration exercises lower-exposure tool selection.

The raw-only configuration removes specialized tools and therefore forces the actual request rewriter to perform field minimization.

The backend also intentionally over-returns an undeclared field so that response filtering is exercised directly.

### E2 result snapshot

Across the controlled broker-validation task family:


| Metric                     | Full Registry | Raw Only |
| -------------------------- | ------------- | -------- |
| Task success               | 1.000         | 1.000    |
| Policy accuracy            | 1.000         | 1.000    |
| Simulator policy agreement | 1.000         | 1.000    |
| Exact decision agreement   | 1.000         | 1.000    |
| Selected-tool agreement    | 1.000         | 1.000    |
| Released-field agreement   | 1.000         | 1.000    |
| Field-rewrite accuracy     | N/A           | 1.000    |
| Response-filter accuracy   | 1.000         | 1.000    |
| Audit completeness         | 1.000         | 1.000    |


These results demonstrate **implementation conformance within the controlled benchmark family**.

They do not demonstrate:

- open-domain natural-language understanding;
- real LLM tool-selection behavior;
- real enterprise deployment performance;
- naturalistic prompt-injection resistance.

Those are future evaluation stages.

---



## Reproducibility

Generate the 500 benchmark scenarios:

```bash
pbme-benchmark generate
```

Run E1:

```bash
pbme-benchmark run --repeats 3
```

Run E2:

```bash
pbme-benchmark broker-run --repeats 3
```

The primary artifacts are:

```text
benchmark/
├── scenarios_500.jsonl
│
├── results/
│   ├── episodes.csv
│   ├── episodes.jsonl
│   ├── summary.json
│   └── reports/
│       ├── domain_breakdown.csv
│       ├── variant_breakdown.csv
│       ├── domain_variant_breakdown.csv
│       └── ablation_breakdown.csv
│
└── broker_results/
    ├── broker_episodes.csv
    ├── broker_episodes.jsonl
    └── broker_summary.json
```

PBME's policy and conformance outcomes are deterministic in the current controlled benchmark. Repeated executions produce identical non-timing decisions.

In-process latency varies with machine load and execution conditions and is therefore treated only as an illustrative prototype regression measurement, not as a fixed scientific outcome.

---



## Security model

PBME separates three questions:

1. **Necessity** — what information is actually required for the task?
2. **Authorization** — is that information permitted for the approved purpose?
3. **Enforcement** — how can only the permitted minimum information cross the tool boundary?

A field can therefore be:

```text
necessary + authorized
necessary + unauthorized
unnecessary + authorized
unnecessary + unauthorized
```

PBME only releases information that satisfies both necessity and authorization requirements.

---



## Trust boundary

The agent and semantic planner are not treated as security authorities.

```text
LLM / Planner
     |
     | proposes capability
     v
Deterministic Verifier
     |
     v
Governance Policy
     |
     v
Tool / Field Enforcement
```

A compromised or prompt-injected planner cannot authorize a new field merely by declaring that field necessary.

---



## Repository structure

```text
src/pbme/
├── models.py
├── context.py
├── catalog.py
├── ontology.py
├── registry.py
├── planner.py
├── llm_planner.py
├── verifier.py
├── scorer.py
├── rewriter.py
├── response_filter.py
├── audit.py
├── broker.py
├── hr_backend.py
├── hr_setup.py
├── mcp_server.py
├── downstream_mcp.py
├── evaluation.py
│
└── benchmark/
    ├── broker_adapter.py
    ├── broker_runner.py
    ├── reporting.py
    ├── baselines.py
    ├── metrics.py
    ├── runner.py
    └── cli.py
```

---



## Install and run

Requires **Python 3.11+**.

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pbme-demo
pytest
pbme-eval
```



### Windows Command Prompt

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -U pip
pip install -e ".[dev]"

pbme-demo
pytest
pbme-eval
```



### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"

pbme-demo
pytest
pbme-eval
```

If PowerShell blocks script execution, run once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Leave the virtual environment with:

```bash
deactivate
```

---



## Without console scripts

If `pbme-benchmark` is not recognized, either activate `.venv` and run `pip install -e .`, or invoke the module directly from the repository root.

### macOS / Linux

```bash
PYTHONPATH=src python -m pbme.benchmark.cli generate
```



### Windows Command Prompt

```cmd
set PYTHONPATH=src
python -m pbme.benchmark.cli generate
```



### Windows PowerShell

```powershell
$env:PYTHONPATH = "src"
python -m pbme.benchmark.cli generate
```

---



## MCP adapter

Install optional dependencies:

```bash
pip install -e ".[all]"
pbme-mcp
```

The protected server is designed for the MCP Python SDK v2 interface and uses Streamable HTTP.

The archived development environment used for the current evaluation did not include the external `mcp` dependency, so the MCP transport itself was not part of the reported runtime evaluation.

The PBME core enforcement pipeline and benchmark backends were executed directly.

---



## Production note

PBME is a research prototype.

The included signed task context uses HMAC to demonstrate that an agent cannot freely modify its approved purpose or task parameters.

A production deployment should integrate:

- enterprise workload identity;
- centralized authorization;
- short-lived credentials;
- asymmetric signing where appropriate;
- key rotation;
- audience binding;
- replay protection;
- enterprise data classification;
- centralized policy management;
- production audit infrastructure.

---



## Current validation status

The current implementation validates:

- multi-domain capability verification;
- host-signed task context;
- host-bound task parameters;
- deterministic necessity planning;
- purpose enforcement;
- deny auditing;
- tool minimization;
- record-granularity penalties;
- field minimization;
- backend over-return filtering;
- structured audit generation;
- 500 benchmark scenarios;
- 9,000 E1 policy-simulation episodes;
- 2,700 E2 broker-validation episodes;
- domain and variant breakdowns;
- PBME-Field vs PBME-Full ablation reporting;
- 19 automated tests.

---



## Current limitations

PBME has not yet been evaluated with real LLM agents in the loop.

The current experiments use:

- synthetic enterprise-style datasets;
- controlled tool schemas;
- deterministic benchmark ground truth;
- deterministic task planning for E2;
- local SQLite-backed tool implementations.

The next research stage will evaluate:

```text
User Task
   |
   v
Real LLM Agent
   |
   v
Proposed Tool Call
   |
   v
PBMEBroker
   |
   v
Tool / Backend
   |
   v
Response Filter
   |
   v
LLM Final Answer
```

This will allow measurement of real-model over-broad requests, tool selection, prompt-injection behavior, task success, token overhead, and exposure reduction.

---



## Research question

> Can a runtime enforcement layer automatically reduce agent-visible information to the minimum required for a host-authorized task while preserving task success?

See:

```text
docs/RESEARCH_DESIGN.md
```

