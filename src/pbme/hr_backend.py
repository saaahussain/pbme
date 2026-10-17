from __future__ import annotations

import sqlite3
from typing import Any


EMPLOYEE_FIELDS = {
    "employee_id", "name", "ssn", "salary", "department",
    "hire_date", "termination_date", "home_address", "email",
}


class HRBackend:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._seed()

    def _seed(self):
        self.conn.executescript(
            """
            CREATE TABLE employees (
                employee_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                ssn TEXT NOT NULL,
                salary INTEGER NOT NULL,
                department TEXT NOT NULL,
                hire_date TEXT NOT NULL,
                termination_date TEXT,
                home_address TEXT NOT NULL,
                email TEXT NOT NULL
            );
            """
        )
        rows = [
            (1, "Ava Patel", "111-22-3333", 121000, "Engineering", "2022-03-01", "2026-02-15", "1 Example St", "ava@example.test"),
            (2, "Noah Smith", "222-33-4444", 93000, "Sales", "2023-06-10", "2026-05-22", "2 Example St", "noah@example.test"),
            (3, "Mia Chen", "333-44-5555", 118000, "Engineering", "2021-09-12", None, "3 Example St", "mia@example.test"),
            (4, "Liam Jones", "444-55-6666", 87000, "Sales", "2024-01-08", "2025-11-30", "4 Example St", "liam@example.test"),
            (5, "Sophia Garcia", "555-66-7777", 102000, "Finance", "2020-04-18", "2026-08-01", "5 Example St", "sophia@example.test"),
            (6, "Ethan Brown", "666-77-8888", 99000, "Engineering", "2024-07-03", "2026-09-10", "6 Example St", "ethan@example.test"),
        ]
        self.conn.executemany(
            """
            INSERT INTO employees
            (employee_id, name, ssn, salary, department, hire_date,
             termination_date, home_address, email)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    def get_employee_data(
        self,
        *,
        fields: list[str],
        year: int | None = None,
        department: str | None = None,
    ) -> list[dict[str, Any]]:
        if not fields:
            return []
        unknown = [f for f in fields if f not in EMPLOYEE_FIELDS]
        if unknown:
            raise ValueError(f"Unknown employee fields: {unknown}")

        projection = ", ".join(f'"{f}"' for f in fields)
        sql = f"SELECT {projection} FROM employees"
        clauses = []
        params: list[Any] = []

        if year is not None and "termination_date" in fields:
            clauses.append(
                "termination_date IS NOT NULL "
                "AND substr(termination_date, 1, 4) = ?"
            )
            params.append(str(year))
        if department is not None:
            clauses.append("department = ?")
            params.append(department)

        if clauses:
            sql += " WHERE " + " AND ".join(clauses)

        return [
            dict(row)
            for row in self.conn.execute(sql, params).fetchall()
        ]

    def turnover_by_department(
        self,
        *,
        year: int | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT department, COUNT(*) AS turnover_count
            FROM employees
            WHERE termination_date IS NOT NULL
        """
        params: list[Any] = []
        if year is not None:
            sql += " AND substr(termination_date, 1, 4) = ?"
            params.append(str(year))
        sql += " GROUP BY department ORDER BY turnover_count DESC, department"

        return [
            dict(row)
            for row in self.conn.execute(sql, params).fetchall()
        ]

    def average_salary_by_department(
        self,
        *,
        department: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT department, ROUND(AVG(salary), 2) AS average_salary
            FROM employees
        """
        params: list[Any] = []
        if department:
            sql += " WHERE department = ?"
            params.append(department)
        sql += " GROUP BY department ORDER BY department"

        return [
            dict(row)
            for row in self.conn.execute(sql, params).fetchall()
        ]
