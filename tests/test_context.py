import pytest

from pbme.context import InvalidTaskContext, TaskContextSigner


SECRET = "1234567890abcdef"


def test_signed_context_round_trip():
    signer = TaskContextSigner(SECRET)
    token = signer.issue(
        task_id="t1",
        user_goal="turnover by department 2026",
        approved_purpose="workforce_analytics",
        actor_id="u1",
        now=1000,
    )
    ctx = signer.verify(token, now=1001)
    assert ctx.task_id == "t1"
    assert ctx.approved_purpose == "workforce_analytics"


def test_tampered_context_is_rejected():
    signer = TaskContextSigner(SECRET)
    token = signer.issue(
        task_id="t1",
        user_goal="turnover",
        approved_purpose="workforce_analytics",
        actor_id="u1",
        now=1000,
    )
    payload, sig = token.split(".")
    tampered = payload[:-1] + ("A" if payload[-1] != "A" else "B")
    with pytest.raises(InvalidTaskContext):
        signer.verify(tampered + "." + sig, now=1001)


def test_expired_context_is_rejected():
    signer = TaskContextSigner(SECRET)
    token = signer.issue(
        task_id="t1",
        user_goal="turnover",
        approved_purpose="workforce_analytics",
        actor_id="u1",
        ttl_seconds=5,
        now=1000,
    )
    with pytest.raises(InvalidTaskContext):
        signer.verify(token, now=1006)
