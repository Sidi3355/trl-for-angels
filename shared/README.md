# shared/

The only folder both sessions use. The research session writes the artefacts the app needs, and the app
reads them. Neither session edits the other's files.

| File | What it is | Produced by | Plan step |
|---|---|---|---|
| `profile_template.md` | The frozen founder profile template, copied unchanged from `MASTER_PLAN.md` section 10a. The model is trained on this exact format, so the app's render step must match it line for line. | App session (copy only). Read-only for both sessions after that. | 10a |
| `artifacts/rules.json` | The RRF question list (`rrf.rules_`, with `rrf.questions_` details), in rule order. | Research session | B1 |
| `artifacts/model.json` | The production Kev endpoint, the decider input type (`answers` or `profile`), and the exact request it was trained on. | Research session | D2, D3 |
| `artifacts/thresholds.json` | The risk-slider lookup table from val: precision and recall at each threshold, for each target outcome and timeline, with the counts behind them. | Research session | D4 |

## Rules

- `artifacts/` belongs to the research session. The app never writes to it.
- The app reads artefacts from the folder named by its `ARTIFACTS_DIR` setting. Until the real files exist,
  that points at `app/contract/mocks/`, which holds mocks with the same file names and structure.
  Switching to the real files means setting `ARTIFACTS_DIR=shared/artifacts`, with no code changes.
- **Formats:** the plan doesn't define them, so the app session has proposed one JSON Schema per file in
  `app/contract/artifacts/`. The research session should confirm or amend those before exporting, so the
  mocks and the real files stay identical in structure.

## Requested from the research session (pending)

- In `model.json`: the request exactly as trained (question names, instructions, option labels), whether
  the server applies the temperature, the answerer used, how answers are serialised for Kev, and whether
  the endpoint needs an auth header. See `app/contract/artifacts/model.schema.json`.
- If the decider input is `answers`: a way to get Jev answers through TRL itself (for example the pickled
  RRF, to call `rrf.answers([text])`), and the answer serialiser as an importable function or 3 worked examples.
- 3 to 5 real rendered profiles from `data/raw/sample50.jsonl`, so `render.py` can be tested against the
  real training format.
