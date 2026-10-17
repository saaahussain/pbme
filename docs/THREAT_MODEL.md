# Threat Model

## Protected assets

- sensitive enterprise data
- personal data
- restricted identifiers
- confidential derived information
- authorization purpose and task scope

## Adversary assumptions

The agent may:

- be manipulated by prompt injection
- request more fields than necessary
- select an over-broad tool
- attempt to change the declared purpose
- smuggle unknown arguments
- receive an over-broad backend response

The downstream tool/server may accidentally over-return fields.

## Trusted components

For this prototype:

- task-context signer
- PBME verifier
- governance catalog
- capability ontology
- tool metadata registered by the operator
- enforcement broker

The semantic planner is not trusted for authorization.

## Out of scope in v0.2

- malicious operating-system administrator
- compromised PBME process
- covert channels
- model memorization after data has already been disclosed
- complete OAuth/OIDC workload identity
- cryptographic proof of data deletion
- arbitrary unstructured binary content
- full dynamic policy language
