---
name: strategic-analysis
description: Analyse a competitive/adversarial position - moves, threats, opportunities, plan - via the kernel's decision methods and possible-worlds. Solver analytic skill; fails closed without the kernel. Use when the user needs a competitive or adversarial position analysed into moves, threats, opportunities, and a plan. Triggers - "analyse this position", "what's my best move", "what are the threats", "think through the strategy".
allowed-tools: solver_strategy
---

# strategic-analysis

Think through a competitive position and come out with a defended recommendation. Given the moves
open to each side and the payoffs at stake, the kernel evaluates options under several decision
rules, plays them out across possible worlds, and reports the strongest line with the threats and
opportunities it turns on.

## Run it

Primary path: call `solver_strategy` with `{"payoffs":{...}}` —
the same JSON the script reads on stdin; it returns exactly what the script prints.

Shell fallback:

```
echo '{"payoffs":{...}}' | python3 scripts/run.py
```

Delegates to the installed engine; holds no copied logic and exits non-zero if the engine is absent.

## More

- `references/reference.md` - full inputs, semantics, and guardrails.
- `references/eval.json` - what it wraps, determinism, and test status.
