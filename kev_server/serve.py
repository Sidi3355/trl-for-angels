"""Run both Kev servers and the front door on this computer (Windows, macOS or Linux).

    python serve.py

Starts kev.serve twice on localhost (base Kev-0.6B answering on 8009; the production model
deciding on 8010, served raw) and proxy.py on PORT (7860), which routes /answerer and /decider
and checks KEV_API_KEY. Put a tunnel in front of PORT (see README.md) to give the app an
address. Settings come from environment variables:
  KEV_API_KEY      the passcode every request must carry (recommended)
  DECIDER_MODEL    the production model's Hugging Face repo id (default: base Kev as stand-in)
  ANSWERER_MODEL   default jaredpalmer/kev-0.6b
  DEVICE           cpu (default), or cuda on a PC with an NVIDIA GPU
  PORT, HOST       7860 and 127.0.0.1 by default (HOST=0.0.0.0 inside Docker)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def kev(run: str, port: int, raw: bool) -> subprocess.Popen:
    env = {**os.environ, "KEV_DTYPE": os.environ.get("KEV_DTYPE", "fp32"),
           "TOKENIZERS_PARALLELISM": "false"}
    env.pop("KEV_API_KEY", None)  # the front door checks the key; the backends stay local
    if raw:
        env["KEV_TEMPERATURE"] = "1.0"  # the app applies the per-question temperatures
    return subprocess.Popen([sys.executable, "-m", "kev.serve", "--run", run, "--port",
                             str(port), "--device", os.environ.get("DEVICE", "cpu")], env=env)


def main() -> int:
    answerer = os.environ.get("ANSWERER_MODEL", "jaredpalmer/kev-0.6b")
    decider = os.environ.get("DECIDER_MODEL") or "jaredpalmer/kev-0.6b"
    if not os.environ.get("KEV_API_KEY"):
        print("warning: KEV_API_KEY isn't set, so anyone with the address can call Kev",
              flush=True)
    procs = [kev(answerer, 8009, raw=False), kev(decider, 8010, raw=True)]
    print(f"answerer: {answerer}\ndecider:  {decider}"
          + ("" if os.environ.get("DECIDER_MODEL") else " (stand-in: set DECIDER_MODEL)"),
          flush=True)
    try:
        import uvicorn

        sys.path.insert(0, str(HERE))
        uvicorn.run("proxy:app", host=os.environ.get("HOST", "127.0.0.1"),
                    port=int(os.environ.get("PORT", "7860")))
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=30)
            except subprocess.TimeoutExpired:
                p.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
