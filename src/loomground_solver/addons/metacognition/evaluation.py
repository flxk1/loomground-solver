# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Deterministic partitioned evaluation for improvement proposals."""
from __future__ import annotations

from dataclasses import replace
from typing import Callable, Iterable, Mapping

from .contracts import (EvaluationCase, EvaluationPartition, EvaluationReport,
                        ImprovementProposal, ProposalStatus)


def evaluate_proposal(proposal: ImprovementProposal,
                      cases: Iterable[EvaluationCase], *,
                      runner: Callable[[ImprovementProposal, EvaluationCase], bool | Mapping]
                      ) -> tuple[ImprovementProposal, EvaluationReport]:
    """Evaluate without mutation; every partition must exist and pass."""
    cases = tuple(cases)
    counts = {part.value: {"total": 0, "passed": 0}
              for part in EvaluationPartition}
    failures = []
    for case in cases:
        raw = runner(proposal, case)
        ok = bool(raw.get("ok")) if isinstance(raw, Mapping) else bool(raw)
        bucket = counts[case.partition.value]
        bucket["total"] += 1
        bucket["passed"] += int(ok)
        if not ok:
            detail = dict(raw) if isinstance(raw, Mapping) else {}
            failures.append({"case_id": case.case_id,
                             "partition": case.partition.value, **detail})
    complete = all(item["total"] > 0 for item in counts.values())
    eligible = complete and not failures
    report = EvaluationReport(
        proposal.proposal_id, len(cases), len(cases) - len(failures), counts,
        tuple(failures), eligible,
    )
    updated = replace(proposal, status=ProposalStatus.EVALUATED,
                      evaluation={
                          "total": report.total,
                          "passed": report.passed,
                          "partitions": counts,
                          "failures": report.failures,
                          "eligible": eligible,
                      })
    return updated, report
