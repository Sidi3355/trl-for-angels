"""Settings and helpers every research script shares, so each condition sees the same text.

TASK and QUESTION are fixed by MASTER_PLAN section 5; the RRF settings by section 4b.3
(library defaults, except beta=0.5 and random_state=42).
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ("train", "val", "test")

TASK = ("Predict whether this startup founder's company will succeed (exit, IPO or funding "
        "over $500M).")
QUESTION = "Will this founder's company succeed (exit, IPO or funding over $500M)?"
POSITIVE, NEGATIVE = "successful", "failed"

GENERATOR = "anthropic:claude-opus-5-5"
GENERATOR_MAX_OUTPUT_TOKENS = 16000  # Claude thinks first; TRL's default 4096 can cut it off
KEV_BASE = "jaredpalmer/kev-0.6b"
RRF_SETTINGS = {"beta": 0.5, "random_state": 42}


def load_split(splits_dir: Path, split: str) -> tuple[list[str], list[str], list[str]]:
    """(ids, texts, labels) of one split written by research/splits.py."""
    rows = [json.loads(line) for line in (splits_dir / f"{split}.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    return [r["id"] for r in rows], [r["input"] for r in rows], [r["label"] for r in rows]


def kev_llm(url: str, name: str = "kev-0.6b"):
    """A Kev server as TRL's decision model (MASTER_PLAN section 0). No key: an open server.

    Keep ``name`` and ``url`` the same across scripts of one run, so TRL's cache matches.
    """
    from think_reason_learn.llm import LLM

    url = url.rstrip("/")
    if not url.endswith("/v1/systemone"):
        url += "/v1/systemone"
    return LLM(name, base_url=url, kind="decision")


def generator_llm(fake: bool = False):
    """Claude as RRF's question writer, or TRL's scripted fake writer for offline tests."""
    from think_reason_learn.llm import LLM

    if fake:
        return "fake:writer"
    return LLM(GENERATOR, max_output_tokens=GENERATOR_MAX_OUTPUT_TOKENS)


@contextmanager
def fake_writer(enabled: bool) -> Iterator[None]:
    """Inside the block, "fake:writer" writes a fixed set of founder questions (tests only)."""
    if not enabled:
        yield
        return
    from think_reason_learn.testing import FakeLLM, fake_llms

    questions = [
        "Has the founder founded a startup before?",
        "Does the founder have a prior exit?",
        "Does the founder have a technical background?",
        "Did the founder attend a top-50 university?",
        "Has the founder worked at a company with more than 5,000 employees?",
        "Does the founder have deep experience in the startup's industry?",
    ]

    def write(request):
        return {"questions": questions} if request.schema is not None else "Instructions."

    with fake_llms(writer=FakeLLM(generate=write)):
        yield


@contextmanager
def kev_server(kev_dir: Path, run: str = KEV_BASE, port: int = 8009, device: str = "cuda",
               dtype: str = "fp32", gpu: str | None = None, log: Path | None = None,
               timeout: float = 1800) -> Iterator[str]:
    """Serve a Kev checkpoint for the block; yields its root URL. fp32 on a T4 (no bf16)."""
    env = {**os.environ, "KEV_DTYPE": dtype}
    env.pop("PYTHONPATH", None)
    if gpu is not None:
        env["CUDA_VISIBLE_DEVICES"] = gpu
    log = log or Path(f"/tmp/kev_serve_{port}.log")
    log.parent.mkdir(parents=True, exist_ok=True)
    python = str(kev_dir / ".venv" / "bin" / "python")
    proc = subprocess.Popen(
        [python, "-m", "kev.serve", "--run", run, "--port", str(port), "--device", device],
        cwd=kev_dir, env=env, stdout=log.open("w"), stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}"
    try:
        t0 = time.time()
        while True:
            if proc.poll() is not None:
                raise RuntimeError(f"kev.serve exited ({proc.returncode}); see {log}")
            try:
                with urllib.request.urlopen(f"{url}/v1/models", timeout=5):
                    break
            except OSError as err:
                if time.time() - t0 > timeout:
                    raise TimeoutError(
                        f"kev.serve not up after {timeout:.0f}s; see {log}") from err
                time.sleep(3)
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            proc.kill()


def usage_rows(usage) -> list[dict]:
    """A TRL Usage as JSON-friendly rows: calls, cache hits, tokens and cost per role."""
    return json.loads(usage.by("role", "model").to_json(orient="records"))
