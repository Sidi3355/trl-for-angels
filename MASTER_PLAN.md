# Master plan: calibrated deal-screening agent for angel investors

Context file for Claude Code. It records every decision already made for this project. Treat the decisions as settled unless the user changes them. Items marked **VERIFY** were checked in the source code or docs but not run, so confirm each one with a small test before building on it.

## 0. Amendments (newest first; these override the sections below)

- **2026-11-14 · Zero budget: Kaggle replaces Modal, and Kev-0.6B is the answerer (user decision).** Nothing may cost money. All GPU work (serving Kev to answer TRL's questions, and fine-tuning) runs in Kaggle notebooks on a free T4, in fp32 because the T4 has no bf16, with Kev's server and TRL in the same notebook. Kev-0.6B (`jaredpalmer/kev-0.6b`) is both the answerer and the learn stage: Kev-4B doesn't fit a 16 GB T4 in fp32, and Kev-0.8B's Qwen3.5 kernels may not run on a T4. Wherever this plan says Modal, read Kaggle, and section 6's `--dtype bf16` becomes `--dtype fp32`. Serving Kev for the app (free CPU such as a Hugging Face Space, or cached demo founders) is decided at E1. The generator and the app's agent use the user's existing Claude API credits. Notebooks live in `kaggle/` and are built by `kaggle/build_notebooks.py`.
- **2026-11-14 · Kev fine-tuning command (VERIFY correction).** Section 6's `kev.train` command is incomplete. (1) `--max_state` defaults to 384 tokens and Kev silently drops longer records, which removes every C3 state (about 1.5–3k tokens), so pass `--max_state 4096`. (2) Kev's own fine-tune recipe copies the checkpoint's architecture into the command (`--base`, `--base_revision`, `--lora`, `--head_dim`, `--lora_targets`, `--option_isolation`, `--special_embeddings`, `--weights_dtype`, `--p_none_pair`); `kaggle/a3_check.py` builds it from the checkpoint's metadata. Kev caps a fine-tune's learning rate at 5e-5, so 2e-5 stands. Also, `kev-0.6b` ships uncalibrated (temperature 1.0).

- **2026-11-14 · Kev replaces Jev as the answerer (user decision).** TypeSafe has no free tier, so every answer-based condition uses a self-hosted base Kev as the answerer, held constant across conditions (the fallback section 3 already allowed). Wherever sections 4–9 say Jev answers the questions (the answer matrix, B2, the app's answer step, the demo cache, the allowed claims), read "the Kev answerer". No TypeSafe key is needed. The answerer is Kev-0.6B (next amendment up).
- **2026-11-14 · TRL spec for a Kev endpoint (VERIFY resolved).** `LLM("kev-0.6b", base_url="http://<host>:8009/v1/systemone", kind="decision", api_key="local")`. `"systemone:..."` is not a TRL provider and would route as an OpenAI chat model. `base_url` must be the full `/v1/systemone` URL, and `api_key` must be non-empty because TRL always sends `Authorization: Bearer <key>`. Checked with one call through TRL's `LLMSession`.
- **2026-11-14 · Kev CLI flags (VERIFY resolved).** Every flag in the section 6 commands exists in Kev at commit `2074cc4`.

## 1. What we're building

A hackathon project (Autonomous Agents track, about 2 days) with two halves:

1. **Research:** with TRL's think and reason steps held fixed, which **learn stage** (the final classifier) gives the most accurate, best-calibrated founder-success decisions?
2. **Product:** a mobile-first deal-screening agent for angel investors. It combines the investor's own knowledge with web research on a founder, runs TRL's questions, and uses a calibrated Kev model to **advance, escalate or pass**, with investor-tunable controls.

The pitch: angels screen alone, without analysts. The agent researches and decides, and calibration is what makes its autonomous actions safe.

## 2. Key components (background)

- **TRL (Think, Reason, Learn):** `github.com/Vela-Research/think-reason-learn`, Vela Research's open-source library.
  - **Think:** a generator LLM writes yes/no questions.
  - **Reason:** an answerer answers them for every sample, giving an answer matrix of P(yes).
  - **Learn:** a classical model (elastic net, vote, tree) turns the answers into a prediction.
  - All six methods are scikit-learn classifiers. We use **RRF (Random Rule Forest)**: about 100 generated questions, combined by an elastic-net logistic regression by default.
  - Its relevant public API:
    - `RRF(task=..., generator=..., answerer=...)`
    - `.fit(X, y)`, `.predict_proba(X)`
    - `.answers(X)`, which returns a DataFrame of P(yes) with one column per question (rule) and one row per sample
    - `.questions_` (a DataFrame) and `.rules_` (a tuple of question strings)

    `X` is a list of texts and `y` a list of labels. Models are given as `"provider:model"` strings, or `"jev"`.
- **Jev:** TypeSafe's closed "System One" decision model. It returns calibrated probabilities over the options you define, with no text output. It's TRL's default answerer, and needs a TypeSafe API key.
- **Kev:** `github.com/jaredpalmer/kev` (Apache-2.0), an open reconstruction of Jev's design.
  - **Architecture:** a Qwen base model with a rank-16 LoRA and a pointer head. The head scores each option's `</opt>` hidden state against the question's `<decide>` hidden state, then applies a softmax and a fitted temperature.
  - **API:** serves TypeSafe's `/v1/systemone` contract.
  - **Checkpoint we use:** `jaredpalmer/kev-0.6b`, on `Qwen/Qwen3-0.6B-Base`. The Qwen3 base is attention-only, which suits interp.

## 3. Confirmed decisions

- **Track:** Autonomous Agents.
- **Data:** generated with Adaption in **instruction format** (instruction / input / output). The output holds two lines, `outcome:` and `years:`. Profiles are grounded in real founders where possible, and the dataset prompt is in section 10.
- **Information cutoff:** founding date. Profiles contain only what was true on the day the company was founded. The same rule applies to the research agent and to model inputs. Post-founding investor notes are shown in the memo but never fed to the model.
- **Research label:** "yes" if the outcome is `$500M-$1B` or `over $1B`, otherwise "no". That's about 20% positives.
- **Answerer for every answer-based condition:** base Kev-0.6B (self-hosted on Kaggle), held constant across conditions. Changed from Jev on 2026-11-14 because TypeSafe has no free tier and the project has no budget (section 0).
- **Kev is not fine-tuned as the answerer.** The sub-questions are too factual for fine-tuning to help. Kev is used as the **learn stage** instead.
- **Fine-tuning is done by hand,** from the released checkpoint with `--init_from`. Adaption credits go to data generation only, not to fine-tuning.
- **XGBoost control included,** to separate "Kev helps" from "nonlinearity helps".
- **TRL fidelity is a hard requirement.** Every test and research run goes through TRL's real pipeline (section 4b), and the Kev learn stage is built as a TRL-native extension in a fork of TRL, so the research feeds directly into TRL's development as a pull request.
- **No claims about real-world accuracy.** The data is generated. VCBench (request access from vcbench.com) is the future real test.
- **Product:** a mobile-first PWA (Next.js) or Expo client. Kev stays on the backend (Modal GPU) and never runs on the device.
- **Remembered mobile features:** the share sheet (share a founder's LinkedIn or website to start the agent), voice notes after meetings (transcribed into investor notes), and a push notification when research finishes.

## 4. Research design

### Conditions

| ID | Learn stage | Input | Trained on |
|---|---|---|---|
| C1a | RRF, `combiner="elasticnet"` (the library default) | Jev answer matrix | Train |
| C1b | RRF, `combiner="vote"` (the paper's method and the VCBench entry) | Jev answer matrix | Train |
| C2 | Base Kev-0.6B, zero-shot, as a TRL decision-model combiner | Jev answers serialised as text | Nothing |
| C3 | Fine-tuned Kev-0.6B, as a TRL decision-model combiner | Jev answers serialised as text | Train |
| C4 | Fine-tuned Kev-0.6B, direct | The founder text exactly as TRL renders it | Train |
| CTRL | XGBoost | Jev answer matrix | Train (tuned on val) |
| EXTRA | Base Kev-0.6B, direct | The founder text exactly as TRL renders it | Nothing |

Every answer-based condition uses the **same** fitted RRF (same `rules_`, same Jev answers), computed once through TRL and cached by TRL's own cache. C1a and C1b share one generation step: fit once, then refit with the other combiner against the cached answers.

## 4b. TRL fidelity protocol (applies to every test and research run)

1. **Pin TRL.** Work from a fork of `Vela-Research/think-reason-learn` at commit `3437d64` (v0.3.0). Record the commit, the TRL version and the model IDs in `results/run_info.json`.
2. **Use TRL's real entry points only.** That means `RRF(...).fit()`, `.answers()`, `.predict_proba()`, `.predict()` and `.estimate_cost()`, TRL's `LLM` and `LLMSession` for every model call (generator, Jev, and Kev served as a System One endpoint), and TRL's disk cache. Never reimplement question generation, answering or rendering outside TRL.
3. **RRF settings:** library defaults, except `beta=0.5` (to match the VCBench and research metric F0.5; the library default is 1.0) and `random_state=42`. Record any other deviation in the README.
4. **Kev learn stage as a TRL-native extension.** Following `CONTRIBUTING.md` ("Adding a model"), implement it in the fork, not as a side script:
   - **Preferred:** a new RRF combiner, `combiner="decision"` with `combiner_model=<decision model spec>`. RRF's answers are serialised in rule order and sent through the `LLMSession` to a decision model (Jev or Kev via `systemone` and `base_url`). The model returns P(success), and TRL's `best_threshold` sets the threshold.
   - **Fallback, if that changes RRF too much:** a `BinaryTRLClassifier` subclass that wraps a fitted RRF and implements `_afit` and `_apredict_proba`.
   - Either way, store every constructor argument unchanged, and pass `check_classifier` and the contract tests offline using `think_reason_learn.testing.fake_llms`.
   - Fine-tuning Kev happens outside TRL (Kev's trainer). TRL only calls the served model.
5. **C4 input fidelity:** C4 and EXTRA read the founder text exactly as TRL renders a sample for its answerer, using TRL's own rendering helper, so the only difference from the TRL conditions is the missing think and reason steps.
6. **One threshold protocol for all conditions.** The primary comparison tunes every condition's threshold on **val** for F0.5. For C1a and C1b, also report TRL's native as-shipped result: `predict()` with TRL's out-of-fold threshold from train. Threshold-free metrics (Brier, ECE, PR-AUC) are reported for every condition.
7. **Same data, same splits, every condition.** Fit only on train, tune only on val, test once.
8. **Development path:** prototype in the fork's `lab/` folder (git-ignored), then move the extension into the package with tests, a docs page and a `docs/source/changelog.rst` line. Run `ruff`, `pyright` and `pytest` (offline) before opening the PR.

### Metrics

On the test split: F0.5 (the main metric, matching VCBench), precision, recall, Brier score and ECE (10 bins). Each gets a bootstrap 95% CI (1,000 resamples, stratified). Also produce a reliability diagram per condition.

### Research phases

- **Phase 1 (app-critical):** score all conditions. This picks the winning learn stage, which the app needs.
- **Phase 2 (app-critical):** train the production model and build the threshold table (sections 7–8).
- **Phase 3 (interp, research only, after the app works):** see below. The app does not depend on it.

### Interp (Phase 3)

The goal is to explain why each learn stage decides as it does, in two parts.

**1. Behavioural interp (answer flips; do this first).**

- For each question, flip its answer (yes↔no) for every test founder, and record the mean change in P(success) for C3. Repeat for C2.
- Rank questions by importance, and compare that ranking against C1's elastic-net coefficients and XGBoost's importances.
- Test interactions by flipping pairs of top questions. A pair effect that isn't additive means an interaction a linear model can't capture.
- Flips measure *use*: if the output moves, the model relies on that input.

**2. Mechanistic interp (Kev is open weights, so this is possible).**

- **Tooling:** get activations with Hugging Face `output_hidden_states=True`, through Kev's own `DecisionModel` forward pass, so the LoRA, special tokens and pointer head are all real. Use PyTorch forward hooks or `nnsight` for patching. Fit probes with scikit-learn. TransformerLens is not used: Kev is Qwen3 plus a LoRA plus a custom pointer head plus special tokens, so it would need merged weights and still leave the head outside.
- Take the hidden state at the `<decide>` token for every layer.
- **Success probes:** at each layer, fit a logistic regression from the `<decide>` hidden state to the success label (train on train, score on test). Plot probe accuracy by layer for base Kev against C3 (and C4). The question: where does the decision form, and does fine-tuning move it earlier or strengthen it?
- **Fact probes:** probe for individual inputs (for example "prior exit = yes") at `<decide>`, layer by layer.
- **Activation patching (to show use, not just presence):** for founder pairs that differ in one key answer, patch one layer's `<decide>` activation from one founder into the other, and measure the change in output. This localises where the decision is made.
- Caveat for the write-up: probes show information is *present* (decodable), not that it's *used*. Flips and patching show use.

**3. Sparse autoencoders, to find inferred features (stretch, after the probes).**

The goal is to discover latent features the model builds that are **not** single template fields, for example "career trajectory" or "founder-market fit".

1. **SAE:** first look for a pretrained SAE for `Qwen3-0.6B-Base` in SAELens, which may transfer to the LoRA-tuned Kev. Otherwise, train a small TopK SAE (width about 4–8k) on one middle layer's residual stream, using every token position of all 3,000 profiles (roughly 0.5–1M vectors).
2. **Label features:** collect each feature's top-activating examples, and have Claude write a one-line description of each.
3. **Explained or inferred:** regress each feature's activation on the template fields. High R² means an encoding of a known input. Low R² means an **inferred** feature.
4. **Link to the decision:** correlate inferred features with the success label, and ablate them to measure the change in Kev's output.
5. **Leakage check:** an inferred feature that predicts success but matches no real founder attribute probably reflects artefacts of the generated data. Report it as such.

### Sanity check

If C1 or XGBoost scores above about 0.8 F0.5 on test, the data is too easy. Stop and regenerate with stronger noise before drawing conclusions.

## 5. Data

### Splits

3,000 rows, split by founder, stratified on outcome band, `seed=42`:

| Split | Rows | Research "yes" | Use |
|---|---|---|---|
| train | 2,000 | ~400 | RRF fit, XGBoost, all Kev fine-tuning |
| val | 400 | ~80 | Temperatures, early stopping, XGBoost tuning, choosing the production decider, agent thresholds |
| test | 600 | ~120 | Final research scores only, run once at the end |

Optional robustness check: a second, independent 600-row test set from a fresh Adaption run.

### Parsing

Each Adaption record has `instruction`, `input` and `output`. The output is exactly two lines:

```
outcome: <shut down | under $50M | $50M-$500M | $500M-$1B | over $1B>
years: <under 5 | 5-8 | over 8>
```

Normalise en and em dashes to `-`, collapse whitespace, and lowercase for matching. Drop and count any row that doesn't parse. Record per split: band counts, years counts, the share of rows with "unknown" fields, and a duplicate check (exact plus near-duplicate on `input`).

### Formats derived from each record

- **TRL:** `X = input text`, `y = "successful" if outcome in {"$500M-$1B","over $1B"} else "failed"`, and `task = "Predict whether this startup founder's company will succeed (exit, IPO or funding over $500M)."`
- **Serialised answers** (for C2 and C3): one line per rule, `"<question> yes"` or `"<question> no"`, thresholding Jev's P(yes) at 0.5 in a fixed rule order. Optionally use bands (`likely yes`, `unsure`, `likely no`). Pick one option and keep it fixed.
- **Kev JSONL** (one request per line, the same shape as the API plus labels):

  ```json
  {"state": "<serialised answers OR raw profile>",
   "questions": {"success": {"type": "noul",
     "instructions": "Will this founder's company succeed (exit, IPO or funding over $500M)?",
     "label": true}}}
  ```

  `noul` labels are `true`/`false`. A `choice` label is the option name, with options given as `"criteria": {"option": "description" | null}`.

## 6. Pipeline steps (research)

1. `research/splits.py`: parse, validate and split. Save `data/splits/{train,val,test}.jsonl` and a stats report.
2. `research/fit_rrf.py`: fit `RRF(task, generator=<OpenAI or Anthropic model>, answerer="jev", beta=0.5, random_state=42)` on train (C1a, elastic net). Refit with `combiner="vote"` for C1b; TRL's cache reuses the generated questions and answers. Save `rrf.rules_` and `rrf.questions_` to `data/answers/rules.json`, pickle both models, and save `rrf.estimate_cost()`.
3. `research/answers.py`: run `rrf.answers()` on train, val and test, and save `data/answers/{split}.csv`. **This is the expensive step, so run it once and cache it.**
4. `research/baselines.py`:
   - **C1:** `rrf.predict_proba(test)`.
   - **CTRL:** XGBoost on the train matrix, tuned on val.
5. `research/serialise.py`: build the serialised answer texts and the Kev JSONL files for C3 (answers) and C4 (raw profile), for each split.
6. `research/kev_zero_shot.py`: run C2 through the TRL-native decision combiner (section 4b) pointed at base Kev, and run EXTRA with base Kev on TRL-rendered founder text.
7. `research/train_kev.py`: fine-tune C3 and C4 (command below), then fit the temperature on val.
8. `research/evaluate.py`: compute all metrics and CIs on test, plus reliability diagrams. Save `results/experiments/` and `results/summary/`.
9. `research/interp_flips.py` (**Phase 3, after the app works**): answer flips and pair flips for C3 and C2, compared against C1's coefficients and XGBoost's importances.
10. `research/interp_probes.py` (**Phase 3**): layer-wise success and fact probes at `<decide>` for base Kev, C3 and C4, then activation patching.
11. `research/interp_sae.py` (**Phase 3, stretch**): SAE training or loading, feature labelling, explained-versus-inferred regression, decision linkage.

### Kev commands (from the Kev README; **VERIFY** the flags with `--help`)

```bash
# setup (Python 3.12 or 3.13, uv)
uv sync --extra serve
# serve a model
uv run --extra serve python -m kev.serve --run jaredpalmer/kev-0.6b --port 8009
# fine-tune from the released checkpoint
uv run python -m kev.train --data train.jsonl --base Qwen/Qwen3-0.6B-Base --init_from jaredpalmer/kev-0.6b \
    --epochs 2 --lr 2e-5 --batch 8 --dtype bf16 --device cuda --out runs/c3
# evaluate
uv run python -m kev.benchmark --run runs/c3 --data val.jsonl --out runs/c3-eval
```

Use early stopping or checkpoint selection on val, and a GPU (a Modal H100 is fastest; Colab works for 0.6B). Kev also has a Modal deploy script at `skills/kev-deploy/scripts/kev_serve.py`.

### TRL with a Kev endpoint (verified 2026-11-14)

Kev is the answerer (section 0), so this is how TRL reaches it. A custom decision endpoint needs `kind="decision"`, the full `/v1/systemone` URL and a non-empty key:

```python
from think_reason_learn import LLM
kev = LLM("kev-0.6b", base_url="http://127.0.0.1:8009/v1/systemone", kind="decision", api_key="local")
```

`research/checks/kev_endpoint.py` makes one call through `LLMSession` against `KEV_BASE_URL`.

## 7. Production model (app)

After the research, pick the winning input type (C3 answers, or C4 raw profile) **on val, never on test**. Train one more Kev with the same recipe, but with two `choice` questions:

- `outcome`: shut down / under $50M / $50M-$500M / $500M-$1B / over $1B
- `years`: under 5 / 5-8 / over 8

Fit a temperature per question on val. This model powers the investor controls. Research results come from C1–C4 only.

## 8. Product (agent and app)

### Inputs (any combination)

- **Investor form:** optional fields matching the profile template, plus free-text notes, plus voice notes (transcribed).
- **Founder identifier:** a name, LinkedIn text or URL, website, or deck text. On mobile, these arrive through the **share sheet**.

### Pipeline

1. **Research agent** (Claude API with the web search tool). For each template field, return `{value, source_url, confidence}`. Only information from before the founding date counts. Stream progress to the UI.
2. **Merge.** Investor fields take precedence. Agent findings that contradict them are flagged as conflicts rather than silently resolved. Missing fields become "unknown". Every field records where it came from: investor, agent (with source) or unknown.
3. **Anonymise and render** into the exact training template (section 10). Notes that don't fit the template (traction, gut feel) go into the memo only.
4. **Answer:** Jev answers the saved `rrf.rules_`.
5. **Decide:** the production Kev returns calibrated `outcome` and `years` distributions.
6. **Act:** the investor controls produce advance, escalate or pass.
7. **Memo:** verdict, probabilities, top drivers (answer flips for this founder), what-if toggles, sources, conflicts and unknowns.
8. **Push notification** when research and scoring finish.

### Investor controls (all computed client-side from cached distributions, so they're instant)

| Control | Computation |
|---|---|
| Target outcome ($50M / $500M / $1B) | P(outcome ≥ target) = the sum of the bands at or above it |
| Timeline (5 / 8 years) | P(within horizon) from `years`. Combined with the target assuming independence, so label it an estimate. |
| Risk appetite | Picks the advance and pass thresholds on the chosen probability. Shows expected precision and recall from a val-derived lookup table. |
| Filters (sector, solo/team, technical founder, first-time/repeat) | Hard filters on profile fields |

What-if toggles re-run only the Kev call, with no new research or Jev call.

### Batch mode

Upload a CSV of founders, and each is researched, scored and triaged into advance, escalate and pass.

### Guardrails (visible in the UI)

Public information only; nothing stored after the session; "screening aid, not investment advice"; a plain statement of what the model predicts (unicorn-scale outcomes, trained on generated data).

### Stack

- **Kev:** server on a Modal GPU (`kev.serve`) with base Kev, C3, C4 and the production model. Keep it warm during the demo.
- **Backend:** FastAPI covering the agent, merge, Jev calls, decider and policy.
- **Frontend:** a mobile-first Next.js PWA, or Expo. Streamlit is the fallback if time runs out.
- **Keys** (environment variables, never committed): TypeSafe (Jev), OpenAI or Anthropic (RRF generator), Anthropic (agent), Modal.
- **Demo fallback:** cache Jev answers and agent results for the demo founders.

## 9. Repo layout, timeline and cut lines

```
data/        raw/  splits/  answers/
research/    splits.py fit_rrf.py answers.py baselines.py serialise.py kev_zero_shot.py train_kev.py evaluate.py interp.py
app/         agent.py merge.py render.py decide.py policy.py api.py  frontend/
results/     README.md FINDINGS.md GLOSSARY.md DECISIONS.md run_info.json data/ experiments/ summary/   (see section 9c)
MASTER_PLAN.md  README.md  .env.example
```

### Timeline

**Day 1**

- [ ] 50-row Adaption test batch, reviewed, then the full 3,000 rows
- [ ] Kev server running; one decision call works
- [ ] TRL works with `answerer="jev"` on 5 founders
- [ ] Splits and stats report
- [ ] RRF fitted; rules saved; Jev answer matrices cached for all splits
- [ ] C1 and CTRL scored
- [ ] Serialisation; C2 and EXTRA scored
- [ ] C3 and C4 fine-tuned, with temperatures fitted on val
- [ ] Agent and merge prototype, tested on 5 real founder pages

**Day 2, app-critical first**

- [ ] C3 and C4 scored on test; results table with CIs; metric and reliability plots
- [ ] Winner picked on val; production model trained (two choice questions); temperatures fitted
- [ ] Risk-threshold lookup table built from val
- [ ] Full app pipeline wired, with mobile share sheet and push notification
- [ ] Batch mode; voice notes (stretch)

**Day 2, Phase 3 interp (only once the app works end to end)**

- [ ] Answer flips and pair flips against the elastic net and XGBoost; importance plot
- [ ] Layer-wise probes (base Kev, C3, C4); probe-accuracy-by-layer plot
- [ ] Activation patching (stretch)
- [ ] SAE inferred-feature analysis (stretch)

**Day 2, finish**

- [ ] README with results, interp findings and limitations; pitch; two rehearsals; backup video

### Cut lines (in order)

The SAE analysis, activation patching, probes, voice notes, batch mode, the EXTRA condition, the timeline control, what-if toggles, then answer-flip interp. **Never cut** C1, CTRL, the confidence intervals, or the advance/escalate/pass policy.

### Claims allowed

On this generated dataset, with Kev as the answerer:

- learn stage X scored Y F0.5 (CI) against RRF's native Z
- fine-tuning changed Kev's ECE from A to B
- the importance comparison between Kev and the elastic net

Real-world accuracy is **not** claimed.

## 9b. Step-by-step order (chronological)

Do the steps in this order. Each step lists what it needs, what it produces, and how to tell it's done. Steps marked ∥ can run in parallel with the step before them.

### Stage A: setup and data (Day 1 morning)

**A1. Repo scaffold and TRL fork.**
- Do: create the project repo layout (section 9), `.env.example` and a README stub.
- Fork `Vela-Research/think-reason-learn`, check out commit `3437d64`, and create a branch `feature/decision-combiner`.
- Install the fork in editable mode in the project environment (`pip install -e ../think-reason-learn` with the extras for your generator provider), plus XGBoost and scikit-learn. Install the fork's dev tools (`poetry install --with dev --all-extras`) to run its tests.
- Done when: `python -c "import think_reason_learn, xgboost"` works, and the fork's `poetry run pytest` passes before any changes.

**A2. 50-row data sample.** ∥
- Do: run the 50-row prompt in Adaption, and save the result to `data/raw/sample50.jsonl`.
- Done when: the user and the parse/validation script both confirm the counts, format, consistency and stereotype rules all pass.

**A3. Kev environment and server.** ∥
- Do: clone Kev and run `uv sync --extra serve`. Serve `jaredpalmer/kev-0.6b` on a GPU (Modal).
- Done when: one `/v1/systemone` request with a `noul` question returns probabilities.

**A4. TRL smoke test.**
- Needs: A1, plus API keys.
- Do: fit `RRF(task, generator=..., answerer="jev")` on about 20 sample rows, with a small `n_prompts`.
- Done when: `rrf.answers()` returns a matrix and `predict_proba` runs. Note the cost per founder.

**A5. Full dataset.**
- Needs: A2 approved.
- Do: run the full 3,000-row prompt and save to `data/raw/full.jsonl`.
- Done when: the validation report shows band proportions within about ±3 points of target, and under 2% of rows dropped.

**A6. Splits.**
- Needs: A5.
- Do: `research/splits.py`, a stratified 2,000 / 400 / 600 split with seed 42.
- Done when: `data/splits/*.jsonl` and a stats report exist, with no founder appearing in two splits.

### Stage B: TRL phase and baselines (Day 1 afternoon)

**B1. Fit RRF on train.**
- Needs: A4 and A6.
- Do: `research/fit_rrf.py`.
- Done when: `rules.json` and the pickled model are saved.

**B2. Cache Jev answer matrices.**
- Needs: B1.
- Do: `research/answers.py` for train, val and test.
- Done when: `data/answers/{split}.csv` has one row per founder and one column per rule, with no missing values.

**B3. C1 and CTRL.**
- Needs: B2.
- Do: score `rrf.predict_proba(test)`. Train XGBoost on the train matrix and tune it on val.
- Done when: both rows are in `results/summary/metrics.csv` (provisional, since CIs come later).

**B4. Sanity check.**
- Needs: B3.
- Done when: C1 and CTRL F0.5 are below about 0.8. If not, stop and regenerate the data with more noise (back to A5).

**B5. Serialisation and Kev JSONL.**
- Needs: B2.
- Do: `research/serialise.py`, building the C3 files (answers as the state) and C4 files (raw profile as the state) for every split.
- Done when: the files exist and one record per file has been checked by eye.

**B5b. TRL-native decision combiner (in the fork).**
- Needs: A1 and A3.
- Do: implement `combiner="decision"` (or the fallback `BinaryTRLClassifier` wrapper) per section 4b.4. Prototype in `lab/`, then move it into the package.
- Done when: it passes `check_classifier` and the contract tests offline with `fake_llms`, and one real call through `LLMSession` to the Kev server returns probabilities.

**B6. C2 and EXTRA.**
- Needs: A3, B5 and B5b.
- Do: `research/kev_zero_shot.py`, base Kev on test, once with answers and once with the raw profile.
- Done when: both rows are in `results/summary/metrics.csv`.

### Stage C: fine-tuning (Day 1 evening)

**C1-train. Fine-tune C3 and C4.**
- Needs: B5.
- Do: `research/train_kev.py`, starting `--init_from jaredpalmer/kev-0.6b` with a learning rate of 2e-5 for 1–2 epochs, selecting checkpoints on val.
- Done when: both runs are saved and their val loss improved over base.

**C2-temp. Temperatures.**
- Needs: C1-train.
- Do: fit one temperature per model on val.
- Done when: val ECE is no worse than before calibration.

**C3-agent. Agent prototype.** ∥
- Do: `app/agent.py`, `app/merge.py` and `app/render.py`.
- Done when: 5 real founder pages render into the exact template, with sources and unknowns marked, and nothing from after the founding date.

### Stage D: results and production model (Day 2 morning; app-critical)

**D1. Final evaluation.**
- Needs: B3, B6 and C2-temp.
- Do: `research/evaluate.py`, scoring every condition on test once, with bootstrap CIs and reliability diagrams.
- Done when: `results/experiments/` and `results/summary/` are complete.

**D2. Pick the winner on val.**
- Needs: D1.
- Do: compare C3 against C4 on val F0.5 and ECE, never test. Record the decision and the reason in the README.

**D3. Production model.**
- Needs: D2.
- Do: train Kev with the winning input type and two `choice` questions (`outcome`, `years`), and fit both temperatures on val.
- Done when: val predictions give sensible band distributions.

**D4. Threshold table.**
- Needs: D3.
- Do: from val, compute precision and recall at each threshold for each target outcome and timeline. Save `app/thresholds.json`.

### Stage E: app (Day 2 midday)

**E1. Backend.**
- Needs: C3-agent, D3 and D4.
- Do: `app/decide.py`, `app/policy.py` and `app/api.py` (FastAPI), covering the agent, merge, render, Jev answers, production Kev, policy and memo.
- Done when: one API call takes a founder from input to a full memo.

**E2. Frontend.**
- Needs: E1.
- Do: a mobile-first PWA (or Expo), with:
  - an investor form, notes and a founder identifier
  - live research progress
  - the memo: verdict, probabilities, drivers, sources, conflicts and unknowns
  - controls: target outcome, timeline, risk and filters
  - what-if toggles
- Done when: the full flow works on a phone.

**E3. Mobile features.**
- Do: the share sheet into the app, and a push notification when scoring finishes. Voice notes are a stretch goal.

**E4. Batch mode and demo cache.**
- Do: CSV upload and triage. Cache Jev answers and agent output for the demo founders.

### Stage F: interp (Day 2 afternoon; only once Stage E works end to end)

**F1. Answer flips.** `research/interp_flips.py`: single and pair flips for C3 and C2, compared against C1's coefficients and XGBoost's importances. Produces the importance plot.

**F2. Probes.** `research/interp_probes.py`: success and fact probes by layer for base Kev, C3 and C4. Produces the probe-accuracy-by-layer plot.

**F3. Activation patching** (stretch).

**F4. SAE inferred features** (stretch). `research/interp_sae.py`.

### Stage G: ship (Day 2 end)

**G1. README.** Method, results table, plots, interp findings, the decision record (D2), and limitations.

**G2. Pitch.** Problem → agent → calibrated autonomy → live demo → results → interp.

**G3. Rehearse twice and record a backup video.** Push the final code.

**G4. TRL contribution.** In the fork:
- finish tests for the decision combiner
- add a docs page with a usage example
- add a `changelog.rst` line
- run `ruff`, `pyright` and `pytest`
- open a PR against `Vela-Research/think-reason-learn`, linking the results table and the method

If time runs out during the hackathon, open it as a draft PR and finish it afterwards.

## 9b-guide. Prompt cues for driving Claude Code, step by step

Give Claude Code one step at a time, using the short cue below as your prompt (adding detail as needed). Before moving on, check the step's "done when" in section 9b. **For:** R = research, A = app, R+A = both.

### Stage A: setup and data

| Step | Prompt cue | What's actually happening | For |
|---|---|---|---|
| A1 | "Read MASTER_PLAN.md, then set up the project repo and the TRL fork as in step A1." | Builds the workspace, and gets your own copy of Vela's library, pinned to one version, so every result can be reproduced and turned into a contribution later. | R+A |
| A2 | "Write the parser and validator for the 50-row sample and check it against the rules." | Before generating thousands of founders, makes sure the sample looks right: the correct mix of outcomes, no names, nothing from the future, and no single detail giving the answer away. | R |
| A3 | "Set up Kev and serve kev-0.6b on Modal; send one test question." | Starts Kev, the small decision model, on a rented GPU, and checks it can answer a yes/no question with a probability. | R+A |
| A4 | "Smoke-test TRL's RRF on 20 rows with Jev as the answerer and estimate the cost." | A tiny dry run of Vela's pipeline: AI writes questions about founders, and Jev answers them. It proves the plumbing works and shows the cost before you spend for real. | R |
| A5 | "Validate the full 3,000-row dataset and report the stats." | Checks that the full dataset came out balanced and clean. | R |
| A6 | "Split the data into train, val and test as in step A6." | Divides founders into three piles: one to learn from, one to make choices on, and one locked away for the final exam, so the results are honest. | R |

### Stage B: TRL phase and baselines

| Step | Prompt cue | What's actually happening | For |
|---|---|---|---|
| B1 | "Fit RRF on train with beta=0.5, both combiners, and save the rules." | Vela's pipeline reads the training founders and writes about 100 yes/no questions that seem to separate winners from losers. These questions are the app's reusable checklist. | R+A |
| B2 | "Compute and cache Jev's answers for all three splits." | Jev answers every question for every founder, building a big table of yes/no probabilities. Everything after this reuses that table, so it's done once. | R+A |
| B3 | "Score C1a, C1b and the XGBoost control on test." | Measures how well Vela's current methods, and a standard ML model, predict success from that table. These are the scores Kev must beat. | R |
| B4 | "Run the sanity check: are the baselines suspiciously good?" | If even simple methods score near-perfectly, the data is too easy and the comparison would be meaningless. This catches it early. | R |
| B5 | "Serialise the answers into text and build Kev's training files for C3 and C4." | Converts the answer table into plain text Kev can read, and prepares two training sets: one where Kev reads TRL's answers, and one where it reads the raw profile. | R |
| B5b | "Build the decision combiner inside the TRL fork, following CONTRIBUTING.md, with offline tests." | Adds a new option to Vela's library: "let a decision model make the final call". This is the actual code contribution, and it keeps the research inside TRL's real pipeline. | R+A |
| B6 | "Score C2 and EXTRA with base Kev, zero-shot." | Tests Kev without any training. How good is it out of the box? | R |

### Stage C: fine-tuning

| Step | Prompt cue | What's actually happening | For |
|---|---|---|---|
| C1-train | "Begin fine-tuning Kev for C3 and C4 from the released checkpoint." | Teaches Kev from the training founders: it sees each founder's answers or profile along with the real outcome, and adjusts to predict better. | R+A |
| C2-temp | "Fit temperatures on val for both fine-tuned models." | Calibration: adjusts Kev's confidence so "70%" really means about 70% of such founders succeed. This is what lets the app's risk slider be trusted. | R+A |
| C3-agent | "Build the research agent, merge and render; test on 5 real founder pages." | The app's researcher: it looks a founder up online, fills in their background with sources, combines that with what the investor typed, and formats it exactly like the training data. | A |

### Stage D: results and production model

| Step | Prompt cue | What's actually happening | For |
|---|---|---|---|
| D1 | "Run the final evaluation on test for every condition, with CIs and reliability plots." | The final exam: every method faces the locked-away founders once, and gets a score with error bars. | R |
| D2 | "Compare C3 and C4 on val and record the decision." | Picks which version of Kev powers the app, using the "choices" pile, never the exam pile. | R+A |
| D3 | "Train the production model with the outcome and years choice questions." | Trains the app's Kev to predict how big the outcome will be and how long it takes, not just yes/no, so the valuation and timeline sliders work. | A |
| D4 | "Build the risk-threshold table from val." | Works out what each risk setting means in practice, e.g. "at this setting, about 45% of advanced founders succeed." | A |

### Stage E: app

| Step | Prompt cue | What's actually happening | For |
|---|---|---|---|
| E1 | "Build the backend API: agent → merge → Jev → production Kev → policy → memo." | Connects everything into one service: send in a founder, get back a verdict (advance, escalate or pass) with reasons. | A |
| E2 | "Build the mobile-first frontend with the investor form, memo and sliders." | The screen the investor uses: type what you know, watch the agent research, read the memo, move the sliders. | A |
| E3 | "Add the share sheet and the push notification." | Lets an investor share a founder's LinkedIn from any app to start screening, and get pinged when it's done. | A |
| E4 | "Add batch mode and cache the demo founders." | Triage a whole list at once, and make sure the live demo can't break if an API is slow. | A |

### Stage F: interp (only once the app works)

| Step | Prompt cue | What's actually happening | For |
|---|---|---|---|
| F1 | "Run the answer-flip interp for C3 and C2 against the baselines." | Asks "what does Kev actually pay attention to?" by flipping one answer at a time and seeing how much the verdict moves, then compares that with what Vela's method weights. | R |
| F2 | "Run layer-wise probes on base Kev, C3 and C4." | Looks inside Kev's layers to see where the success judgement forms, and whether training moved it. | R |
| F3 | "Run activation patching on the top question pairs." | Swaps internal signals between two founders to prove which parts of Kev cause the decision, rather than just correlate with it. | R |
| F4 | "Train or load an SAE and find inferred features." | Uncovers hidden concepts Kev invented that aren't in the data, like "career momentum", and checks whether any are just artefacts of the generated data. | R |

### Stage G: ship

| Step | Prompt cue | What's actually happening | For |
|---|---|---|---|
| G1 | "Write the results READMEs and FINDINGS.md per section 9c." | Turns the numbers into a story anyone can follow. | R |
| G2–G3 | "Draft the pitch outline and a demo script from FINDINGS.md." | Prepares what you'll say and show to judges. | R+A |
| G4 | "Finish the TRL PR: tests, docs, changelog, checks; open it as a draft." | Packages the new decision combiner so Vela can review and merge it into TRL. | R |

## 9c. Results and records: organised for non-researchers

Every result must be easy to find and understand for someone with no ML background, such as an investor, a judge or a Vela engineer skimming quickly.

### Layout

```
results/
  README.md            START HERE: what this project tested, the answer in 3 sentences, and a map of this folder
  FINDINGS.md          plain-English findings, one short section per finding, each with its key number and plot
  GLOSSARY.md          every term used (F0.5, precision, recall, calibration, ECE, Brier, CI, learn stage...) in one or two plain sentences, with an everyday example
  DECISIONS.md         decision log: date, decision, reason, evidence (e.g. "picked C3 over C4 on val because...")
  run_info.json        TRL commit and version, model IDs, seeds, split sizes, dates, costs
  data/
    README.md          what the dataset is, how it was made, its limits
    stats.md           band counts, years, unknowns, duplicates, drops, per split (tables, not raw dumps)
  experiments/
    01_baselines/      C1a, C1b, CTRL
    02_kev_zero_shot/  C2, EXTRA
    03_kev_finetuned/  C3, C4
    04_production_model/
    05_interp_flips/
    06_interp_probes/
    07_interp_sae/
  summary/
    metrics.csv        one row per condition: every metric with its CI
    metrics.md         the same table, formatted, with a one-line "what this means" under it
    plots/             final figures used in README, FINDINGS and the pitch
```

### Every experiment folder contains

- `README.md`, written in plain English, with these headings in this order:
  1. **Question:** what we wanted to know, in one sentence
  2. **What we did:** 3–5 sentences, with no unexplained jargon
  3. **Result:** the headline number, with its confidence interval, plus a plain reading (e.g. "out of every 10 founders it flags, about 4 succeed")
  4. **What it means:** for the research, and for the app
  5. **Caveats:** honest limits
  6. **Files:** what each file in the folder is
- `metrics.csv`, plus `metrics_dictionary.md` explaining every column (name, meaning, units, better if higher or lower).
- `predictions.csv`: one row per test founder, with an ID, the true label, P(success), the decision and the condition. This lets anyone check the numbers.
- `config.json`: the exact settings, seeds and model IDs used.
- `plots/`: every plot with a descriptive file name (e.g. `reliability_c3_vs_c1a.png`), a title, labelled axes with units, a legend, and a one-sentence caption in the folder README.

### Writing rules

- Put the answer first and the detail after.
- Define every technical term the first time it appears in each document, or link to `GLOSSARY.md`.
- Pair every number with a plain reading and a CI. Never give a bare metric.
- Use consistent names everywhere: C1a, C1b, C2, C3, C4, CTRL, EXTRA, with a short descriptive name alongside, e.g. "C3 (fine-tuned Kev on TRL's answers)".
- Use tables and plots over long prose, and short paragraphs over walls of bullets.
- Never overwrite a result. Rerun into a new dated subfolder, and record why in `DECISIONS.md`.
- The top-level project `README.md` links to `results/README.md` first.

## 10a. Dataset prompt (50-row quality-check sample; Adaption, instruction format)

Run this first (step A2). Validate the output before running the full prompt in section 10.

```text
TASK
Create a sample instruction dataset of exactly 50 records for fine-tuning a model that predicts a startup's outcome, and how long it took, from an anonymised profile of its founder at the time of founding. This is a quality-check sample, so accuracy, realism and variety matter more than anything else.

EXACT COUNTS BY OUTCOME
shut down: 25
under $50M: 8
$50M-$500M: 7
$500M-$1B: 5
over $1B: 5
Shuffle the records so outcomes are not grouped together.

FORMAT (every record)
instruction: "Based on this founder's profile at the time of founding, predict the company's outcome and how long it took."
input: the founder profile, following the template below exactly
output: exactly two lines, copying these values character for character, with no other text:
outcome: <one of: shut down | under $50M | $50M-$500M | $500M-$1B | over $1B>
years: <one of: under 5 | 5-8 | over 8>

LABEL DEFINITIONS
outcome: the company's final outcome as of 2025. Use the exit or IPO value if it exited; total funding raised if it is still private and has raised over $500M; "shut down" if it closed. A private company still operating with under $500M raised should not be used.
years: years from founding to that outcome (to closure, for shut-down companies).
All companies founded between 2010 and 2019.

GROUNDING AND ACCURACY
1. Base every record on a real founder and real company outcome wherever possible, especially the 10 records at $500M and above. Where a real basis isn't available, create a founder whose background is typical of real founders with that outcome.
2. The outcome and years must be correct for the real company the record is based on. Do not guess. If you are not confident of a real company's outcome, choose a different company.
3. Prefer lesser-known companies. Do not use founders of household-name companies or anyone widely famous.

INPUT TEMPLATE (use these exact lines and allowed values)
This founder leads a startup in the [industry] industry, founded with [solo / 1 / 2 / 3+] co-founder(s).
Founder background: [technical / business / mixed / domain specialist], [<5 / 5-10 / 10-15 / 15+] years of work experience, [none / some / deep] prior experience in this startup's industry.
Education:
- [degree, e.g. BSc / BA / MSc / MBA / PhD / no degree] in [field], university ranked QS [top 50 / 51-100 / 101-300 / 300+ / unranked]
Jobs (oldest first):
- [role], [generic company description], [1-10 / 11-50 / 51-200 / 201-1,000 / 1,001-5,000 / 5,000+] employees, [industry], [<1 / 1-2 / 2-3 / 3-5 / 5+ years]
Prior startups: [none / N founded before, with outcomes, e.g. "1 shut down" or "1 shut down, 1 acquired under $50M"].
Prior exits: [none / N acquisitions or IPOs as co-founder, value band e.g. "under $50M", "$50M-$500M"].
List 1 to 3 education entries and 1 to 6 jobs, matching the person's real or plausible history.

INTERNAL CONSISTENCY (check every record)
1. Years of work experience must roughly match the sum of job durations.
2. Prior exits can't exceed prior startups, and their value bands must match the prior startup outcomes listed.
3. Degrees, fields and roles must fit together (for example a technical background with engineering roles or a technical degree).
4. Job industries and "prior experience in this startup's industry" must agree.
5. Timelines must be realistic for the outcome: shut-downs are mostly under 5 or 5-8 years; exits over $1B are mostly 5-8 or over 8 years and rarely under 5.

AVOID STEREOTYPES (these let a model take shortcuts)
1. No single field may predict the outcome. Each of these must appear in both strong-outcome and shut-down records: top-50 universities, unranked or no degree, big-tech-sized employers, solo founders, first-time founders, repeat founders, prior exits.
2. About 15 records (spread across all bands) should be surprising: strong backgrounds that shut down, and modest or unusual backgrounds that reached large outcomes. Base these on real cases where possible; real founder outcomes are often surprising.
3. Do not make larger outcomes have longer or more detailed profiles. Similar length and detail across all bands.
4. Use neutral, factual wording only. No evaluative words such as "exceptional", "prestigious", "visionary", "strong", "struggled" or "successful".

VARIETY
1. At least 15 different startup industries across the 50 records (for example fintech, healthtech, biotech, B2B SaaS, developer tools, e-commerce, logistics, edtech, climate, cybersecurity, marketplaces, media, hardware, insurtech, agtech, gaming, proptech, HR tech, travel, food).
2. Mix solo founders and teams, technical, business, mixed and domain specialist backgrounds, early-career and very experienced founders, and degrees from no degree to PhD.
3. No two records should share the same career path or obvious template.
4. In exactly 8 records, spread across all outcome bands, mark 1 or 2 fields as "unknown" (for example "Prior exits: unknown", "unknown employees", or "QS unknown").

PROFILE RULES
1. Include only what was true on the day the company was founded. No later roles, funding, team size, traction or events, and no role at the startup itself.
2. Fully anonymise: no names of people, companies, products or universities, no exact dates, cities, countries or unique phrases. Describe employers generically, e.g. "a payments company" or "a large search and advertising company".

FORMAT EXAMPLE (for structure only; do not reuse its content, industry or career path)
instruction: Based on this founder's profile at the time of founding, predict the company's outcome and how long it took.
input:
This founder leads a startup in the logistics industry, founded with 1 co-founder(s).
Founder background: business, 5-10 years of work experience, some prior experience in this startup's industry.
Education:
- BA in Economics, university ranked QS 101-300
Jobs (oldest first):
- Analyst, a management consulting firm, 1,001-5,000 employees, Professional Services, 2-3 years
- Operations Manager, a freight brokerage company, 201-1,000 employees, Logistics, 3-5 years
Prior startups: none.
Prior exits: none.
output:
outcome: shut down
years: under 5
```

## 10. Dataset prompt (full run, 3,000 rows; Adaption, instruction format)

Identical to the 50-row sample in section 10a, apart from the counts and the batch instructions. Run it only after the sample passes.

```text
TASK
Create an instruction dataset of 3,000 records for fine-tuning a model that predicts a startup's outcome, and how long it took, from an anonymised profile of its founder at the time of founding. Accuracy, realism and variety matter more than speed.

COUNTS BY OUTCOME (within about 1 percentage point)
shut down: 1,500 (50%)
under $50M: 450 (15%)
$50M-$500M: 450 (15%)
$500M-$1B: 300 (10%)
over $1B: 300 (10%)
Generate in batches of 50 with the same proportions in each batch, and shuffle so outcomes are not grouped together.

FORMAT (every record)
instruction: "Based on this founder's profile at the time of founding, predict the company's outcome and how long it took."
input: the founder profile, following the template below exactly
output: exactly two lines, copying these values character for character, with no other text:
outcome: <one of: shut down | under $50M | $50M-$500M | $500M-$1B | over $1B>
years: <one of: under 5 | 5-8 | over 8>

LABEL DEFINITIONS
outcome: the company's final outcome as of 2025. Use the exit or IPO value if it exited; total funding raised if it is still private and has raised over $500M; "shut down" if it closed. A private company still operating with under $500M raised should not be used.
years: years from founding to that outcome (to closure, for shut-down companies).
All companies founded between 2010 and 2019.

GROUNDING AND ACCURACY
1. Base every record on a real founder and real company outcome wherever possible, especially the records at $500M and above. Where a real basis isn't available, create a founder whose background is typical of real founders with that outcome.
2. The outcome and years must be correct for the real company the record is based on. Do not guess. If you are not confident of a real company's outcome, choose a different company.
3. Prefer lesser-known companies. Do not use founders of household-name companies or anyone widely famous.

INPUT TEMPLATE (use these exact lines and allowed values)
This founder leads a startup in the [industry] industry, founded with [solo / 1 / 2 / 3+] co-founder(s).
Founder background: [technical / business / mixed / domain specialist], [<5 / 5-10 / 10-15 / 15+] years of work experience, [none / some / deep] prior experience in this startup's industry.
Education:
- [degree, e.g. BSc / BA / MSc / MBA / PhD / no degree] in [field], university ranked QS [top 50 / 51-100 / 101-300 / 300+ / unranked]
Jobs (oldest first):
- [role], [generic company description], [1-10 / 11-50 / 51-200 / 201-1,000 / 1,001-5,000 / 5,000+] employees, [industry], [<1 / 1-2 / 2-3 / 3-5 / 5+ years]
Prior startups: [none / N founded before, with outcomes, e.g. "1 shut down" or "1 shut down, 1 acquired under $50M"].
Prior exits: [none / N acquisitions or IPOs as co-founder, value band e.g. "under $50M", "$50M-$500M"].
List 1 to 3 education entries and 1 to 6 jobs, matching the person's real or plausible history.

INTERNAL CONSISTENCY (check every record)
1. Years of work experience must roughly match the sum of job durations.
2. Prior exits can't exceed prior startups, and their value bands must match the prior startup outcomes listed.
3. Degrees, fields and roles must fit together (for example a technical background with engineering roles or a technical degree).
4. Job industries and "prior experience in this startup's industry" must agree.
5. Timelines must be realistic for the outcome: shut-downs are mostly under 5 or 5-8 years; exits over $1B are mostly 5-8 or over 8 years and rarely under 5.

AVOID STEREOTYPES (these let a model take shortcuts)
1. No single field may predict the outcome. Each of these must appear in both strong-outcome and shut-down records: top-50 universities, unranked or no degree, big-tech-sized employers, solo founders, first-time founders, repeat founders, prior exits.
2. About 30% of records (spread across all bands) should be surprising: strong backgrounds that shut down, and modest or unusual backgrounds that reached large outcomes. Base these on real cases where possible; real founder outcomes are often surprising.
3. Do not make larger outcomes have longer or more detailed profiles. Similar length and detail across all bands.
4. Use neutral, factual wording only. No evaluative words such as "exceptional", "prestigious", "visionary", "strong", "struggled" or "successful".

VARIETY
1. At least 15 different startup industries in every batch of 50, and at least 25 across the whole dataset (for example fintech, healthtech, biotech, B2B SaaS, developer tools, e-commerce, logistics, edtech, climate, cybersecurity, marketplaces, media, hardware, insurtech, agtech, gaming, proptech, HR tech, travel, food).
2. Mix solo founders and teams, technical, business, mixed and domain specialist backgrounds, early-career and very experienced founders, and degrees from no degree to PhD.
3. No two records should share the same career path or obvious template, across the whole dataset.
4. In about 15% of records, spread across all outcome bands, mark 1 or 2 fields as "unknown" (for example "Prior exits: unknown", "unknown employees", or "QS unknown").

PROFILE RULES
1. Include only what was true on the day the company was founded. No later roles, funding, team size, traction or events, and no role at the startup itself.
2. Fully anonymise: no names of people, companies, products or universities, no exact dates, cities, countries or unique phrases. Describe employers generically, e.g. "a payments company" or "a large search and advertising company".

FORMAT EXAMPLE (for structure only; do not reuse its content, industry or career path)
instruction: Based on this founder's profile at the time of founding, predict the company's outcome and how long it took.
input:
This founder leads a startup in the logistics industry, founded with 1 co-founder(s).
Founder background: business, 5-10 years of work experience, some prior experience in this startup's industry.
Education:
- BA in Economics, university ranked QS 101-300
Jobs (oldest first):
- Analyst, a management consulting firm, 1,001-5,000 employees, Professional Services, 2-3 years
- Operations Manager, a freight brokerage company, 201-1,000 employees, Logistics, 3-5 years
Prior startups: none.
Prior exits: none.
output:
outcome: shut down
years: under 5
```

## 11. Working rules for Claude Code

- Fixed seeds everywhere. Every expensive output (Jev answers, generator questions, model predictions) is cached to disk and reused.
- Never touch the test split until final evaluation. All selection and tuning happens on val.
- Keys come from the environment. Commit a `.env.example`, never real keys.
- Verify the **VERIFY** items with a tiny test before building on them.
- Write results in the structure of section 9c as you go, not at the end. Each experiment's folder README is part of that experiment being done.
- Keep the research code and the app separate. The app only loads the saved artifacts: rules, the production model and the threshold table.
