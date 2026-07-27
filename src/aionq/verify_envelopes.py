"""Verify every committed EvidenceEnvelope.  Exit 1 if any fails.

R4-E.  This is the CI-facing half of the membrane: without it, envelopes are
files nobody reads, which is the ceremonial outcome the round preregistered as
its kill condition.

    python -m aionq.verify_envelopes artifacts
"""

from __future__ import annotations

import sys
from pathlib import Path

from .evidence import load_envelope, verify


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0]) if args else Path("artifacts")
    paths = sorted(root.rglob("*.envelope.json"))
    if not paths:
        print(f"no envelopes under {root}/ -- nothing to verify")
        return 0

    failed = 0
    for path in paths:
        result = verify(load_envelope(path), repo_root=Path.cwd())
        mark = "ok  " if result.ok else "FAIL"
        print(f"{mark} {path}  n_eff={result.effective_n} "
              f"independent={result.independent}")
        for f in result.failures:
            print(f"       FAIL  {f}")
        for w in result.warnings:
            print(f"       warn  {w}")
        failed += not result.ok

    print(f"\n{len(paths) - failed}/{len(paths)} envelopes verified")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
