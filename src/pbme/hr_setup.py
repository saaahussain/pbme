from __future__ import annotations

from .catalog import GovernanceCatalog, HR_FIELD_POLICIES
from .hr_backend import HRBackend
from .models import ToolSpec
from .registry import ToolRegistry


def build_hr_environment():
    backend = HRBackend()
    catalog = GovernanceCatalog(HR_FIELD_POLICIES)
    registry = ToolRegistry()

    registry.register(
        ToolSpec(
            name="get_employee_data",
            description="Retrieve projected employee records",
            accepted_arguments=frozenset({"fields", "year", "department"}),
            output_fields=tuple(
                f for f in HR_FIELD_POLICIES
                if f not in {"turnover_count", "average_salary"}
            ),
            capabilities=frozenset({
                "turnover_by_department",
                "average_salary_by_department",
                "terminated_employee_names",
                "employee_email_lookup",
            }),
            raw_record_tool=True,
            supports_projection=True,
            field_argument="fields",
            executor=backend.get_employee_data,
        )
    )

    registry.register(
        ToolSpec(
            name="turnover_by_department",
            description="Return aggregate turnover count grouped by department",
            accepted_arguments=frozenset({"year"}),
            output_fields=("department", "turnover_count"),
            capabilities=frozenset({"turnover_by_department"}),
            raw_record_tool=False,
            executor=backend.turnover_by_department,
        )
    )

    registry.register(
        ToolSpec(
            name="average_salary_by_department",
            description="Return aggregate average salary grouped by department",
            accepted_arguments=frozenset({"department"}),
            output_fields=("department", "average_salary"),
            capabilities=frozenset({"average_salary_by_department"}),
            raw_record_tool=False,
            executor=backend.average_salary_by_department,
        )
    )

    return backend, catalog, registry
