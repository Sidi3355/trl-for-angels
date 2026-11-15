# Draft pull request: Sidi3355/think-reason-learn `feature/decision-combiner` → Vela-Research/think-reason-learn `main`

**Title:** RRF: `combiner="decision"`, a decision model as the final step

**Not opened yet.** Open it as a draft once the owner says so, after adding the results link
(marked TODO below). The body follows the repo's pull request template.

---

## Summary

Random Rule Forest can now hand its final step to a **decision model** (Jev, Kev on your own
server, or any model behind TypeSafe's System One API) instead of weighing the answers with an
elastic net or counting them in a vote.

```python
kev = LLM("kev", base_url="http://127.0.0.1:8009/v1/systemone", kind="decision")
model = RRF(task=..., generator=..., answerer="jev",
            combiner="decision", combiner_model=kev,
            combiner_question="Will this founder's company succeed?")
```

**How it works.** For each sample, RRF writes its answers as text, one line per rule, best
F-beta first (`"<question> yes"`, `"no"`, or `"unknown"` when unanswered). It asks the decision
model one yes/no question about that text, and the model's probability is the score. `fit`
tunes the threshold with `best_threshold`, as the other combiners do.

**Why.** Decision models already answer RRF's questions. Making one the final step lets it
combine answers in ways a linear model can't, and lets it be fine-tuned on exactly the text it
reads: `think_reason_learn.rrf.answers_text` builds that text, for training and prediction
alike.

**Details**

- New settings `combiner_model` and `combiner_question`, stored unchanged. Both `combiner` and
  `combiner_model` are checked before any paid call. The other combiners ignore
  `combiner_model`, so grid searches over `combiner` still work.
- Every scored question goes to the decision model (the best `max_rules` if set): the same
  ranked set the elastic net starts from.
- New fitted attribute `decision_question_`, saved and loaded. Prediction asks the answerer,
  then the decision model, which reports usage under the role `"combiner"`.
- `estimate_cost` counts the decision model's calls. They're counted at their most, because
  identical answer texts are asked once and that only shows after answering; every other
  role's count stays exact. This adds an `rrf-decision` case to
  `tests/core/test_estimate_cost.py`, next to the existing at-most cases.
- The threshold is tuned on the samples `fit` scores. If the decision model was trained on
  those samples it's optimistic; the docs say to tune it on held-out data then.

**Fix (System One).** A decision model on a server without a key (`LLM(..., base_url=...,
kind="decision")` with no `api_key`) was called with `Authorization: Bearer ` (empty), which
the HTTP client rejects as illegal, so every call failed. This included any saved and
reloaded model, since saving drops keys. With no key, the header is now left out.

**Results.** TODO: link the comparison of this combiner (base and fine-tuned Kev-0.6B) with
the elastic net, the vote and an XGBoost control, on generated founder data, once it's public.

**Checked:** with a real Kev-0.6B server as both answerer and decision model on a toy set,
`fit` and `predict_proba` returned probabilities (founders with an exit 0.50–0.52, without
0.35–0.42), and the tuned threshold separated them.

**FYI, unrelated to this change:** `sphinx-build -W` already fails on `main` from about 116
warnings in scikit-learn's inherited docstrings (`verifiable_rl`, metadata routing). This PR
adds none, and CI doesn't build the docs.

## Type of change
- [x] feat
- [x] fix
- [ ] refactor
- [x] docs
- [x] test
- [ ] chore

## Checklist
- [x] Tests added/updated: `tests/rrf/test_decision.py` (new), `rrf-decision` in the shared
      contract tests (`check_classifier`), `tests/core/test_estimate_cost.py`, and a System One
      wire test for the keyless server
- [x] Lint and type-check pass: `poetry check --lock`, `ruff check`, `ruff format --check`,
      `pyright` (strict, 0 errors), `pytest` (404 passed, 2 skipped, offline)
- [x] Docs updated: `docs/source/getting_started/decision_combiner.rst` (linked from the
      index), and two `changelog.rst` lines

## Related issues
None filed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_018ARa1i23b9dWrmykLT4KM7
