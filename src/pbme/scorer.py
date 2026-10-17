from __future__ import annotations

from .catalog import GovernanceCatalog
from .models import Sensitivity


BASE_WEIGHT = {
    Sensitivity.PUBLIC: 0.25,
    Sensitivity.INTERNAL: 1.0,
    Sensitivity.CONFIDENTIAL: 3.0,
    Sensitivity.RESTRICTED: 7.0,
}


class ExposureScorer:
    """Scores agent-visible data exposure.

    This is an experimental metric, not a claim of universal risk.
    """

    def __init__(self, catalog: GovernanceCatalog):
        self.catalog = catalog

    def field_cost(self, field: str) -> float:
        policy = self.catalog.require(field)
        cost = BASE_WEIGHT[policy.sensitivity]
        if policy.pii:
            cost += 2.0
        if policy.direct_identifier:
            cost += 2.0
        return cost

    def fields_cost(self, fields: list[str] | tuple[str, ...]) -> float:
        return round(sum(self.field_cost(f) for f in fields), 4)
