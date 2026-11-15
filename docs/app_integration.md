# Research → app: what changed and what the app needs (2026-11-14, updated 2026-11-15)

For the app session (`app-track`), passed on by the owner. Checked against `app-track` at
`f7b828b`. Plan changes behind this are in `MASTER_PLAN.md` section 0.

## Already fine

- **The founder template.** `app/backend/screener/template.py` renders and parses every line
  exactly as MASTER_PLAN section 10 specifies, with the same allowed values as the research
  validator (`research/validate.py`). No change needed.
- **The three artefacts.** `research/export_artifacts.py` writes `rules.json`, `thresholds.json`
  and `model.json` to `shared/artifacts/` and validates each against the app contract's schemas
  before writing. **The real files are there now (2026-11-15)**: set
  `ARTIFACTS_DIR=shared/artifacts`. The decider reads TRL's answers (`decider_input:
  "answers"`, D2). `rules.json` holds **40 questions** (the best by F0.5 on train, best first; TRL's
  `max_rules=40`, decided 2026-11-14), so the app's answerer asks Kev 40 questions per founder.
  If the D2 winner is C4 (Kev reads the profile directly), the app doesn't answer questions at
  all: `model.json → decider_input` (`"answers"` or `"profile"`) says which.

## What the app needs to change

1. **The answerer is Kev, not Jev.** TypeSafe has no free tier and the project has no budget,
   so base **Kev-0.6B** (`jaredpalmer/kev-0.6b`, self-hosted, fp32) answers the rules, through TRL.
   `JevAnswerer` becomes a Kev answerer. `model.json → answerer.spec` names it. With TRL:

   ```python
   from think_reason_learn.llm import LLM, LLMSession, YesNoQuestion
   kev = LLM("kev-0.6b", base_url=f"{ANSWERER_URL}/v1/systemone", kind="decision")
   qs = {r["id"]: YesNoQuestion(r["question"]) for r in rules["rules"]}
   [row] = await LLMSession().answer([kev], [profile_text], qs, role="answerer")
   p_yes = [row[r["id"]].probability() if row[r["id"]] else float("nan") for r in rules["rules"]]
   ```

   A local Kev server needs no key; no key header is sent (fixed in our TRL fork).
2. **Turn answers into Kev's input with TRL's own function**, so the app sends exactly what Kev
   was trained on: `think_reason_learn.rrf.answers_text(questions, p_yes)`, with questions in
   `rules.json` order. It matches `answer_serialisation` (binary, 0.5, `"{question} {answer}"`,
   newline-separated), plus one case the app's `serialise.py` lacks: an unanswered rule (NaN)
   becomes `"<question> unknown"`. Both functions come from our TRL fork:
   `pip install "think-reason-learn @ git+https://github.com/Sidi3355/think-reason-learn@feature/decision-combiner"`.
3. **Temperatures are applied by the client.** `model.json → temperature.applied_by` is
   `"client"`, with one temperature for `outcome` and one for `years`. Serve the production
   model raw (`KEV_TEMPERATURE=1.0`), then per question: `p_i ← p_i^(1/T) / Σ_j p_j^(1/T)`. This is
   the same as dividing the logits by T.
4. **Send the questions from `model.json`, word for word, descriptions included.**
   `request.questions` holds the real instructions and each option's description (the
   `criteria` values) that the production model was trained with. Send `criteria` as given, not
   with `null` values: without the descriptions the same model's answers move by up to 0.18
   (on val it put 35% on "shut down" instead of 52%). Through TRL, use our fork at `d9d1380` or
   later and `ChoiceQuestion(text, labels, descriptions)`; older TRL sends empty criteria.
5. **kev.serve's response** (what `KevDecider` was waiting on), from `/v1/systemone`:

   ```json
   {"model": "kev-latest",
    "answers": {"outcome": {"type": "choice", "choice": "shut down", "confidence": 0.21,
                            "probabilities": {"shut down": 0.47, "under $50M": 0.2, "...": 0.1}},
                "years":   {"type": "choice", "choice": "5-8", "probabilities": {"...": 0.3}}},
    "usage": {"input_tokens": 101, "output_tokens": 161}, "latency_ms": 495}
   ```

   Read `answers.<id>.probabilities`, then apply the temperatures.
6. **Two Kev servers, on the owner's PC for the demo.** Hugging Face Spaces that run code
   now need a paid plan, so `kev_server/serve.py` runs on the owner's Windows PC behind a free
   Cloudflare tunnel: base Kev at `<tunnel address>/answerer/v1/systemone` (the answerer) and the
   production model at `<tunnel address>/decider/v1/systemone` (raw: apply the temperatures).
   Both need `Authorization: Bearer <KEV_API_KEY>`; set the same key on the backend. The tunnel
   address (`https://<words>.trycloudflare.com`) changes each time it starts, so the backend should
   read it from an environment variable rather than from `model.json`: for example `KEV_URL`
   (the bare tunnel address), which, when set, overrides `model.json → endpoint` for both
   paths. A restart is then one Railway variable to paste, with no new artefact. `GET /health` reports
   readiness, and whether the decider is still base Kev standing in. Expect a few seconds per
   founder on CPU; keep the demo cache as the backup. `model.json → endpoint.base_url` is a
   placeholder (`https://replace-with-tunnel.trycloudflare.com/decider`), so `KEV_URL` is
   needed. The PC server loads the production model with
   `DECIDER_MODEL=Sidi3355/trl-for-angels-kev-prod` (`kev_server/README.md`).
7. **Show each target's probability, never a single "predicted outcome".** Half of all founders
   shut down, so "shut down" is the most likely band for every val founder; the information is
   in P(outcome ≥ target). The probabilities are timid: on val, P($500M or more) ranges from
   0.10 to 0.37 (20% got there), so present them against the base rate.
8. **One empty combination:** no val founder reached $1B within 5 years. Its table in
   `thresholds.json` has `n_positive: 0`, so its precision and recall are all 0 and mean
   nothing. Show "not enough data" whenever `n_positive` is 0.

## Optional

- **Risk presets.** The research table (`results/experiments/04_production_model/<stage>/`)
  suggests advance thresholds at TRL's F0.5-, F1- and F2-best (conservative, balanced,
  aggressive), and pass thresholds that turn away at most 5%, 10% or 20% of the founders who
  succeeded. `thresholds.json` carries the full table, so the app can keep its own rule.
