# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The product surface for the vision: narrow an unknown problem's solution by
inference over a federation (reasoning in fingerprint space), with undetermined
structure routed to a bounded escalation set — never guessed."""
from __future__ import annotations

from loomground_solver import fingerprint, narrow


def _prob(forces, node="x"):
    edges = [{"subject": "s", "predicate": "p", "object": node,
              "dimension": d, "polarity": s} for d, s in forces]
    return fingerprint(pairs=[{"id": "i", "edges": edges}], filters=["contradiction"])


def test_narrow_derives_the_accepted_structure_and_escalates_the_rest():
    physics = [
        (_prob([("structural", +1), ("causal", -1)], "beam"), _prob([("structural", +1)], "beam")),
        (_prob([("temporal", +1), ("causal", -1)], "signal"), _prob([("temporal", +1)], "signal")),
    ]
    out = narrow(_prob([("intentional", +1), ("relational", -1)], "record"), physics)
    # the invariant is derived (accepted, auto): the contradiction is resolved
    assert out["solution"]["contradiction/contradiction_count"] == 0.0
    # the domain-bound axis identity could not be pinned -> it escalates, not guessed
    assert "contradiction/tradeoff_axes" in out["escalate"]
    assert out["complete"] is False
    assert 0.0 < out["determinacy"] < 1.0


def test_narrow_is_complete_when_the_federation_pins_everything():
    pairs = [(_prob([("structural", +1), ("causal", -1)], "beam"), _prob([("structural", +1)], "beam"))]
    out = narrow(_prob([("structural", +1), ("causal", -1)], "beam"), pairs)
    assert out["complete"] is True
    assert out["escalate"] == []
    assert out["determinacy"] == 1.0


def test_narrow_pins_nothing_from_an_empty_federation():
    out = narrow(_prob([("structural", +1)], "beam"), [])
    assert out["solution"] == {} and out["escalate"] == []
    # nothing pinned -> NOT complete, even though nothing escalated either
    assert out["determinacy"] == 0.0 and out["complete"] is False
