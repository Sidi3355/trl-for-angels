# Glossary

Every term the results use, in plain words. Terms are grouped by topic: the method, the
models, the data, the scores and the inside view.

## The method

**TRL (Think, Reason, Learn).** Vela Research's open-source library for predictions that show
their reasons. It works in three steps: an AI writes yes/no questions (think), an AI answers
them about each founder (reason), and a simple model turns the answers into a prediction
(learn). *Like a hiring panel that agrees a checklist, fills it in for every candidate, then
scores the checklists.*

**RRF (Random Rule Forest).** The TRL method this project uses. It writes about 100 yes/no
questions, answers them for every founder, and combines the answers into one probability.

**Question (rule).** One yes/no question RRF wrote, such as "Has the founder founded a company
before?". The app reuses the same questions for every founder.

**Generator.** The AI that writes the questions. Here: Claude.

**Answerer.** The AI that answers each question about each founder. Here: base Kev-0.6B (see
*Kev*), the same for every condition so the comparison is fair.

**Answer matrix.** A table with one row per founder and one column per question, holding the
answerer's probability that the answer is yes.

**Learn stage (combiner).** The last step: whatever turns a founder's answers into a single
prediction. **This is what the research compares.** RRF ships two: an *elastic net* and a
*vote*. This project adds a third, a *decision model*.

**Elastic net.** A weighted sum: each question gets a weight learned from the training
founders, and the weights add up to a score. *Like a points system: +3 for a prior exit, +1
for a technical degree.* TRL's default learn stage (C1a).

**Vote.** Count how many of the best questions say yes; predict success if enough do. The
learn stage in RRF's paper (C1b).

**Decision model.** An AI that reads text and returns calibrated probabilities instead of
writing words. Jev and Kev are decision models. As a learn stage it reads a founder's answers
as text ("Has the founder founded a company before? yes …") and returns P(success).

**XGBoost.** A widely used machine-learning method that combines many small decision trees.
It's the control (CTRL): if Kev beats the elastic net but not XGBoost, the gain comes from
handling combinations of answers, not from Kev itself.

**Zero-shot.** Used as released, with no training on this task (C2, EXTRA).

**Fine-tuning.** Further training of a released model on this task's training founders, so
it learns this task (C3, C4, the production model).

**Production model.** The fine-tuned Kev the app uses. Instead of yes/no, it predicts which
outcome band a founder's company reaches, and how many years that takes.

## The models

**Jev.** TypeSafe's commercial decision model, TRL's default answerer. Not used here, because
it isn't free.

**Kev.** An open reconstruction of Jev's design that anyone can run and train. We use
**Kev-0.6B** (0.6 billion parameters, small enough for a free Kaggle GPU or a laptop).

**Base model.** A model as it was released, before any fine-tuning on this task.

**Checkpoint.** A saved copy of a model's learned settings at one point in training.

**Epoch.** One pass of training over every training founder.

**LoRA.** A way to fine-tune a large model by training a small add-on instead of the whole
model. Kev is a LoRA add-on on a Qwen language model.

**Temperature.** One number that makes a model's probabilities more or less confident without
changing which answer it ranks first. It's fitted on val so that "70%" means about 70%. Kev's
production model has one temperature per question.

## The data

**Generated data.** Founder profiles written by an AI (Adaption), grounded in real founders
where possible. Results describe this dataset, not the real world.

**Founding-date cutoff.** A profile holds only what was true on the day the company was
founded, so no model can peek at the future.

**Research label.** "Successful" if the company's outcome was $500M or more (exit, IPO or
funding), otherwise "failed". About 1 in 5 founders are successful.

**Base rate.** The share of founders who are successful: the score a coin weighted to that
share would get. Any useful model must beat it.

**Train, val and test (splits).** Three separate piles of founders. Models learn from **train**;
every choice (thresholds, temperatures, which model the app uses) is made on **val**
(validation); **test** is locked away and scored once at the end. *Like homework, mock exams
and the final exam.*

**Stratified.** Each split gets the same mix of outcomes as the whole dataset, so no split is
by chance easier.

**Overfitting.** Learning the training founders by heart instead of the pattern. It shows as
much better scores on train than on val or test.

## The scores

**Threshold.** The probability above which a model says "successful". Every condition's
threshold is tuned on val for F0.5, then used unchanged on test.

**Precision.** Of the founders a model flags as successful, the share who really were. *If it
flags 10 and 4 succeed, precision is 40%.*

**Recall.** Of the founders who really were successful, the share the model flagged. *If 10
succeeded and it flagged 6 of them, recall is 60%.*

**F0.5 (F-beta with beta 0.5).** One number that combines precision and recall but counts
precision twice as much: false alarms cost an investor more than misses. Between 0 and 1,
higher is better. It's the main score, and VCBench uses it too.

**PR-AUC.** How well a model ranks the successful founders above the rest, across every
threshold at once. Between 0 and 1, higher is better; the base rate is what random ranking
scores.

**Calibration.** Whether a model's probabilities mean what they say. *A calibrated model's
"30%" founders succeed about 30% of the time.* It's what makes the app's risk settings
trustworthy.

**Brier score.** The average squared gap between the predicted probability and what happened
(1 or 0). Lower is better. It rewards being both right and well calibrated.

**ECE (expected calibration error).** Founders are sorted into 10 bins by predicted
probability; in each bin, compare the average prediction with the share who succeeded, and
average the gaps. Lower is better. *An ECE of 0.05 means predictions are off by about 5
percentage points on average.*

**Reliability diagram.** The picture behind ECE: predicted probability across, actual success
rate up. A calibrated model's line follows the diagonal.

**Confidence interval (95% CI).** The range a score would likely fall in if we could test on
another sample of founders like these. Ours come from the *bootstrap*. *An F0.5 of 0.40 (CI
0.32–0.48) is pinned down to about ±0.08.* When two conditions' ranges overlap a lot, their
difference may be luck.

**Bootstrap.** Re-scoring a model on 1,000 random resamples of the test founders (drawn with
replacement, keeping the successful/failed mix) to see how much the score moves.

## Inside the model (interpretability)

**Answer flip.** Change one answer from yes to no (or the reverse) and see how much the
model's prediction moves. A big move means the model relies on that question.

**Probe.** A simple model trained to read a fact (such as "will succeed") out of Kev's internal
signals at one layer. If it can, that layer holds the fact. That shows the information is
present, not that Kev uses it.

**Activation patching.** Copy Kev's internal signal at one layer from one founder into
another and see whether the prediction follows. It shows where the decision is actually made.

**Sparse autoencoder (SAE).** A tool that breaks Kev's internal signals into separate, more
readable features, some of which may be concepts nobody wrote into the data.

## In the app

**Advance, escalate, pass.** The app's three actions: advance (worth a meeting), pass (not
now), and escalate (unclear: the investor decides). The risk setting picks where the
boundaries sit, using the val threshold table.
