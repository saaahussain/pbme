from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import asdict

from .models import TaskContext


class InvalidTaskContext(ValueError):
    pass


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64d(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


class TaskContextSigner:
    """HMAC task token for the research prototype.

    This keeps task/purpose authority outside the agent. The agent may carry
    the token, but cannot alter the payload without invalidating the signature.
    """

    def __init__(self, secret: str, *, audience: str = "pbme"):
        if len(secret.encode("utf-8")) < 16:
            raise ValueError("Task context secret must be at least 16 bytes")
        self.secret = secret.encode("utf-8")
        self.audience = audience

    def issue(
        self,
        *,
        task_id: str,
        user_goal: str,
        approved_purpose: str,
        actor_id: str,
        ttl_seconds: int = 600,
        destination: str = "internal",
        task_parameters: dict[str, object] | None = None,
        now: int | None = None,
    ) -> str:
        issued = int(time.time() if now is None else now)
        ctx = TaskContext(
            task_id=task_id,
            user_goal=user_goal,
            approved_purpose=approved_purpose,
            actor_id=actor_id,
            issued_at=issued,
            expires_at=issued + ttl_seconds,
            audience=self.audience,
            destination=destination,
            task_parameters=dict(task_parameters or {}),
        )
        payload = json.dumps(
            asdict(ctx), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        sig = hmac.new(self.secret, payload, hashlib.sha256).digest()
        return f"{_b64e(payload)}.{_b64e(sig)}"

    def verify(self, token: str, *, now: int | None = None) -> TaskContext:
        try:
            payload_part, sig_part = token.split(".", 1)
            payload = _b64d(payload_part)
            supplied_sig = _b64d(sig_part)
        except Exception as exc:
            raise InvalidTaskContext("Malformed task token") from exc

        expected = hmac.new(self.secret, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, supplied_sig):
            raise InvalidTaskContext("Invalid task-token signature")

        try:
            data = json.loads(payload.decode("utf-8"))
            ctx = TaskContext(**data)
        except Exception as exc:
            raise InvalidTaskContext("Invalid task-token payload") from exc

        current = int(time.time() if now is None else now)
        if ctx.audience != self.audience:
            raise InvalidTaskContext("Wrong task-token audience")
        if ctx.expires_at < current:
            raise InvalidTaskContext("Expired task token")
        if ctx.issued_at > current + 30:
            raise InvalidTaskContext("Task token issued in the future")
        return ctx
