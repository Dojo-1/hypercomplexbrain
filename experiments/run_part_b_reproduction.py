"""QSigma-R6O: recompute Part B on this platform. Exit 0 only on REPRODUCED.

    python experiments/run_part_b_reproduction.py [report-path]

Prints one line beginning `R6O_REPORT ` carrying the full JSON report, so the
result is recoverable from a CI log even if no artifact is uploaded.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aionq.part_b_reproduction import reproduce  # noqa: E402


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    report = reproduce(ROOT)
    text = json.dumps(report, sort_keys=True, allow_nan=False)
    print("R6O_REPORT " + text)
    if argv:
        path = Path(argv[0])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
                        encoding="utf-8", newline="\n")
    print(f"verdict: {report['verdict']}")
    return 0 if report["verdict"] == "REPRODUCED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
