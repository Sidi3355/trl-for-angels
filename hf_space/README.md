---
title: trl-for-angels Kev
emoji: 🧭
colorFrom: gray
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
short_description: Kev answerer and decider for the trl-for-angels app
---

# Kev for the trl-for-angels app

Two Kev servers on this Space's free CPU, behind one front door:

| Path | Model | Role |
|---|---|---|
| `/answerer/v1/systemone` | `jaredpalmer/kev-0.6b` (base) | answers TRL's yes/no questions about a founder |
| `/decider/v1/systemone` | the production model (`DECIDER_MODEL`, a model repo) | outcome and years distributions, **raw**: the app applies the per-question temperatures from `model.json` |

Both speak TypeSafe's System One protocol, exactly as `kev.serve` (Kev commit `2074cc4`) does,
in fp32 on CPU. `GET /health` reports whether both have loaded; a request before then gets a 503.

**Settings** (Space settings → Variables and secrets):

- `KEV_API_KEY` (secret, recommended): every request needs `Authorization: Bearer <key>`.
- `DECIDER_MODEL` (variable): the production model's repo id. Until it's set, the decider runs
  base Kev as a stand-in, and `/health` says so.
- `HF_TOKEN` (secret): needed only if `DECIDER_MODEL` is a private repo.

Built by `hf_space/` in the trl-for-angels repo.
