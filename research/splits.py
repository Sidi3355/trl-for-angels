"""Split the founder records into train, val and test (MASTER_PLAN step A6).

Usage:
    python research/splits.py data/raw/full.jsonl [--seed 42]

Every row is parsed with validate.py, and rows that don't parse (no valid outcome and years, or
no profile in the template) are dropped and counted by reason. Each kept row gets an id
(``r00001`` is the file's first record; blank lines are skipped) and the research label
("successful" for $500M-$1B and over $1B, otherwise "failed").

The kept rows are split 2,000 / 400 / 600, stratified on the five outcome bands, with seed 42.
If the file doesn't hold exactly 3,000 usable rows, the sizes are scaled to keep that ratio.
Each row is one anonymised founder, so the unit of the split is the row, but exact and
near-duplicate profiles (validate.py's ``duplicates``) are joined into groups and every group
stays in one split, so no profile can leak from train into val or test.

Writes data/splits/{train,val,test}.jsonl, the plain-English report results/data/stats.md, and
the key ``splits.actual`` in results/run_info.json. The same input and seed give byte-identical
files: the random order comes from SHA-256 hashes of the seed and row positions, not from a
library's random number stream.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import validate as v  # noqa: E402

ROOT = HERE.parent
SEED = 42
SPLITS = ("train", "val", "test")
PLANNED = {"train": 2000, "val": 400, "test": 600}  # MASTER_PLAN section 5
BANDS = tuple(v.OUTCOME_LABELS.values())  # "shut down" ... "over $1B"
POSITIVE, NEGATIVE = "successful", "failed"  # section 5, TRL format
FIELDS = ("id", "instruction", "input", "output", "outcome", "years", "label")

DROP_REASONS = {
    "json": "the line isn't valid JSON",
    "output": "the output has no valid outcome and years",
    "input": "the profile is empty or doesn't follow the template",
    "both": "both the output and the profile are invalid",
}

PURPOSE = {
    "train": "what models learn from",
    "val": "used to make choices: thresholds, temperatures, which model the app uses",
    "test": "locked away and scored once, at the very end",
}


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------


def label(outcome: str) -> str:
    """The research label: "successful" for $500M and above, otherwise "failed"."""
    return POSITIVE if outcome in v.STRONG else NEGATIVE


def split_sizes(n: int) -> dict[str, int]:
    """Sizes in the plan's 2,000 : 400 : 600 ratio that add up to n (largest remainder)."""
    total = sum(PLANNED.values())
    exact = {s: Fraction(n * PLANNED[s], total) for s in SPLITS}
    sizes = {s: math.floor(exact[s]) for s in SPLITS}
    by_remainder = sorted(SPLITS, key=lambda s: (-(exact[s] - sizes[s]), SPLITS.index(s)))
    for s in by_remainder[: n - sum(sizes.values())]:
        sizes[s] += 1
    return sizes


def band_quotas(counts: dict[str, int], sizes: dict[str, int]) -> dict[str, dict[str, int]]:
    """Rows of each band per split: each band's exact proportional share, rounded down or up so
    that every band and every split adds up exactly (controlled rounding).

    A band's share in a split is count * size / n. Each one is rounded down, then the rows still
    missing are added one per cell, choosing among the cells with a fractional part the
    combination that fits every split's size and is closest to the exact shares. With five
    bands and three splits there are at most 3^5 combinations, so all are tried. One always
    exists, so every quota is within one row of its exact share.
    """
    n = sum(counts.values())
    bands = [b for b in BANDS if counts.get(b)]
    exact = {(b, s): Fraction(counts[b] * sizes[s], n) for b in bands for s in SPLITS}
    base = {k: math.floor(x) for k, x in exact.items()}
    frac = {k: exact[k] - base[k] for k in exact}
    band_need = {b: counts[b] - sum(base[b, s] for s in SPLITS) for b in bands}
    split_need = {s: sizes[s] - sum(base[b, s] for b in bands) for s in SPLITS}
    options = [
        list(itertools.combinations([s for s in SPLITS if frac[b, s]], band_need[b]))
        for b in bands
    ]
    best, best_score = None, Fraction(-1)
    for choice in itertools.product(*options):
        got = Counter(s for combo in choice for s in combo)
        if any(got[s] != split_need[s] for s in SPLITS):
            continue
        score = sum((frac[b, s] for b, combo in zip(bands, choice) for s in combo), Fraction(0))
        if score > best_score:
            best, best_score = choice, score
    if best is None:  # can't happen: the fractional shares are themselves a solution
        raise AssertionError("no rounding of the band quotas fits the split sizes")
    quotas = {b: {s: base[b, s] for s in SPLITS} for b in bands}
    for b, combo in zip(bands, best):
        for s in combo:
            quotas[b][s] += 1
    return quotas


def _hash(seed: int, *parts: object) -> str:
    return hashlib.sha256("|".join(map(str, (seed, *parts))).encode("utf-8")).hexdigest()


def _uniform(seed: int, *parts: object) -> float:
    """A number in [0, 1) that depends only on the seed and the parts."""
    return int(_hash(seed, *parts)[:15], 16) / 16**15


# ---------------------------------------------------------------------------
# Duplicate groups
# ---------------------------------------------------------------------------


@dataclass
class Group:
    rows: list[v.Record]
    kinds: set[str] = field(default_factory=set)  # "exact", "near"

    @property
    def kind(self) -> str:
        return " and ".join(k for k in ("exact", "near") if k in self.kinds) + " copy"


def duplicate_groups(records: list[v.Record]) -> list[Group]:
    """Every record in one group; records linked by an exact or near duplicate share one.

    Links come from validate.py's ``duplicates`` (same normalised text, or Jaccard >= 0.8 on
    5-word shingles) and are joined transitively (union-find), so a chain A~B~C is one group.
    """
    exact, near = v.duplicates(records)
    parent = {r.row: r.row for r in records}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    links: list[tuple[int, int, str]] = []
    for rows in exact:
        links += [(rows[0], other, "exact") for other in rows[1:]]
    links += [(a, b, "near") for a, b, _ in near]
    for a, b, _ in links:
        union(a, b)
    groups: dict[int, Group] = {}
    for r in records:
        groups.setdefault(find(r.row), Group([])).rows.append(r)
    for a, _, kind in links:
        groups[find(a)].kinds.add(kind)
    return sorted(groups.values(), key=lambda g: g.rows[0].row)


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------


def _weighted_pick(options: list[str], weights: list[int], u: float) -> str:
    x = u * sum(weights)
    for option, w in zip(options, weights):
        if x < w:
            return option
        x -= w
    return options[-1]


def _overflow(comp: Counter, remaining: dict[str, dict[str, int]], s: str) -> int:
    return sum(max(0, c - remaining[b][s]) for b, c in comp.items())


def _room(remaining: dict[str, dict[str, int]], s: str) -> int:
    return sum(remaining[b][s] for b in remaining)


def _repair(remaining: dict[str, dict[str, int]], s: str) -> int:
    """After a group overfilled a band's quota in split s, move quota so split sizes still add
    up: band b gets one more row in s and one fewer in s2, another band b2 one fewer in s and
    one more in s2. Returns the number of such swaps.
    """
    swaps = 0
    for b in remaining:
        while remaining[b][s] < 0:
            s2 = max((x for x in SPLITS if x != s and remaining[b][x] > 0),
                     key=lambda x: remaining[b][x], default=None)
            b2 = max((x for x in remaining if x != b and remaining[x][s] > 0),
                     key=lambda x: remaining[x][s], default=None)
            if s2 is None or b2 is None:
                break  # nothing to swap with: the split sizes will be off, and reported
            remaining[b][s] += 1
            remaining[b][s2] -= 1
            remaining[b2][s] -= 1
            remaining[b2][s2] += 1
            swaps += 1
    return swaps


def assign(groups: list[Group], quotas: dict[str, dict[str, int]],
           seed: int) -> tuple[dict[int, str], int]:
    """Split for every row (by file position), and the number of quota swaps needed.

    Groups of two or more rows go first (largest first), each into one split chosen at random
    among the splits with room for all its rows, weighted by the room left for its main band.
    Single rows then fill each band's remaining quota per split, in a seeded random order.
    """
    remaining = {b: dict(q) for b, q in quotas.items()}
    split_of: dict[int, str] = {}
    swaps = 0
    multi = sorted((g for g in groups if len(g.rows) > 1),
                   key=lambda g: (-len(g.rows), _hash(seed, "group", g.rows[0].row)))
    for g in multi:
        comp = Counter(r.outcome for r in g.rows)
        main = max(comp, key=lambda b: (comp[b], -BANDS.index(b)))
        fits = [s for s in SPLITS if _overflow(comp, remaining, s) == 0]
        if fits:
            weights = [remaining[main][s] for s in fits]
            chosen = _weighted_pick(fits, weights, _uniform(seed, "pick", g.rows[0].row))
        else:
            chosen = min(SPLITS, key=lambda s: (_overflow(comp, remaining, s),
                                                -_room(remaining, s), SPLITS.index(s)))
        for b, c in comp.items():
            remaining[b][chosen] -= c
        for r in g.rows:
            split_of[r.row] = chosen
        swaps += _repair(remaining, chosen)

    singles: dict[str, list[v.Record]] = defaultdict(list)
    for g in groups:
        if len(g.rows) == 1:
            singles[g.rows[0].outcome].append(g.rows[0])
    for b in remaining:
        rows = sorted(singles[b], key=lambda r: _hash(seed, "row", r.row))
        start = 0
        for s in SPLITS:
            take = rows[start : start + max(0, remaining[b][s])]
            for r in take:
                split_of[r.row] = s
            remaining[b][s] -= len(take)
            start += len(take)
        # A band's quotas always add up to its unplaced rows, so every row has a place.
        assert start == len(rows), "unplaced rows"
    return split_of, swaps


# ---------------------------------------------------------------------------
# The whole step
# ---------------------------------------------------------------------------


@dataclass
class SplitResult:
    rows_read: int
    kept: list[v.Record]
    dropped: dict[str, list[int]]  # reason key -> positions in the file
    ids: dict[int, str]  # position in the file -> id
    split_of: dict[str, str]  # id -> split
    by_split: dict[str, list[v.Record]]
    groups: list[Group]  # duplicate groups of 2+ rows
    target_sizes: dict[str, int]
    sizes: dict[str, int]
    scaled: bool
    swaps: int
    checks: list[tuple[str, str, str]]  # (check, PASS/WARN, detail)
    actual: dict  # what went into run_info.json splits.actual


def _drop_reason(row: dict, rec: v.Record) -> str | None:
    if "__error__" in row:
        return "json"
    bad_output, bad_input = rec.outcome is None, rec.profile is None
    if bad_output and bad_input:
        return "both"
    return "output" if bad_output else "input" if bad_input else None


def _shown(path: Path) -> str:
    """A path as the report shows it: relative to the repo, or just its name."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def _leakage_checks(res_by_split: dict[str, list[v.Record]], kept: list[v.Record],
                    groups: list[Group], ids: dict[int, str],
                    split_of: dict[str, str]) -> list[tuple[str, str, str]]:
    """Checks computed from the written splits, not assumed. Leaks raise; a loose
    stratification (only possible with very large duplicate groups) is a WARN.
    """
    seen: Counter = Counter(ids[r.row] for rs in res_by_split.values() for r in rs)
    in_two = [i for i, c in seen.items() if c > 1]
    missing = [ids[r.row] for r in kept if ids[r.row] not in seen]
    spread = [g for g in groups if len({split_of[ids[r.row]] for r in g.rows}) > 1]
    text_splits: dict[str, set[str]] = defaultdict(set)
    for s, rs in res_by_split.items():
        for r in rs:
            text_splits[v.normalise(r.input)].add(s)
    shared_text = [t for t, ss in text_splits.items() if len(ss) > 1]
    if in_two or missing or spread or shared_text:
        raise AssertionError(
            f"leak: ids in two splits {in_two[:5]}, missing {missing[:5]}, "
            f"groups spread {len(spread)}, shared texts {len(shared_text)}"
        )
    counts = Counter(r.outcome for r in kept)
    n = len(kept)
    worst = Fraction(0)
    for rs in res_by_split.values():
        got = Counter(r.outcome for r in rs)
        for b in counts:
            worst = max(worst, abs(got[b] - Fraction(counts[b] * len(rs), n)))
    return [
        ("Every kept row is in exactly one split", "PASS",
         f"{n:,} rows, {len(seen):,} ids, none missing, none repeated"),
        ("No duplicate group is spread over two splits", "PASS",
         f"{len(groups)} group(s) checked"),
        ("No profile text appears in two splits", "PASS",
         "compared after normalising case, dashes and spaces"),
        ("Each band's count in each split is within one row of its exact proportional share",
         "PASS" if worst <= 1 else "WARN", f"largest gap {float(worst):.2f} rows"
         + ("" if worst <= 1 else ": a duplicate group was bigger than its band's share")),
    ]


def make_splits(path: Path, out_dir: Path, report_path: Path, run_info_path: Path,
                seed: int = SEED) -> SplitResult:
    """Parse, split and write everything for one input file. Paths are explicit so that tests
    can point every output at a temporary folder.
    """
    path, out_dir = Path(path), Path(out_dir)
    report_path, run_info_path = Path(report_path), Path(run_info_path)
    raw = v.load(path)
    kept: list[v.Record] = []
    dropped: dict[str, list[int]] = {k: [] for k in DROP_REASONS}
    for i, row in enumerate(raw, 1):
        rec = v.parse_record(row, i)
        reason = _drop_reason(row, rec)
        if reason:
            dropped[reason].append(i)
        else:
            v.check_record(rec)  # rule errors are reported, not dropped (see the notes)
            kept.append(rec)
    if not kept:
        raise ValueError(f"{path}: no row parses, so there is nothing to split")

    ids = {r.row: f"r{r.row:05d}" for r in kept}
    groups = duplicate_groups(kept)
    target = split_sizes(len(kept))
    quotas = band_quotas(Counter(r.outcome for r in kept), target)
    row_split, swaps = assign(groups, quotas, seed)
    split_of = {ids[row]: s for row, s in row_split.items()}
    by_split: dict[str, list[v.Record]] = {s: [] for s in SPLITS}
    for r in kept:  # file order within each split
        by_split[row_split[r.row]].append(r)
    sizes = {s: len(by_split[s]) for s in SPLITS}
    multi = [g for g in groups if len(g.rows) > 1]
    checks = _leakage_checks(by_split, kept, multi, ids, split_of)

    out_dir.mkdir(parents=True, exist_ok=True)
    for s in SPLITS:
        lines = []
        for r in by_split[s]:
            obj = {"id": ids[r.row], "instruction": r.instruction, "input": r.input,
                   "output": r.output, "outcome": r.outcome, "years": r.years,
                   "label": label(r.outcome)}
            lines.append(json.dumps(obj, ensure_ascii=False) + "\n")
        (out_dir / f"{s}.jsonl").write_text("".join(lines), encoding="utf-8", newline="\n")

    actual = {
        **sizes,
        "seed": seed,
        "input_file": path.name,
        "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rows_read": len(raw),
        "rows_kept": len(kept),
        "rows_dropped": len(raw) - len(kept),
        "scaled_from_planned": len(kept) != sum(PLANNED.values()),
        "stratified_on": "outcome band",
        "duplicate_groups": len(multi),
    }
    result = SplitResult(
        rows_read=len(raw), kept=kept, dropped=dropped, ids=ids, split_of=split_of,
        by_split=by_split, groups=multi, target_sizes=target, sizes=sizes,
        scaled=actual["scaled_from_planned"], swaps=swaps, checks=checks, actual=actual,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    text = report(result, path, out_dir, run_info_path, seed)
    report_path.write_text(text, encoding="utf-8", newline="\n")
    update_run_info(run_info_path, actual)
    return result


def update_run_info(path: Path, actual: dict) -> None:
    """Set ``splits.actual`` and leave every other key as it is."""
    info = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    info.setdefault("splits", {})["actual"] = actual
    path.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# Report (results/data/stats.md), written for non-researchers (MASTER_PLAN 9c)
# ---------------------------------------------------------------------------


def _md(text: str) -> str:
    """Escape '$' so Markdown viewers don't read "$50M-$500M" as maths."""
    return text.replace("$", "\\$")


def _cs(n: int, total: int) -> str:
    return f"{n:,} ({n / total:.1%})" if total else "0"


def _positions(rows: list[int], limit: int = 20) -> str:
    shown = ", ".join(str(r) for r in rows[:limit])
    return shown + (f", and {len(rows) - limit} more" if len(rows) > limit else "")


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(row) + " |" for row in rows]
    return out


def report(res: SplitResult, path: Path, out_dir: Path, run_info_path: Path,
           seed: int) -> str:
    kept, by = res.kept, res.by_split
    n_drop = res.rows_read - len(kept)
    sizes = " / ".join(f"{res.sizes[s]:,} {s}" for s in SPLITS)
    out = [
        "# Data splits",
        "",
        f"**In short:** {res.rows_read:,} rows were read from `{_shown(path)}`. "
        f"{len(kept):,} were kept and {n_drop:,} dropped because they don't parse. The kept "
        f"rows are split into **{sizes}**, with the same mix of outcomes in each (stratified "
        f"on outcome band, seed {seed}). No founder, and no group of duplicate profiles, "
        "appears in more than one split.",
        "",
    ]
    if res.scaled:
        out += [
            f"The plan expects 3,000 usable rows. This file has {len(kept):,}, so the three "
            "sizes were scaled to keep the plan's 2,000 : 400 : 600 ratio.",
            "",
        ]
    if res.sizes != res.target_sizes:
        out += [
            "**Note:** duplicate groups too large to fit their band's share forced the sizes "
            "away from the target of "
            + " / ".join(f"{res.target_sizes[s]:,} {s}" for s in SPLITS) + ".",
            "",
        ]
    out += [
        "## What the words mean",
        "",
        "- **Row (founder):** one anonymised founder profile and its company's outcome. Every "
        "row is a different founder, so splitting by founder means splitting by row.",
        "- **Train, val and test:** three separate piles of founders. Train is "
        f"{PURPOSE['train']}; val (validation) is {PURPOSE['val']}; test is "
        f"{PURPOSE['test']}, so the final results are honest.",
        "- **Outcome band:** the company's final outcome, one of five bands from \"shut down\" "
        "to \"over \\$1B\". **Years** is the time from founding to that outcome.",
        "- **Research label:** \"successful\" if the outcome is \\$500M-\\$1B or over \\$1B, "
        "otherwise \"failed\". It is what the research models predict.",
        "- **Stratified:** each split gets the same mix of outcome bands as the whole dataset, "
        "to within one row, so no split is by chance easier or harder than another.",
        "- **Duplicate group:** profiles that are exact copies, or near copies (sharing 80% or "
        "more of their five-word phrases), of each other. A group is kept together in one "
        "split, so no model is tested on a founder it has, in effect, already seen.",
        "- **Unknown field:** a profile detail the dataset marks as \"unknown\" on purpose "
        "(for example \"Prior exits: unknown\").",
        "",
        "## Rows read, kept and dropped",
        "",
    ]
    out += _table(["", "Rows"], [["Read from the file", f"{res.rows_read:,}"],
                                 ["Kept", f"{len(kept):,}"], ["Dropped", f"{n_drop:,}"]])
    out.append("")
    if n_drop:
        out += _table(["Why dropped", "Rows", "Positions in the file"],
                      [[DROP_REASONS[k], f"{len(rows):,}", _positions(rows)]
                       for k, rows in res.dropped.items() if rows])
        out.append("")

    n = len(kept)
    out += ["## Split sizes", ""]
    out += _table(["Split", "What it is for", "Rows", "Share of kept rows"],
                  [[s, PURPOSE[s], f"{res.sizes[s]:,}", f"{res.sizes[s] / n:.1%}"]
                   for s in SPLITS])
    out += ["", "## Outcome bands per split", "",
            "Each cell is the number of founders, and in brackets that number as a share of "
            "the split. Reading across a row, the shares should be nearly equal.", ""]
    band_rows = []
    for b in BANDS:
        cells = [_cs(sum(r.outcome == b for r in by[s]), res.sizes[s]) for s in SPLITS]
        band_rows.append([_md(b)] + cells + [_cs(sum(r.outcome == b for r in kept), n)])
    out += _table(["Outcome band", *SPLITS, "All"], band_rows)
    out += ["", "## Years to outcome per split", ""]
    year_rows = []
    for y in v.YEARS:
        cells = [_cs(sum(r.years == y for r in by[s]), res.sizes[s]) for s in SPLITS]
        year_rows.append([y] + cells + [_cs(sum(r.years == y for r in kept), n)])
    out += _table(["Years", *SPLITS, "All"], year_rows)
    out += ["", "Years weren't used to stratify, so their mix can vary a little more between "
            "splits than the outcome bands do."]

    out += ["", "## Research label per split", ""]
    label_rows = []
    for name in (POSITIVE, NEGATIVE):
        cells = [_cs(sum(label(r.outcome) == name for r in by[s]), res.sizes[s])
                 for s in SPLITS]
        label_rows.append([name] + cells + [_cs(sum(label(r.outcome) == name for r in kept), n)])
    out += _table(["Label", *SPLITS, "All"], label_rows)

    out += ["", "## Profiles with an unknown field, per split", ""]
    unknown = [_cs(sum(bool(r.profile.unknown_fields) for r in by[s]), res.sizes[s])
               for s in SPLITS]
    out += _table(["", *SPLITS, "All"],
                  [["Rows with at least one unknown field"] + unknown
                   + [_cs(sum(bool(r.profile.unknown_fields) for r in kept), n)]])

    out += ["", "## Duplicate groups", ""]
    if res.groups:
        rows_in = sum(len(g.rows) for g in res.groups)
        per = Counter(res.split_of[res.ids[g.rows[0].row]] for g in res.groups)
        out += [
            f"{len(res.groups)} group(s) of duplicate profiles, holding {rows_in:,} rows. Each "
            "group sits wholly in one split: "
            + ", ".join(f"{per[s]} in {s}" for s in SPLITS) + ".",
            "",
        ]
        limit = 30
        table = []
        for g in res.groups[:limit]:
            table.append([
                ", ".join(res.ids[r.row] for r in g.rows), g.kind,
                ", ".join(_md(b) for b in sorted({r.outcome for r in g.rows}, key=BANDS.index)),
                res.split_of[res.ids[g.rows[0].row]],
            ])
        out += _table(["Rows (ids)", "Kind", "Outcome bands", "Split"], table)
        if len(res.groups) > limit:
            out.append(f"\n...and {len(res.groups) - limit} more.")
        mixed = [g for g in res.groups if len({r.outcome for r in g.rows}) > 1]
        if mixed:
            out += ["", f"{len(mixed)} group(s) have copies with different outcome bands: the "
                    "same profile was given different outcomes. They are worth a look in the "
                    "raw data."]
    else:
        out.append("None: no two profiles are exact or near copies of each other.")

    out += ["", "## Leakage checks", "",
            "Computed from the written split files. PASS means the check holds.", ""]
    out += _table(["Check", "Result", "Detail"], [[c, s, d] for c, s, d in res.checks])

    with_errors = [r for r in kept if r.errors]
    out += [
        "",
        "## How the split was made",
        "",
        "1. Every row was parsed with `research/validate.py`. Rows without a valid outcome and "
        "years, or without a profile in the template, were dropped.",
        "2. Each kept row got an id, `r` plus its position in the file (`r00001` is the first "
        "record; blank lines are skipped), and the research label.",
        "3. Duplicates were found with validate.py's check (identical text after normalising "
        "case, dashes and spaces; or 80% or more of five-word phrases shared), and linked rows "
        "were joined into groups.",
        "4. Each band's share of each split was worked out exactly, then rounded so that every "
        "band and every split adds up (each within one row of its exact share).",
        "5. Groups of two or more rows were placed first, each wholly in one split chosen at "
        "random, weighted by the room left. Single rows were then dealt in a random order to "
        "fill each band's share of each split.",
        f"6. The random order comes from SHA-256 hashes of the seed ({seed}) and each row's "
        "position, so the same file and seed give identical splits on any machine.",
        "",
        "## Notes",
        "",
        f"- Input file SHA-256: `{res.actual['input_sha256']}`.",
        "- Near copies are found by comparing likely pairs rather than every pair, so a few "
        "may be missed. Exact copies are always found.",
    ]
    if res.swaps:
        out.append(f"- {res.swaps} quota swap(s) were needed so that duplicate groups fit "
                   "while keeping the split sizes exact.")
    if with_errors:
        out.append(
            f"- {len(with_errors):,} kept row(s) parse but break a dataset rule checked by "
            "`research/validate.py` (for example a banned word or a value outside the "
            "template). They are kept here; the validation report lists them: "
            + _positions([r.row for r in with_errors]) + " (positions in the file)."
        )
    out += ["", "## Files", ""]
    out += _table(["File", "What it is"], [
        [f"`{_shown(out_dir / f'{s}.jsonl')}`",
         f"the {s} split, one founder per line, with the fields "
         + ", ".join(f"`{f}`" for f in FIELDS)] for s in SPLITS
    ] + [[f"`{_shown(run_info_path)}`", "key `splits.actual`: the sizes, seed and input file"]])
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("path", type=Path, nargs="?", default=ROOT / "data" / "raw" / "full.jsonl")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "splits")
    ap.add_argument("--report", type=Path, default=ROOT / "results" / "data" / "stats.md")
    ap.add_argument("--run-info", type=Path, default=ROOT / "results" / "run_info.json")
    args = ap.parse_args(argv)
    if not args.path.exists():
        print(f"{args.path}: no such file", file=sys.stderr)
        return 1
    res = make_splits(args.path, args.out_dir, args.report, args.run_info, args.seed)
    print(f"{res.rows_read:,} rows read, {len(res.kept):,} kept, "
          f"{res.rows_read - len(res.kept):,} dropped; "
          + ", ".join(f"{s} {res.sizes[s]:,}" for s in SPLITS)
          + f"; {len(res.groups)} duplicate group(s)" + (" (sizes scaled)" if res.scaled else ""))
    for c, s, d in res.checks:
        if s != "PASS":
            print(f"  {s}: {c}: {d}")
    print(f"Report: {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
