# 03 · Kev fine-tuned: C3 and C4

## Question

Does Kev-0.6B predict founder success better, and with more trustworthy probabilities, once
it's trained on the training founders: reading TRL's answers (**C3**) or the founder profile
(**C4**)?

## What we did

Kev was fine-tuned from the released checkpoint with Kev's own recipe on the 2,000 training
founders (`research/train_kev.py`, on a free Kaggle T4): one epoch, then a second from it. The
checkpoint with the lowest val log-loss (released, epoch 1 or epoch 2) was kept, and its
temperature was fitted on val so its probabilities are calibrated. **C3** reads the same
answer text as C2, through the same TRL learn stage; **C4** reads the profile, as EXTRA does.
Thresholds are tuned on val for F0.5.

## Result

*Pending.* F0.5 and ECE on test with CIs, against C1a and CTRL.

## What it means

*Pending.* For the research: whether a trained decision model beats TRL's own learn stages,
and whether the questions help Kev (C3 against C4). For the app: the winner on val (never test)
becomes the input type of the production model (folder 04).

## Caveats

- C3's threshold, if taken from TRL's fit, would be optimistic, because Kev was trained on
  the same founders; the main comparison tunes it on val.
- Two epochs at most, chosen on val; longer training wasn't tried on the free GPU.

## Files

Same layout as folder 01, plus the training reports from the Kaggle run (`kev/c3_report.json`,
`kev/c4_report.json` on the `kaggle-results` branch): the chosen checkpoint, val scores
before and after, and the temperature.
