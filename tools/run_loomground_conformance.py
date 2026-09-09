#!/usr/bin/env python3
"""Run Solver through the language repository's neutral conformance kit."""
from __future__ import annotations

from loomground_governance import run_conformance
from loomground_solver import loomground


def main() -> int:
    report = run_conformance(loomground)
    for failure in report.failures:
        print(f"[FAIL] {failure['name']}: {failure['error']}")
    print(f"{report.passed}/{report.total} vectors passed")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
