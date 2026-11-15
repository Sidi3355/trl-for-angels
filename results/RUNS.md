# GPU runs (Kaggle)

Every run on Kaggle's free GPUs, newest last. Each run clones this repo's development branch,
runs one task from `kaggle/run.sh`, and pushes everything it wrote (except model weights and
files over 5 MB) to the **`kaggle-results`** branch under `runs/<UTC start>-<task>/`: `run.log`
(the full log), `status.txt`, `task.txt`, `repo_commit.txt` (the exact code that ran) and the
task's outputs. Outputs the next steps need are copied into this repo's `data/` with
`kaggle/import_run.py`. Hardware for every run: 2 × Tesla T4 (15 GB), driver 580, fp32.

| Run | Task (plan step) | Code | Result | What it did | Recorded in |
|---|---|---|---|---|---|
| `20261114-124358-a3` | a3 (A3) | `10ee3cc` | PASS | Served Kev-0.6B through TRL, measured answering speed (104/s) and fine-tuning speed and memory for short and long texts | DECISIONS: A3 |
| `20261114-124701-a3` | a3 (A3) | `5fdf335` | PASS | The same check, rerun with the new GitHub-linked runner | DECISIONS: A3 |
| `20261114-142314-hf_setup` | hf_setup | `d8b780a` | failed | Tried to create a Hugging Face Space for the Kev server: Hugging Face returned 402 (Spaces that run code need PRO), so the server moved to the owner's PC | DECISIONS: hosting |
| `20261114-153153-a4` | a4 (A4) | `df5a5aa` | PASS | TRL smoke test on 20 sample founders: Claude wrote 10 questions, Kev answered them, predictions ran; $0.11 | DECISIONS: A4 |
| `20261114-160701-b1b2` | b1b2 (B1, B2) | `22f39d4` | finished | Claude wrote 93 questions ($0.49); C1a, C1a-40, C1b and C2 fitted on 2,000 train founders; answer matrices and TRL predictions for every split; 86 min | DECISIONS: B1/B2 |
| `20261114-173802-c_kev` | c_kev (C1-train, C2-temp, B6) | `e44ead9` | **failed** | Trained C3 (2 epochs, 98 min) and C4 (chose epoch 2, T 1.275), then failed scoring C3 on val: the scorer used Kev's 384-token default, and C3's texts are 873 tokens. Nothing saved | DECISIONS: first c_kev run failed |
| `20261114-192753-c_kev` | c_kev (C1-train, C2-temp, B6) | `1fd795e` | finished | The rerun with the scoring fix: C3 (49 min per epoch) and C4 (8.5 min per epoch) both chose epoch 2; temperatures 1.072 and 1.275; both saved to Hugging Face; C3, C4 and EXTRA scored through TRL on val and test; 2 h 13 min | DECISIONS: C1-train, C2-temp |
| `20261114-224030-d_prod` | d_prod (D3) | `d5a461a` | finished | The production model on C3's input, with the outcome and years questions: 2 epochs of 87 min (two questions per founder), chose epoch 2, temperatures 1.149 (outcome) and 0.871 (years), val ECE 0.027 → 0.021; saved to Hugging Face. Its val distributions were asked without the options' descriptions, so they were redone on CPU (DECISIONS); 3 h 16 min | DECISIONS: D3/D4 |

To read a run's log: `git show origin/kaggle-results:runs/<run>/run.log`.
