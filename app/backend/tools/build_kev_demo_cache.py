"""Build screener/data/kev_demo_cache.json: the real Kev's replies for the three fictional demo founders.

With it, the dashboard's examples answer at once, drivers included, and still work while the Kev server on the
owner's PC is off (the demo-cache backup in research's docs/app_integration.md). It's used only with the
model.json and rules.json it was built for, and only for exactly the same text.

Needs research's kev_server running with both real models (kev_server/README.md on the research branch) and the
real artefacts. Runs each demo founder through the backend exactly as the app does (canned research, then the
real answerer, the verdict and every driver) and saves each reply Kev gave:

    KEV_URL=http://127.0.0.1:7860 KEV_API_KEY=<the server's passcode> ARTIFACTS_DIR=shared/artifacts \\
        app/backend/.venv/bin/python app/backend/tools/build_kev_demo_cache.py

Rebuild it whenever research exports a new model.json or rules.json (the old one is then ignored, not wrong).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from screener.config import Settings  # noqa: E402
from screener.main import create_app  # noqa: E402
from screener.mocks.founders import DEMO_FOUNDERS  # noqa: E402
from screener.pipeline.kev import DEMO_CACHE, KevCache  # noqa: E402

TIMEOUT_S = 20 * 60  # 40 drivers at ~5 s each on a CPU, per founder


def wait(client: TestClient, url: str, key: str, done: tuple[str, ...]) -> dict:
    deadline = time.time() + TIMEOUT_S
    while time.time() < deadline:
        doc = client.get(url).json()
        if doc.get(key) in done:
            return doc
        time.sleep(1)
    sys.exit(f"{url} didn't finish in {TIMEOUT_S} s")


def main(out: Path = DEMO_CACHE) -> int:
    settings = Settings(agent="mock", answerer="kev", decider="kev", kev_demo_cache=False, mock_pace=0)
    with TestClient(create_app(settings)) as client:
        svc = client.app.state.service
        if svc is None:
            sys.exit(f"the backend isn't configured: {client.app.state.errors}")
        p = svc.pipeline
        cache = KevCache(None, model_id=p.artifacts.model["model_id"], rules=p.artifacts.rules, record=True)
        p.answerer.cache = p.decider.cache = cache
        for spec in DEMO_FOUNDERS:
            t0 = time.time()
            job = client.post("/v1/screenings", json=spec["input"]).json()
            job = wait(client, f"/v1/screenings/{job['job_id']}", "status", ("complete", "failed", "partial"))
            if job["status"] != "complete":
                sys.exit(f"{spec['input']['founder']['name']}: {job['error']}")
            memo = wait(client, job["memo_url"], "drivers_status", ("complete", "failed"))
            if memo["drivers_status"] != "complete":
                sys.exit(f"{spec['input']['founder']['name']}: drivers failed")
            v = memo["verdict"]
            print(f"{spec['input']['founder']['name']}: {v['decision']} at {v['probability']:.0%}, "
                  f"{len(memo['drivers'])} drivers, {time.time() - t0:.0f} s")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cache.dump(), indent=1) + "\n")
    print(f"wrote {len(cache.answers)} answer sets and {len(cache.decisions)} decisions to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
