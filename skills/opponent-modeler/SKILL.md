---
name: opponent-modeler
description: Model an adversary - their options, payoffs, likely move, and exploitable tendencies. Solver analytic skill wrapping the installed loomground_solver kernel; fails closed without it. Use when the user needs to anticipate a specific adversary or counterparty before choosing a move. Triggers - "model the opponent", "what will they do", "predict their move", "where are they exploitable".
allowed-tools: solver_opponent_model
governance:
  grade: L1
  actions:
    - { kind: model_opponent, risk: low }
    - { kind: release_opponent_model, risk: medium, grade: L2 }
  reserved:
    - { kind: release_opponent_model, by: workspace_owner }
  prohibited:
    - model_without_kernel
  obligations:
    - delegates_to_installed_engine
    - result_verifiable_not_guessed
  redress:
    - { kind: release_opponent_model, by: workspace_owner, overturn: true }
  budget: { usd: 1, iters: 20 }
  on-boundary: fail-closed-without-kernel
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

The opponent model is released only by the workspace owner; until then it is a draft, not a decision.

## More

- `references/reference.md` - full inputs, semantics, and guardrails.
- `references/eval.json` - what it wraps, determinism, and test status.
