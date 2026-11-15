"""Turn the raw screencast segments (raw/<segment>/frames.json + JPEGs, variable frame rate) into the demo video's
clips: constant 30 fps JPEG sequences at 804x1748 in clips/<name>/000001.jpg..., with clips/<name>/meta.json.

    python3 tools/frames-to-clips.py            # every clip in CLIPS
    python3 tools/frames-to-clips.py c2_research

A clip is one or more segments played in order (a jump cut between them), optionally sped up (speed > 1, shown
in the video with a "sped up" badge) or fitted to a length (fit_s: speed chosen so the clip lasts that long).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RAW, OUT = HERE / "raw", HERE / "clips"
W, H, FPS = 804, 1748, 30

CLIPS = {
    "c1_type": {"segments": ["c1_type"]},
    "c2_research": {"segments": ["c2_research"], "fit_s": 10.0},
    "c3_profile": {"segments": ["c3_profile"]},
    "c4_verdict": {"segments": ["c4_verdict"]},
    "c5_bar": {"segments": ["c5_bar"]},
    "c6_whatif": {"segments": ["c6a_factors", "c6b_whatif"]},
    "c7_list": {"segments": ["c7_list"]},
    "c8_voice": {"segments": ["c8a_record", "c8b_filled"]},
    "c9_notify": {"segments": ["c9_notify"]},
    "c10_profile": {"segments": ["c10_profile"]},
}


def seconds(seg: str) -> float:
    d = json.loads((RAW / seg / "frames.json").read_text())
    return d["end"] - d["frames"][0]["t"] if d["frames"] else 0.0


def render_segment(seg: str, speed: float, out: Path) -> int:
    d = json.loads((RAW / seg / "frames.json").read_text())
    frames, end = d["frames"], d["end"]
    if not frames:
        raise SystemExit(f"{seg}: no frames")
    lines = ["ffconcat version 1.0"]
    for i, f in enumerate(frames):
        nxt = frames[i + 1]["t"] if i + 1 < len(frames) else end
        lines += [f"file '{(RAW / seg / f['file']).as_posix()}'", f"duration {max(nxt - f['t'], 0.001):.4f}"]
    lines.append(f"file '{(RAW / seg / frames[-1]['file']).as_posix()}'")  # the concat demuxer needs the last file twice
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as lst:
        lst.write("\n".join(lines) + "\n")
    out.mkdir(parents=True, exist_ok=True)
    vf = (f"setpts=PTS/{speed},fps={FPS},scale={W}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0xeeeeea")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst.name, "-vf", vf,
                    "-q:v", "3", str(out / "%06d.jpg")], check=True)
    Path(lst.name).unlink()
    return len(list(out.glob("*.jpg")))


def build(name: str, spec: dict) -> dict:
    total = sum(seconds(s) for s in spec["segments"])
    speed = spec.get("speed") or (round(max(total / spec["fit_s"], 1.0), 1) if spec.get("fit_s") else 1.0)
    dest = OUT / name
    keep = [p for p in dest.glob("placeholder*")] if dest.exists() else []
    saved = {p.name: p.read_bytes() for p in keep}
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    for n, b in saved.items():
        (dest / n).write_bytes(b)
    n = 0
    for seg in spec["segments"]:
        with tempfile.TemporaryDirectory() as tmp:
            render_segment(seg, speed, Path(tmp))
            for f in sorted(Path(tmp).glob("*.jpg")):
                n += 1
                shutil.move(str(f), dest / f"{n:06d}.jpg")
    meta = {"frames": n, "fps": FPS, "speed": speed, "seconds": round(n / FPS, 2), "source_seconds": round(total, 1),
            "segments": spec["segments"]}
    (dest / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


if __name__ == "__main__":
    names = sys.argv[1:] or list(CLIPS)
    for name in names:
        print(name, build(name, CLIPS[name]))
