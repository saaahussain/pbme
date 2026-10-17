from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import EnforcementRecord


class JsonlAuditLog:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self.events: list[dict] = []

    def record(self, record: EnforcementRecord) -> dict:
        event = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            **asdict(record),
        }
        # Enums inside dataclass output need a stable serializable value.
        event["decision"] = record.decision.value
        self.events.append(event)

        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, sort_keys=True, default=str) + "\n")

        return event
