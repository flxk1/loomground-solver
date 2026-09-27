---
name: estimate-liability
description: Estimate the conditional probability of liability (or other adverse outcome) as a calibrated range, given evidence factors. Solver analytic skill wrapping the kernel's Bayesian method; an organisational estimate, not legal advice. Use when the user wants a calibrated probability of liability or another adverse outcome from known evidence factors. Triggers - "how likely is liability", "exposure probability", "odds of an adverse finding".
allowed-tools: solver_estimate_liability
governance:
  grade: L1
  actions:
    - { kind: estimate_liability, risk: low }
    - { kind: release_liability_estimate, risk: medium, grade: L2 }
  reserved:
    - { kind: release_liability_estimate, by: workspace_owner }
  prohibited:
    - estimate_without_kernel
    - present_estimate_as_legal_advice
  obligations:
    - delegates_to_installed_engine
    - assumptions_shown
    - calibrated_range_reported
  redress:
    - { kind: release_liability_estimate, by: workspace_owner, overturn: true }
  budget: { usd: 1, iters: 20 }
  on-boundary: fail-closed-without-kernel
---

# estimate-liability

Turn a set of evidence factors into a calibrated estimate of how likely an adverse outcome is.
The kernel updates a prior on each factor's likelihood and reports a range, with the assumptions
that move it — so the number is defensible, not asserted.

## Run it

Primary path: call `solver_estimate_liability` with `{"prior":{...},"likelihoods":{...},"evidence":"e"}` —
the same JSON the script reads on stdin; it returns exactly what the script prints.

Shell fallback:

```
echo '{"prior":{...},"likelihoods":{...},"evidence":"e"}' | python3 scripts/run.py
```

Delegates to the installed engine; holds no copied logic and exits non-zero if the engine is absent.

The estimate is an organisational estimate, not legal advice, and is released only by the workspace owner.

## More

- `references/reference.md` - full inputs, semantics, and guardrails.
- `references/eval.json` - what it wraps, determinism, and test status.
