# PBME Local Validation

Validation performed after consolidating the active E3 code and benchmark under the
single public name **E3**.

## Automated tests

```text
42 passed
```

Command:

```bash
python -m pytest -q
```

## Python compilation

`python -m compileall -q src tests` completed successfully.

## Canonical E3 dataset

```text
Path:    benchmark/e3/scenarios.jsonl
Count:   200 scenarios
SHA-256: fc9bf1e8aabe4db42052658a28843421b704091a94ac30ea61a4dbb37670c667
```

Regenerating the dataset with `pbme-benchmark generate-e3` produced a byte-for-byte
identical `scenarios.jsonl` with the same SHA-256.

Prompt SHA-256:

```text
9c3b588d09c85a5ee1914e156fab203a48fa1f8e875af31db13a3327df3a7405
```

## Cached-proposal replay check

The retained final GPT-6 Luna three-repeat proposal cache was replayed against
the consolidated `benchmark/e3/scenarios.jsonl` without making a new model call.
All substantive Direct/PBME metrics matched the archived final summary; only
in-process execution latency is expected to vary across replay environments.

```text
Final GPT-6 Luna x3 cached replay
  proposals:                        600
  paired episodes:                  1,200

Direct
  scenario success:                 0.815
  task completion:                  0.9056
  policy success:                   0.900
  mean exposure cost:               6.6417
  UDAR:                             0.0668
  FFRR:                             0.0217

PBME
  scenario success:                 1.000
  task completion:                  1.000
  policy success:                   1.000
  mean exposure cost:               4.3500
  UDAR:                             0.000
  FFRR:                             0.000
  eligible tool-minimization cases: 64
  successful minimizations:         64
  TMR:                              1.000
```


The final GPT-6 Luna artifact is retained under:

```text
benchmark/llm_results/final_gpt6_luna_r3/
```

The one-repeat validation artifact remains separately labeled under
`benchmark/llm_results/validation_gpt6_luna_r1/`.


## OpenRouter Chat Completions adapter

The OpenRouter proposal adapter uses `/chat/completions` and preserves the frozen E3 neutral instruction text and semantic function schemas. It requires one tool call, omits the inconsistently supported `parallel_tool_calls` transport parameter, and rejects zero/multiple tool-call responses.

## E3 invalid-proposal harness validation

- Test suite: 44 passed.
- Completed-but-invalid model responses (zero/multiple/malformed tool calls) are recorded as proposal failures and do not terminate the run.
- Invalid proposals produce paired Direct/PBME failure rows so they are not silently excluded from success metrics.
- Transport/API exceptions remain fatal.
- Existing final GPT-6 Luna x3 proposal cache replayed successfully; all historical non-execution-latency summary fields were unchanged.
- Frozen E3 scenario JSONL SHA-256 remains `fc9bf1e8aabe4db42052658a28843421b704091a94ac30ea61a4dbb37670c667`.
