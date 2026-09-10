---
name: probability-tracker
description: Maintain and update a calibrated probability over an uncertain hypothesis as evidence arrives (Bayesian). Solver analytic skill wrapping the loomground_solver kernel; fails closed without it. Use when the user holds an uncertain hypothesis and wants its probability tracked and updated as evidence arrives. Triggers - "track the odds", "update the probability", "what's the likelihood now", "chances given this evidence".
allowed-tools: solver_probability
---

# probability-tracker

Keep an honest running estimate of how likely something is. Supply a prior and the evidence
likelihoods; the kernel's Bayesian-update method returns the posterior with its working — a
calibrated probability, not a number pulled from the air.

## Run it

Primary path: call `solver_probability` with `{"prior":{...},"likelihoods":{...},"evidence":"e"}` —
the same JSON the script reads on stdin; it returns exactly what the script prints.

Shell fallback:

```
echo '{"prior":{...},"likelihoods":{...},"evidence":"e"}' | python3 scripts/run.py
```

Delegates to the installed engine; holds no copied logic and exits non-zero if the engine is absent.

## When to use

- "What are the chances now, given this evidence?"
- Keeping a running estimate that updates as observations come in.

Do NOT invent a prior, and do NOT assert a probability the evidence does not support — an absent
prior is made explicit, never guessed.

## More

- `references/reference.md` - full inputs, semantics, and guardrails.
- `references/eval.json` - what it wraps, determinism, and test status.
