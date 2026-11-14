import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from screener.config import Settings
from screener.contract import REPO_ROOT, get_contract
from screener.main import create_app

CONTRACT_DIR = REPO_ROOT / "app" / "contract"
EXAMPLES = CONTRACT_DIR / "examples"
MOCKS = CONTRACT_DIR / "mocks"


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    """Tests see only the settings they pass, never keys or switches set in the real environment."""
    names = {f.upper() for f in Settings.model_fields} | {"SCREENER_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"}
    for name in names:
        monkeypatch.delenv(name, raising=False)


def load(path: Path):
    return json.loads(path.read_text())


def make_client(**overrides) -> TestClient:
    settings = Settings(_env_file=None, mock_pace=0, **overrides)
    return TestClient(create_app(settings))


@pytest.fixture
def client():
    with make_client() as c:
        yield c


@pytest.fixture(scope="session")
def contract():
    return get_contract(CONTRACT_DIR)


def wait_for(client: TestClient, url: str, key: str = "status", done=("complete", "failed", "partial"), timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        doc = client.get(url).json()
        if doc.get(key) in done:
            return doc
        time.sleep(0.02)
    raise AssertionError(f"{url} didn't finish in {timeout}s: {doc}")


def screen(client: TestClient, body: dict) -> tuple[dict, dict]:
    r = client.post("/v1/screenings", json=body)
    assert r.status_code == 202, r.text
    job = wait_for(client, f"/v1/screenings/{r.json()['job_id']}")
    assert job["status"] == "complete", job
    return job, client.get(job["memo_url"]).json()


def parse_sse(text: str) -> list[dict]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line and not line.startswith(":"))
        if "data" in lines:
            ev = json.loads(lines["data"])
            assert int(lines["id"]) == ev["seq"] and lines["event"] == ev["type"]
            events.append(ev)
    return events
