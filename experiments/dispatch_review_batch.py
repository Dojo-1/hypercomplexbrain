#!/usr/bin/env python3
"""Dispatch, resume, ingest and visualise the Godelian-1 witness batch.

The trigger is asynchronous.  ``dispatch`` records returned conversation URLs
and exits; it does not claim that this process will collect a future verdict.
A terminal response exported from the agent conversation is applied explicitly
with ``ingest``.

Examples
--------

Set the token in the shell environment without placing its value on this command
line, then:

    PYTHONPATH=src python3 experiments/dispatch_review_batch.py dispatch
    PYTHONPATH=src python3 experiments/dispatch_review_batch.py status
    PYTHONPATH=src python3 experiments/dispatch_review_batch.py render
    PYTHONPATH=src python3 experiments/dispatch_review_batch.py ingest \
        s7-deterministic-recompute response.json

A declined or failed task is retried only when named explicitly:

    PYTHONPATH=src python3 experiments/dispatch_review_batch.py dispatch \
        --retry s7-deterministic-recompute
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

from aionq.witness_batch import (batch_status, dispatch_batch, ingest_response,
                                 write_witness_markdown)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = "manifests/godelian_review_batch_v1.json"
DEFAULT_VIEW = "artifacts/witness_batches/godelian-review-v1/WITNESS_NERVE.md"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--root", default=str(ROOT))
    sub = parser.add_subparsers(dest="command", required=True)

    dispatch = sub.add_parser("dispatch", help="submit every currently dispatchable task")
    dispatch.add_argument("--workers", type=int, default=None)
    dispatch.add_argument("--retry", action="append", default=[], metavar="TASK_ID")

    sub.add_parser("status", help="fold the append-only journal and show current state")

    ingest = sub.add_parser("ingest", help="apply an explicit terminal response JSON")
    ingest.add_argument("task_id")
    ingest.add_argument("response_json")

    render = sub.add_parser("render", help="write a Mermaid witness-nerve view")
    render.add_argument("--output", default=DEFAULT_VIEW)
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "dispatch":
        report = dispatch_batch(
            args.manifest,
            root=args.root,
            workers=args.workers,
            retry_task_ids=args.retry,
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
