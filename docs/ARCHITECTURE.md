# PBME Architecture

## Trust boundary

The agent is outside the trusted policy boundary.

A trusted host / control plane creates a short-lived task context containing:

- task ID
- user goal
- approved purpose
- actor identity
- expiration
- destination

The task context is signed. PBME verifies it before considering any tool call.

## Planning

The planner maps a goal to a known domain capability.

The planner never grants permissions and never defines the authoritative field
set. The trusted capability ontology does that.

This means an LLM planner can be used without allowing the LLM to self-authorize.

## Verification

The verifier checks:

- capability exists
- required fields exactly match ontology
- output fields exactly match ontology
- all fields have governance classification
- at least one registered tool can satisfy the capability
- required parameters exist

Unknown / ambiguous capabilities fail closed.

## Tool minimization

All tools that can satisfy the verified capability are considered.

PBME scores the agent-visible output of each tool and selects the
lowest-exposure policy-compliant candidate.

Aggregate tools normally beat raw-record tools.

## Field minimization

If a raw-record tool is the only viable tool, the request rewriter replaces
the requested projection with the capability's verified minimum raw field set.

## Response filtering

The returned object is filtered again to prevent an over-returning backend from
leaking undeclared fields.

## Future adapters

The core broker is transport independent.

Adapters can front:

- MCP
- REST
- GraphQL
- SQL
- vector/RAG retrieval
- SaaS SDKs
