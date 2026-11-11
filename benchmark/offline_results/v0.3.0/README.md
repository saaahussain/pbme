# PBME v0.3.0 offline study outputs

This folder contains outputs regenerated from published source commit `2d2450d2b7f8ba8beb3269053ee5971fc941074c`. Its study summaries exactly match those used in the revised manuscript. The original study used commit `cef237bda4696be3774ffae27d0a62729e8655fe`. Source hashes and input hashes are recorded in study_manifest.json.

## Contents

- E3_by_scenario_type.csv contains the seven original E3 challenge families by model and execution condition.
- The three sensitivity CSVs contain all tested settings and metrics.
- registry_mutation_manifest.json records the capability masks and mutations.
- replay_summary.json records zero mismatches over all 3,600 archived executions.
- The .jsonl.gz files contain the full per-execution records, compressed losslessly with gzip.
- study_manifest.json records settings, source identity, input hashes, record counts, and uncompressed-record hashes.
- SHA256SUMS contains exact-byte hashes for every artifact file except SHA256SUMS itself.

## Verify after downloading

From the repository root with Python 3.11 or later:

```text
python benchmark/offline_results/v0.3.0/verify_checksums.py
```

On systems with sha256sum, change into this folder and run `sha256sum -c SHA256SUMS`.

## Reproduce

From the repository root:

```text
python pbme_offline_study.py replay
python pbme_offline_study.py weights
python pbme_offline_study.py broker500
python pbme_offline_study.py registry
```

The harness reads the frozen inputs already in the repository and writes regenerated outputs to PBME_offline_study/ at the repository root. It disables network calls and generates no new LLM proposals. It uses in-memory backends and isolated metadata for fault injection.

The study includes 3,600 replay executions, 27,000 E3 weight executions, 15,000 controlled broker executions, and 135,000 registry-fault executions. These counts include repetitions and repeated controls. They do not represent independent task families. Timing fields can differ on reproduction.

## Read a compressed record file

```python
import gzip
import json

path = "benchmark/offline_results/v0.3.0/E3_weight_episodes.jsonl.gz"
with gzip.open(path, "rt", encoding="utf-8") as handle:
    first_record = json.loads(next(handle))
print(first_record)
```

This folder is prepared for review. Publication of a Git tag, GitHub Release, and Zenodo record is performed separately.
