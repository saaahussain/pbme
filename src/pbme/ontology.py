from __future__ import annotations

from .models import CapabilitySpec


CAPABILITIES: dict[str, CapabilitySpec] = {
    "turnover_by_department": CapabilitySpec(
        name="turnover_by_department",
        description="Count employee departures grouped by department, optionally for a year",
        trigger_terms=frozenset({
            "turnover", "department", "departures", "left", "leavers",
            "highest", "most"
        }),
        required_raw_fields=("department", "termination_date"),
        safe_output_fields=("department", "turnover_count"),
        required_parameters=(),
        supports_year=True,
    ),
    "average_salary_by_department": CapabilitySpec(
        name="average_salary_by_department",
        description="Calculate average salary grouped by department",
        trigger_terms=frozenset({
            "average", "salary", "compensation", "department", "pay"
        }),
        required_raw_fields=("department", "salary"),
        safe_output_fields=("department", "average_salary"),
        supports_department=True,
    ),
    "terminated_employee_names": CapabilitySpec(
        name="terminated_employee_names",
        description="List names of employees terminated in a given period",
        trigger_terms=frozenset({
            "terminated", "employees", "names", "left", "who"
        }),
        required_raw_fields=("name", "termination_date"),
        safe_output_fields=("name", "termination_date"),
        supports_year=True,
    ),
    "employee_email_lookup": CapabilitySpec(
        name="employee_email_lookup",
        description="Retrieve an employee email address",
        trigger_terms=frozenset({
            "email", "contact", "employee", "address"
        }),
        required_raw_fields=("name", "email"),
        safe_output_fields=("name", "email"),
    ),
}


def get_capability(name: str) -> CapabilitySpec:
    try:
        return CAPABILITIES[name]
    except KeyError as exc:
        raise KeyError(f"Unknown capability: {name}") from exc
