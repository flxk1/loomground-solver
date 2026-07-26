# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The LLM-interpretation bridge: parse an LLM's stated reasoning into structure
and audit it — the solver catching a hallucinated leap."""
from __future__ import annotations

from loomground_solver import interpret, audit, audit_text, Rule


# ── parser round-trips ───────────────────────────────────────────────────────

def test_parses_facts_rules_and_candidate():
    text = """
    # a small argument
    fact: p
    fact: -q
    fact: a|b

    rule: p, r => s
    claim: s
    """
    interp = interpret(text)
    assert interp["facts"] == {"p", "-q", "a|b"}
    assert interp["candidate"] == "s"
    assert len(interp["rules"]) == 1
    r = interp["rules"][0]
    assert r.id == "r1"
    assert r.conditions == ("p", "r")
    assert r.consequence == "s"


def test_parses_exceptions_and_therefore_and_auto_ids():
    text = """
    fact: p
    rule: p => q ! e1, e2
    rule: q => r
    therefore: r
    """
    interp = interpret(text)
    ids = [rule.id for rule in interp["rules"]]
    assert ids == ["r1", "r2"]
    assert interp["rules"][0].exceptions == ("e1", "e2")
    assert interp["rules"][1].conditions == ("q",)
    assert interp["candidate"] == "r"


# ── sound / hallucinated ─────────────────────────────────────────────────────

def test_sound_argument_is_sound():
    text = """
    fact: p
    rule: p => q
    rule: q => s
    claim: s
    """
    report = audit_text(text)
    assert report["verdict"] == "sound"
    assert report["entailed"] is True
    assert report["consistent"] is True
    assert "s" in report["closure"]


def test_hallucinated_claim_is_unsound_with_reason():
    # premises do not entail the claim — the LLM leaped.
    text = """
    fact: p
    rule: p => q
    claim: z
    """
    report = audit_text(text)
    assert report["verdict"] == "unsound"
    assert report["entailed"] is False
    assert report["unwarranted"] == ["z"]
    assert any("z" in reason and "not entailed" in reason
               for reason in report["reasons"])


# ── consistency / falsification ──────────────────────────────────────────────

def test_inconsistent_premises_flagged():
    text = """
    fact: p
    fact: -p
    """
    report = audit_text(text)
    assert report["consistent"] is False
    assert report["verdict"] == "unsound"
    assert any("inconsistent" in reason for reason in report["reasons"])


def test_falsified_rule_is_reported():
    # antecedent holds, but the consequence is denied by the evidence.
    text = """
    fact: p
    fact: -q
    rule: p => q
    """
    report = audit_text(text)
    assert "r1" in report["falsified"]
    assert report["verdict"] == "unsound"


# ── injected parse callable overrides the built-in ───────────────────────────

def test_injected_parse_callable_overrides_builtin():
    def fake_llm(text):
        return {"facts": {"a"}, "rules": [Rule("x", ("a",), "b")],
                "candidate": "b"}

    interp = interpret("this prose is ignored by the fake parser", parse=fake_llm)
    assert interp["facts"] == {"a"}
    assert interp["candidate"] == "b"
    report = audit(interp)
    assert report["verdict"] == "sound"
    assert "b" in report["closure"]
