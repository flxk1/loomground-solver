---
name: analyse-risks
description: Score and rank risks by impact x likelihood and prioritise mitigations, via the kernel's decision methods. Solver analytic skill; fails closed without the kernel. Use when the user has a set of risks to score, rank, or prioritise for mitigation. Triggers - "analyse the risks", "risk matrix", "score these risks", "what to mitigate first".
allowed-tools: solver_analyse_risks
governance:
  grade: L1
  actions:
    - { kind: analyse_risks, risk: low }
    - { kind: release_mitigation_priority, risk: medium, grade: L2 }
  reserved:
    - { kind: release_mitigation_priority, by: workspace_owner }
  prohibited:
    - analyse_without_kernel
  obligations:
    - delegates_to_installed_engine
    - scoring_scheme_shown
  redress:
    - { kind: release_mitigation_priority, by: workspace_owner, overturn: true }
  budget: { usd: 1, iters: 20 }
  on-boundary: fail-closed-without-kernel
---

# analyse-risks

Take a list of risks and turn it into a defensible priority order. Each risk gets an impact and a
likelihood; the kernel scores and ranks them, and proposes mitigations in priority order — with
the scoring scheme shown so the ranking is auditable, not a black box.

## Run it

Primary path: call `solver_analyse_risks` with `{"vectors":{"riskA":[impact,likelihood]}}` —
the same JSON the script reads on stdin; it returns exactly what the script prints.

Shell fallback:

```
echo '{"vectors":{"riskA":[impact,likelihood]}}' | python3 scripts/run.py
```

Delegates to the installed engine; holds no copied logic and exits non-zero if the engine is absent.

The mitigation priority is released only by the workspace owner; until then it is a draft, not a decision.

## More

- `references/reference.md` - full inputs, semantics, and guardrails.
- `references/eval.json` - what it wraps, determinism, and test status.
