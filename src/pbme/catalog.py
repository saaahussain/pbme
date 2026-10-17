from __future__ import annotations

from .models import FieldPolicy, Sensitivity


class GovernanceCatalog:
    def __init__(self, fields: dict[str, FieldPolicy]):
        self.fields = dict(fields)

    def require(self, field: str) -> FieldPolicy:
        if field not in self.fields:
            raise KeyError(f"Unclassified field: {field}")
        return self.fields[field]

    def purpose_allows(self, field: str, purpose: str) -> bool:
        return purpose in self.require(field).allowed_purposes

    def all_known(self, fields: list[str] | tuple[str, ...]) -> bool:
        return all(field in self.fields for field in fields)


HR_FIELD_POLICIES = {
    "employee_id": FieldPolicy(
        "employee_id", "Internal employee identifier",
        Sensitivity.CONFIDENTIAL,
        frozenset({"hr_operations", "workforce_analytics", "payroll"}),
        pii=True, direct_identifier=True,
    ),
    "name": FieldPolicy(
        "name", "Employee full name",
        Sensitivity.CONFIDENTIAL,
        frozenset({"hr_operations", "payroll"}),
        pii=True, direct_identifier=True,
    ),
    "ssn": FieldPolicy(
        "ssn", "US Social Security number",
        Sensitivity.RESTRICTED,
        frozenset({"payroll"}),
        pii=True, direct_identifier=True,
    ),
    "salary": FieldPolicy(
        "salary", "Annual employee salary",
        Sensitivity.RESTRICTED,
        frozenset({"payroll", "compensation_analysis"}),
        pii=False, direct_identifier=False,
    ),
    "department": FieldPolicy(
        "department", "Employee department",
        Sensitivity.INTERNAL,
        frozenset({
            "hr_operations", "workforce_analytics",
            "payroll", "compensation_analysis"
        }),
    ),
    "hire_date": FieldPolicy(
        "hire_date", "Employee hire date",
        Sensitivity.CONFIDENTIAL,
        frozenset({"hr_operations", "workforce_analytics"}),
    ),
    "termination_date": FieldPolicy(
        "termination_date", "Employee termination date",
        Sensitivity.CONFIDENTIAL,
        frozenset({"hr_operations", "workforce_analytics"}),
    ),
    "home_address": FieldPolicy(
        "home_address", "Employee home address",
        Sensitivity.RESTRICTED,
        frozenset({"hr_operations"}),
        pii=True, direct_identifier=True,
    ),
    "email": FieldPolicy(
        "email", "Employee email",
        Sensitivity.CONFIDENTIAL,
        frozenset({"hr_operations"}),
        pii=True, direct_identifier=True,
    ),
    # Derived / aggregate outputs.
    "turnover_count": FieldPolicy(
        "turnover_count", "Aggregated turnover count",
        Sensitivity.INTERNAL,
        frozenset({"workforce_analytics", "hr_operations"}),
    ),
    "average_salary": FieldPolicy(
        "average_salary", "Department-level average salary",
        Sensitivity.CONFIDENTIAL,
        frozenset({"compensation_analysis"}),
    ),
}
