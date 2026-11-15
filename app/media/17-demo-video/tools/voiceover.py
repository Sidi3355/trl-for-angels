"""Generate the demo video's voiceover from script.json with ElevenLabs (text to speech with timestamps).

    app/backend/.venv/bin/python tools/voiceover.py            # every section
    app/backend/.venv/bin/python tools/voiceover.py s8_close   # one section again

- Sections are generated in order with request stitching (previous_request_ids), so they flow as one read.
- The voice reads "Halo-mark" (said HAY-lo-mark); the alignment files drop that hyphen, so captions show
  "Halomark".
- The closing section is generated TAKES times; the take whose last words fall lowest in pitch, compared with
  the rest of the line, is kept, so the video ends on a low, grave tone.
The key comes from the environment's network proxy (or ELEVENLABS_API_KEY); it's never written here.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
import numpy as np

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "voiceover"
API = "https://api.elevenlabs.io/v1"
KEY = os.environ.get("ELEVENLABS_API_KEY") or "sk_proxyinjected0000000000000000000000000000000000000"
SETTINGS = {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0, "use_speaker_boost": True}
CLOSE_ID, TAKES = "s8_close", 3


def tts_text(text: str) -> str:
    return text.replace("Halomark", "Halo-mark")


def display_alignment(al: dict, spoken: str) -> dict:
    """Drop the hyphens added for pronunciation, so the alignment spells what the captions show."""
    chars = al["characters"]
    if "".join(chars) != spoken:
        raise SystemExit(f"alignment text differs from the request: {''.join(chars)[:80]!r}")
    drop, i = set(), spoken.find("Halo-mark")
    while i != -1:
        drop.add(i + 4)
        i = spoken.find("Halo-mark", i + 1)
    keep = [k for k in range(len(chars)) if k not in drop]
    return {name: [al[name][k] for k in keep] for name in ("characters", "character_start_times_seconds",
                                                              "character_end_times_seconds")}


def speak(client: httpx.Client, d: dict, text: str, previous: list[str], seed: int | None = None) -> tuple[bytes, dict, str]:
    body = {"text": text, "model_id": d["model_id"], "voice_settings": SETTINGS, "previous_request_ids": previous[-3:]}
    if seed is not None:
        body["seed"] = seed
    r = client.post(f"{API}/text-to-speech/{d['voice_id']}/with-timestamps", params={"output_format": "mp3_44100_128"},
                    headers={"xi-api-key": KEY}, json=body)
    if r.status_code != 200:
        raise SystemExit(f"ElevenLabs {r.status_code}: {r.text[:300]}")
    j = r.json()
    print(f"  {len(text)} characters charged: {r.headers.get('x-character-count', '?')}")
    return base64.b64decode(j["audio_base64"]), j["alignment"], r.headers.get("request-id", "")


def pcm(mp3: Path, rate: int = 16000) -> np.ndarray:
    raw = subprocess.check_output(["ffmpeg", "-loglevel", "error", "-i", str(mp3), "-f", "f32le", "-ac", "1", "-ar",
                                   str(rate), "-"])
    return np.frombuffer(raw, dtype=np.float32)


def pitch(x: np.ndarray, rate: int = 16000) -> float | None:
    """Median F0 of a stretch of speech, by autocorrelation per 40 ms frame (voiced frames only)."""
    f0s, n = [], int(0.04 * rate)
    for s in range(0, len(x) - n, n // 2):
        fr = x[s:s + n] - x[s:s + n].mean()
        if np.sqrt((fr ** 2).mean()) < 0.02:
            continue
        ac = np.correlate(fr, fr, "full")[n - 1:]
        lo, hi = rate // 300, rate // 60  # 60-300 Hz
        lag = lo + int(np.argmax(ac[lo:hi]))
        if ac[lag] > 0.3 * ac[0]:
            f0s.append(rate / lag)
    return float(np.median(f0s)) if f0s else None


def fall(mp3: Path, al: dict, words: str = "investment advice") -> float:
    """How far the last words sit below the rest of the line, in semitones (bigger is lower)."""
    text, starts = "".join(al["characters"]), al["character_start_times_seconds"]
    t = starts[text.rfind(words)]
    x, rate = pcm(mp3), 16000
    tail, head = pitch(x[int(t * rate):], rate), pitch(x[:int(t * rate)], rate)
    return 12 * np.log2(head / tail) if tail and head else float("-inf")


def main(only: list[str]) -> None:
    d = json.loads((HERE / "script.json").read_text())
    OUT.mkdir(exist_ok=True)
    ids_file = OUT / "request_ids.json"
    ids = json.loads(ids_file.read_text()) if ids_file.exists() else {}
    durations = json.loads((OUT / "durations.json").read_text()) if (OUT / "durations.json").exists() else {}
    with httpx.Client(timeout=180) as client:
        previous: list[str] = []
        for s in d["sections"]:
            sid, spoken = s["id"], tts_text(s["text"])
            if only and sid not in only:
                if ids.get(sid):
                    previous.append(ids[sid])
                continue
            print(sid)
            if sid == CLOSE_ID:
                takes = []
                for seed in range(1, TAKES + 1):
                    audio, al, rid = speak(client, d, spoken, previous, seed=seed)
                    path = OUT / f"{sid}.take{seed}.mp3"
                    path.write_bytes(audio)
                    takes.append((fall(path, al), seed, audio, al, rid))
                    print(f"  take {seed}: last words {takes[-1][0]:+.1f} semitones below the line")
                _, seed, audio, al, rid = max(takes, key=lambda t: t[0])
                print(f"  kept take {seed}")
            else:
                audio, al, rid = speak(client, d, spoken, previous)
            (OUT / f"{sid}.mp3").write_bytes(audio)
            (OUT / f"{sid}.alignment.json").write_text(json.dumps(display_alignment(al, spoken)))
            dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                                 "csv=p=0", str(OUT / f"{sid}.mp3")]).decode())
            durations[sid] = round(dur, 2)
            ids[sid] = rid
            previous.append(rid)
            print(f"  {dur:.2f} s")
    (OUT / "durations.json").write_text(json.dumps(durations, indent=1) + "\n")
    ids_file.write_text(json.dumps(ids, indent=1) + "\n")
    print("total", round(sum(durations.values()), 1), "s")


if __name__ == "__main__":
    main(sys.argv[1:])
