from pbme.response_filter import ResponseFilter


def test_over_returned_fields_are_removed():
    raw = [
        {
            "department": "Sales",
            "termination_date": "2026-01-01",
            "ssn": "999-99-9999",
        }
    ]
    safe = ResponseFilter().filter(
        raw, ["department", "termination_date"]
    )
    assert safe == [
        {
            "department": "Sales",
            "termination_date": "2026-01-01",
        }
    ]
