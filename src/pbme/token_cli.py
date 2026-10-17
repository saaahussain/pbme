from __future__ import annotations

import argparse
import os

from .context import TaskContextSigner


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--ttl", type=int, default=600)
    args = parser.parse_args()

    secret = os.environ.get(
        "PBME_CONTEXT_SECRET",
        "pbme-demo-secret-change-me",
    )
    signer = TaskContextSigner(secret)
    print(
        signer.issue(
            task_id=args.task_id,
            user_goal=args.goal,
            approved_purpose=args.purpose,
            actor_id=args.actor,
            ttl_seconds=args.ttl,
        )
    )


if __name__ == "__main__":
    main()
