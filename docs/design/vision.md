# loomground-solver — VISION & POINTS OF RECORD

The canonical statement of what this solver is for, in product-owner terms.
Written 2026-07-18 as a faithful readback of the design conversation, so any
reviewer (human or a model like Codex) can check the code against the intent.
Nothing here is collapsed or paraphrased away. Companion to the
[operations guide](../guides/operations.md) (how to run it).

---

## A. The vision (the frame everything serves)

1. The fingerprint is **based on the edges** — problem-solution structure compiled
   over the 5D edges, not over surface text.
2. **nD is reasoning.** The extra dimensions are not storage; they are structure
   you *reason over*. The open filter family and the open method family are that nD.
3. The goal is a **large federation of problem-solution fingerprints that narrows
   solutions to *unknown* problems by knowing the fingerprints** — inference over
   structure, never lookup.

## B. Why retrieval is no longer state of the art (the endorsed reframe)

4. Naive kNN RAG is superseded — by agentic reasoning, long-context, and a
   **compilation-stage knowledge layer** that precomputes structure instead of
   fetching raw chunks at runtime.
5. The reasoning frontier is now **generate-and-verify**: test-time compute
   proposes, a verifier checks.
6. Dropping retrieval does not touch the solver's core, which is **verifier +
   structured world model** — retrieval was only ever the *generator slot*, the
   replaceable part.
7. The generator becomes a **reasoning model**, and the fingerprint/graph layer
   **conditions and constrains** it — a prior and a context, not a shelf. No kNN.
8. **The solver IS the verifier** — the scarce, defensible half: symbolic,
   grounded, deterministic, replayable, signable (contract + grounded
   defeasibility + attack-closure). Categorically better than a reward model or an
   LLM judge, on exactly the axis the frontier lacks. In generate-and-verify, **the
   verifier is the moat**.
9. The **federation is a compile-time knowledge layer, not a retrieval index** —
   problem→solution structure compiled offline into a comparable, signed,
   reasoning-ready substrate (fingerprints, edges, contradictions, solver-DAGs,
   defeat relations).
10. **Retention** closes the loop into the current learning paradigm: every
    verified pass/fail is outcome data that steers the generator — but the labels
    are **explained and replayable**, not a scalar reward.
11. The outcome: don't build a retrieval engine. Build the **solver as a verifier
    service behind any generator**, and the **federation as a compile-time layer**
    that conditions the generator and supplies the defeaters the verifier needs.
    Generate with the frontier, verify with the thing only you have, compile ahead
    of time, learn from outcomes.

## C. The four ideas — and the owner's decision on each

12. **#1 — the verifier as a data pump.** Point any frontier model at a problem,
    verify with the solver, keep only verified traces, train a small local
    generator on them; the verifier's pass/fail is the verifiable-reward signal
    (symbolic verifier, not a reward model). Biggest lever; nothing like it exists
    today. → Decision: **"great. How to bring it into the product?"**
13. **#2 — fingerprint the contradiction, not the surface.** Abstract each problem
    to its **invariant/contradiction** and match cross-domain on that — so a legal
    problem can be solved by the structural shape of a physics solution. Solves
    genuinely unknown problems, not near-duplicates. Changes what a fingerprint
    *is*. → Decision: **"fingerprint argumentative / logical relations / negative
    space / etc."**
14. **#3 — return the attack graph, not an answer.** Emit candidates with their
    defeaters to reinstatement closure — the defeasibility structure and where a
    human must choose. The grounded resolver is half; the missing piece is
    **producing the defeaters**, not consuming one candidate. → Decision: **"do it."**
15. **#4 (the owner's new idea) — automatic decision-making pulls a *deterministic
    decision space* from the LLM.** The machine gets a bounded space; the LLM picks
    *within* it, never invents it.

## D. The syntheses that were accepted

16. **#3 and #4 are the same object.** The attack graph *is* the deterministic
    decision space. `decision_space()` returns `{accepted, undecided, rejected}`:
    `accepted` = auto-safe, `undecided` = the *only* set the LLM/human may choose
    within, `rejected` = invalid/defeated with reasons. Non-determinism is **fenced
    by construction** — the seam RVND's verdict engine consumes.
17. **Productizing #1 without building a corpus.** RVND's **Ed25519 signed audit
    chain** already records every governed run (generator proposed → solver
    verified → verdict). That signed chain *is* the labeled, replayable dataset.
    Add **one export** (verified traces → training pairs), feed Versum's local
    Phi/Qwen backend, ship as an **autonomy-graded background agent** (harvest →
    train adapter → propose swap on gate). No new product — a capture+train loop
    riding the chain that already exists.
18. **The fingerprint's three layers** (before generalization): (a) **logical
    form** — polarity/predicate/modality/quantification (universal_form); (b)
    **attack-graph shape** — who defeats whom, reinstatement (the decision_space
    *topology*, not just nodes); (c) **negative space** — applicable-but-unfired
    rules, untriggered exceptions, reported gaps. Two problems are alike **not only
    in what's present but in what's absent** (Gentner & Kuhn: the deciding object
    is the one that isn't there). Matching on negative space catches the
    confident-wrong analogy *at the fingerprint stage*.
19. **The demanded generalization: no hard-coded layers — an OPEN set of pluggable
    filters (lenses).** Negative space is one filter, argument-types another,
    statistics another, and **you register your own in one line**. That is nD as an
    open family. Shipped lenses: `logical_form`, `attack_topology`,
    `negative_space`, `argument_types`, `statistics`. Any registered filter
    participates in `distance` (generic numeric-L1 + set-Jaccard, or its own
    comparator); facets can be weighted or dropped; version-mismatched fingerprints
    refuse to compare (A2); domain filters live in adapters, not the core.

## E. The fingerprint in NORMAL MODE, and its negative-space complement

20. In **normal mode the fingerprint *is* the edges** — the `logical_form` lens
    over the plain 5D edges: the histogram of structural / causal / intentional /
    temporal / relational relations (plus deontic modality). This is "the *present*
    relations," the base/default fingerprint, and it is exactly point 1
    (fingerprint *based on the edges*).
21. **Negative space is the complement of that base** — not what the edges say but
    what is *absent-yet-relevant*: applicable-but-**unfired** defeaters,
    **untriggered** exceptions, reported **gaps**. Normal-mode edges + negative
    space are the two halves: what is present and what is pointedly missing.

## F. The reasoning-methods strand — "line up more methods of reasoning"

Requested from **philosophy, methodology, logic, rationalist decision theory,
mathematics, data science**. Built as the open `METHODS` registry (rule-nD,
19 methods, `register_method(...)` for more; methods grouped by kind —
`inference` / `critique` / `decide`):

22. **Logic** — `modus_ponens`, `modus_tollens`, `hypothetical_syllogism`,
    `disjunctive_syllogism`.
23. **Philosophy** — `abduction` (inference to the best explanation),
    `analogical_inference`.
24. **Methodology** — `falsification`, `consistency`, `hypothetico_deductive`.
25. **Rationalist Decision Theory** — `expected_utility`, `maximin`, `maximax`,
    `hurwicz`, `minimax_regret`, `satisficing`.
26. **Mathematics** — `pareto`, `lexicographic` (the mathematical-reasoning
    methods).
27. **Data Science** — `bayesian_update`, `inductive_generalization`.
28. The registry is **open in the same way the fingerprint filters are** — nD as an
    open family on the *reasoning* side, mirroring the filter registry on the
    *fingerprint* side.

## G. Subsumption — the rule-reasoning spine

29. **`subsumption.py`**: a `Rule` is **Tatbestand → Rechtsfolge + Ausnahme
    (exception) + deontic**. Deterministic-first `holds` / `subsume` (the
    Tatbestand→facts step), with a **`judge` port** for model escalation only where
    the deterministic step cannot decide.
30. **End-to-end rule reasoning**: `forward_chain` (apply), `to_norms`, and
    `solve_rules` (extract-plug → subsume → apply → resolve) — subsumption feeding
    the grounded resolver, so rule reasoning and defeasible reasoning are one
    pipeline, not two.

## H. The panel verdict and the "reasoning" bar

31. **Panel** (Gentner, Aamodt, Altshuller, Kuhn, Dung, LeCun, Kleppmann).
    Adoptions: **A1** retrieval proposes / contract disposes — re-derive every
    candidate, escalate if ungroundable; **A2** version-pin every fingerprint,
    incomparable pairs escalate (never fabricate a cross-schema distance); **A3**
    cheap MAC recall filter + explicit FAC structural alignment emitting **labelled
    correspondences**; **A4** a failed re-derivation *is* an attack edge, run
    grounded over the closed set; the **4th R — RETAIN** repaired adaptations with
    explanations = the replayable training set. Rejections: "placement is
    inference," "nearness is trust," "one metric adjudicates," "sign a learned
    float as truth."
32. **nD reasons, but the bar is earned.** Placing a problem in the topography is
    inferential *only if* the answer can exhibit the labelled base→target
    correspondences (Gentner) or the defense graph to reinstatement closure (Dung).
    Bare placement ≠ reasoning. Operating frame: **Generate → Verify → DECIDE
    (rational operation) → sign / replay.**

## I. Hard constraints (non-negotiable)

33. **The fingerprint stays.** Already worked on; not up for redesign.
34. **No RAG.** "We will not build another stupid RAG." `distance()` is a cheap
    recall filter only — never a trust signal, never the reasoning.
35. **Universal, standalone.** One solver — epistemic *or* rules *or* whatever —
    that both the 5D+nD Graph (Versum) and RVND **import without owning**;
    governance and corpus arrive only through injected ports. The
    dependency-inversion gate passing *is* the definition of "universal."
36. **RVND imports it and loses no functionality**; the KG imports the same package
    symmetrically.
37. **Work in the folder. No archives** — no tarballs.

---

## Build status (honest, at time of writing)

Green build: **269 solver tests + 10 RVND-integration tests**, all passing; the
dependency-inversion gate (universality) still green with every addition below.

Built this row (supervised loops, each verified, then adversarially reviewed):

- **Federation over negative space (18c).** `federation.py` now reasons over the
  set-valued negative-space coordinates as well as the numeric ones: the *count* of
  defeaters/gaps a solution closes is structural and transfers; the *identity* of a
  specific gap escalates unless the federation systematically agrees. Guarded
  against incomparable fingerprint **shapes** (a facet on one side, absent on the
  other, is no longer silently read as zero — it raises, A2).
- **#2 — the `contradiction` filter (13).** Abstracts a problem's edges to a
  domain-neutral invariant (opposing forces on a shared node). The shape
  coordinates (`contradiction_count`, `tradeoff`) are dimension-agnostic and
  transfer across domains; the `tradeoff_axes` / `dimension_tension` are
  domain-bound and escalate. Proven: a **legal** problem's solution invariant is
  derived from a federation of **physics** pairs (cross-domain, by inference).
- **The product surface `narrow()` (Loop 3).** Takes an unknown problem's
  fingerprint + a federation, derives the solution structure, and routes the
  undetermined coordinates to a bounded escalation set (decision-space discipline).
  `complete` requires the whole structure pinned (determinacy 1.0), never merely
  "nothing escalated."
- **#1 — the data-pump productization (12, 17).** `adapters_rvnd/datapump_rvnd.py`
  (RVND side, not the universal core): reads the Ed25519 signed audit chain, maps
  events to `harvest` records, re-checks signatures, and emits training data + an
  **autonomy-graded** swap proposal (only an autonomous grade auto-applies; the
  default grade escalates). Injectable chain-reader + verifier; proven against a
  faked chain.
- Earlier in the session: the LLM-interpretation bridge (`interpret.py`) and the
  core data-pump export (`datapump.py`).

Open / next (rough priority): preferred/stable argumentation semantics (reserved,
NP-hard); specialisation-by-configuration bundles; a production Ed25519 replay
verifier wired into the data-pump (the adapter's default check is presence-only by
design). The V1 false-analogy benchmark and the retrieval→A1 wiring are **declined**
by the owner (no RAG).
