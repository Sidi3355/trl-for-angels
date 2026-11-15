"""Turn the raw screencast segments (raw/<segment>/frames.json + JPEGs, variable frame rate) into the demo video's
clips: constant 30 fps JPEG sequences at 804x1748 in clips/<name>/000001.jpg..., with clips/<name>/meta.json.

    python3 tools/frames-to-clips.py            # every clip in CLIPS
    python3 tools/frames-to-clips.py c2_research

A clip is one or more segments played in order (a jump cut between them). A segment can be cut to part of
itself: {"seg": name, "from": s, "to": s} in source seconds, or {"seg": name, "tail": s} for its last seconds.
A clip can be sped up (speed > 1) or fitted to a length (fit_s: speed chosen so it lasts that long); the video
shows a "sped up" badge for those. Only the live research clip is sped up; the rest play at real speed.
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

# Slot lengths come from scenes/manifest.json (Fable's scenes); a clip longer than its slot is cut by the scene.
CLIPS = {
    "c1_type": {"segments": ["c1_type", {"seg": "c2_research", "to": 4.6}]},  # typing, then the research starting
    "c2_research": {"segments": [{"seg": "c2_research", "from": 4.6}], "fit_s": 12.6},
    "c3_profile": {"segments": [{"seg": "c3_profile", "from": 2.2}]},
    "c4_verdict": {"segments": ["c4_verdict"]},
    "c5_bar": {"segments": ["c5_bar"]},
    "c6_whatif": {"segments": ["c6a_factors", "c6b_whatif"]},
    "c7_list": {"segments": [{"seg": "c7_list", "tail": 2.6}]},
    "c8_voice": {"segments": [{"seg": "c8a_record", "tail": 1.4}, {"seg": "c8b_filled", "tail": 1.65}]},
    "c9_notify": {"segments": [{"seg": "c9_notify", "tail": 2.55}]},
    "c10_profile": {"segments": [{"seg": "c10_profile", "from": 0.3, "to": 3.3}]},
}


def seconds(seg: str) -> float:
    d = json.loads((RAW / seg / "frames.json").read_text())
    return d["end"] - d["frames"][0]["t"] if d["frames"] else 0.0


def part(spec) -> tuple[str, float, float]:
    """(segment, from, to) in source seconds."""
    if isinstance(spec, str):
        return spec, 0.0, seconds(spec)
    total = seconds(spec["seg"])
    if "tail" in spec:
        return spec["seg"], max(0.0, total - spec["tail"]), total
    return spec["seg"], spec.get("from", 0.0), min(spec.get("to", total), total)


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
    parts = [part(s) for s in spec["segments"]]
    total = sum(b - a for _, a, b in parts)
    speed = spec.get("speed") or (round(max(total / spec["fit_s"], 1.0), 1) if spec.get("fit_s") else 1.0)
    dest = OUT / name
    keep = [p for p in dest.glob("placeholder*")] if dest.exists() else []
    saved = {p.name: p.read_bytes() for p in keep}
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    for n, b in saved.items():
        (dest / n).write_bytes(b)
    n = 0
    for seg, a, b in parts:
        with tempfile.TemporaryDirectory() as tmp:
            render_segment(seg, speed, Path(tmp))
            frames = sorted(Path(tmp).glob("*.jpg"))
            lo, hi = round(a / speed * FPS), round(b / speed * FPS)
            for f in frames[lo:hi]:
                n += 1
                shutil.move(str(f), dest / f"{n:06d}.jpg")
    meta = {"frames": n, "fps": FPS, "speed": speed, "seconds": round(n / FPS, 2), "source_seconds": round(total, 1),
            "segments": [{"seg": s, "from": round(a, 2), "to": round(b, 2)} for s, a, b in parts]}
    (dest / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


if __name__ == "__main__":
    names = sys.argv[1:] or list(CLIPS)
    for name in names:
        print(name, build(name, CLIPS[name]))
