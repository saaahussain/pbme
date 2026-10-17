from __future__ import annotations

from pbme.models import Sensitivity

from .domains import DomainSpec


WEIGHTS = {
    Sensitivity.PUBLIC: 0.25,
    Sensitivity.INTERNAL: 1.0,
    Sensitivity.CONFIDENTIAL: 3.0,
    Sensitivity.RESTRICTED: 7.0,
}


def exposure_cost(spec: DomainSpec, fields: list[str]) -> float:
    total = 0.0
    for field in fields:
        policy = spec.field_policies.get(field)
        if not policy:
            total += 10.0
            continue
        total += WEIGHTS[policy.sensitivity]
        if policy.pii:
            total += 2.0
        if policy.direct_identifier:
            total += 2.0
    return round(total, 4)


def data_minimization_ratio(
    requested: list[str], released: list[str]
) -> float:
    if not requested:
        return 0.0
    # A rerouted aggregate tool can legitimately return a derived field
    # (e.g. turnover_count) in addition to a grouping key even when the raw
    # request named fewer columns. DMR is therefore a bounded *reduction*
    # metric; tool-level benefit is measured separately by exposure and TMR.
    return round(
        max(0.0, 1 - (len(set(released)) / len(set(requested)))),
        4,
    )


def unnecessary_rate(
    released: list[str], required: list[str]
) -> tuple[list[str], float]:
    released_set = set(released)
    unnecessary = sorted(released_set - set(required))
    if not released_set:
        return unnecessary, 0.0
    return unnecessary, round(
        len(unnecessary) / len(released_set),
        4,
    )
