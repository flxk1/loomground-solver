---
name: litigation-risk-assessor
description: Assess dispute risk - quantify exposure, weigh merits, recommend settle or fight - via the kernel's decision theory. Solver analytic skill; an organisational assessment, not legal advice. Use when the user faces an actual or threatened dispute and needs exposure quantified or a settle-or-fight recommendation. Triggers - "assess litigation risk", "what's our exposure", "settle or fight", "weigh the merits".
allowed-tools: solver_litigation_risk
governance:
  grade: L1
  actions:
    - { kind: assess_litigation_risk, risk: low }
    - { kind: release_litigation_assessment, risk: medium, grade: L2 }
  reserved:
    - { kind: release_litigation_assessment, by: workspace_owner }
  prohibited:
    - assess_without_kernel
    - present_assessment_as_legal_advice
  obligations:
    - delegates_to_installed_engine
    - decision_rule_shown
  redress:
    - { kind: release_litigation_assessment, by: workspace_owner, overturn: true }
  budget: { usd: 1, iters: 20 }
  on-boundary: fail-closed-without-kernel
---

# litigation-risk-assessor

Weigh a dispute the way a decision analyst would: enumerate the outcomes (win / lose / settle at
various points), attach a value and a probability to each, and let the kernel compute the
expected value and the downside, then recommend a line — with the rule that produced it shown.

## Run it

Primary path: call `solver_litigation_risk` with `{"payoffs":{...},"probabilities":{...}}` —
the same JSON the script reads on stdin; it returns exactly what the script prints.

Shell fallback:

```
echo '{"payoffs":{...},"probabilities":{...}}' | python3 scripts/run.py
```

Delegates to the installed engine; holds no copied logic and exits non-zero if the engine is absent.

The assessment is an organisational assessment, not legal advice, and is released only by the workspace owner.

## More

- `references/reference.md` - full inputs, semantics, and guardrails.
- `references/eval.json` - what it wraps, determinism, and test status.
