---
name: opponent-modeler
description: Model an adversary - their options, payoffs, likely move, and exploitable tendencies. Solver analytic skill wrapping the installed loomground_solver kernel; fails closed without it. Use when the user needs to anticipate a specific adversary or counterparty before choosing a move. Triggers - "model the opponent", "what will they do", "predict their move", "where are they exploitable".
allowed-tools: solver_opponent_model
---

# opponent-modeler

Reason about what another agent will do. Given their available options and the payoffs they
face, the kernel evaluates which move a payoff-driven opponent takes, infers their type from
observed play, and surfaces exploitable tendencies — as a verifiable result, not a guess.

## Run it

Primary path: call `solver_opponent_model` with `{"payoffs":{...},"probabilities":{...}}` —
the same JSON the script reads on stdin; it returns exactly what the script prints.

Shell fallback:

```
echo '{"payoffs":{...},"probabilities":{...}}' | python3 scripts/run.py
```

Delegates to the installed engine; holds no copied logic and exits non-zero if the engine is absent.

## More

- `references/reference.md` - full inputs, semantics, and guardrails.
- `references/eval.json` - what it wraps, determinism, and test status.
