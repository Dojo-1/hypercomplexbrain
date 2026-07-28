#!/usr/bin/env python3
"""Dispatch, resume, ingest and visualise the Godelian-1 witness batch.

The trigger is asynchronous.  ``dispatch`` records opaque handle references and
exits; it does not claim that this process will collect a future verdict.
A terminal response exported from the agent conversation is applied explicitly
with ``ingest``.

Examples
--------

Set the token in the shell environment without placing its value on this command
line, then:

    PYTHONPATH=src python3 experiments/dispatch_review_batch.py dispatch
    PYTHONPATH=src python3 experiments/dispatch_review_batch.py status
    PYTHONPATH=src python3 experiments/dispatch_review_batch.py render
    PYTHONPATH=src python3 experiments/dispatch_review_batch.py reconcile \
        artifacts/r4/review_batch/dispatch.json
    PYTHONPATH=src python3 experiments/dispatch_review_batch.py ingest \
        s7-deterministic-recompute response.json

``dispatch --dry-run`` performs no writes and no network calls.  By default the
committed dispatch request is an allowlist, so tasks added to the batch manifest
are not silently granted external execution authority. Retries require their
own explicit authorization entry; the current request grants none.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aionq.witness_batch import (batch_status, dispatch_batch, ingest_response,
                                 reconcile_handles, write_witness_markdown)

DEFAULT_MANIFEST = "manifests/godelian_review_batch_v1.json"
DEFAULT_AUTHORIZATION = "manifests/godelian_dispatch_request.json"
DEFAULT_VIEW = "artifacts/witness_batches/godelian-review-v1/WITNESS_NERVE.md"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--authorization", default=DEFAULT_AUTHORIZATION)
    parser.add_argument("--root", default=str(ROOT))
    sub = parser.add_subparsers(dest="command", required=True)

    dispatch = sub.add_parser("dispatch", help="submit every currently dispatchable task")
    dispatch.add_argument("--workers", type=int, default=None)
    dispatch.add_argument("--task", action="append", default=[], metavar="TASK_ID")
    dispatch.add_argument("--retry", action="append", default=[], metavar="TASK_ID")
    dispatch.add_argument("--dry-run", action="store_true")

    sub.add_parser("status", help="fold the append-only journal and show current state")

    ingest = sub.add_parser("ingest", help="apply an explicit terminal response JSON")
    ingest.add_argument("task_id")
    ingest.add_argument("response_json")

    reconcile = sub.add_parser(
        "reconcile",
        help="import already-issued pending handles without an external call",
    )
    reconcile.add_argument("handles_json")

    render = sub.add_parser("render", help="write a Mermaid witness-nerve view")
    render.add_argument("--output", default=DEFAULT_VIEW)
    return parser


def _authorization(
    path: str,
    root: str,
    manifest_path: str,
) -> tuple[list[str], list[str]]:
    root_path = Path(root).resolve()
    authorization = Path(path)
    if not authorization.is_absolute():
        authorization = root_path / authorization
    data = json.loads(authorization.read_text(encoding="utf-8"))
    if data.get("schema") != "hypercomplexbrain.witness_dispatch_request.v1":
        raise ValueError(f"{authorization}: unsupported dispatch request schema")
    if data.get("requested_action") != "dispatch":
        raise ValueError(f"{authorization}: requested_action is not dispatch")
    authorized_manifest = Path(data.get("batch_manifest", ""))
    if not authorized_manifest.is_absolute():
        authorized_manifest = root_path / authorized_manifest
    requested_manifest = Path(manifest_path)
    if not requested_manifest.is_absolute():
        requested_manifest = root_path / requested_manifest
    if authorized_manifest.resolve() != requested_manifest.resolve():
        raise ValueError(
            "dispatch authorization names a different batch manifest: "
            f"{authorized_manifest}"
        )
    tasks = data.get("requested_tasks")
    if not isinstance(tasks, list) or not all(
        isinstance(task, str) and task.strip() for task in tasks
    ):
        raise ValueError(f"{authorization}: requested_tasks must be task ids")
    retries = data.get("authorized_retry_tasks", [])
    if not isinstance(retries, list) or not all(
        isinstance(task, str) and task.strip() for task in retries
    ):
        raise ValueError(
            f"{authorization}: authorized_retry_tasks must be task ids"
        )
    unknown_retries = set(retries) - set(tasks)
    if unknown_retries:
        raise ValueError(
            f"{authorization}: retry tasks are not in requested_tasks: "
            f"{sorted(unknown_retries)}"
        )
    return tasks, retries


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "dispatch":
        allowed, authorized_retries = _authorization(
            args.authorization,
            args.root,
            args.manifest,
        )
        unauthorized_retries = set(args.retry) - set(authorized_retries)
        if unauthorized_retries:
            raise ValueError(
                "dispatch request does not authorize retries for: "
                f"{sorted(unauthorized_retries)}"
            )
        report = dispatch_batch(
            args.manifest,
            root=args.root,
            workers=args.workers,
            retry_task_ids=args.retry,
            task_ids=args.task or None,
            allowed_task_ids=allowed,
            dry_run=args.dry_run,
        )
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 0 if report.ok else 1

    if args.command == "status":
        print(json.dumps(batch_status(args.manifest, root=args.root),
                         indent=2, sort_keys=True))
        return 0

    if args.command == "ingest":
        result = ingest_response(
            args.manifest,
            args.task_id,
            args.response_json,
            root=args.root,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("verification_ok", True) else 1

    if args.command == "reconcile":
        result = reconcile_handles(
            args.manifest,
            args.handles_json,
            root=args.root,
        )
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0

    if args.command == "render":
        destination = write_witness_markdown(
            args.manifest,
            args.output,
            root=args.root,
        )
        print(destination)
        return 0

    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
