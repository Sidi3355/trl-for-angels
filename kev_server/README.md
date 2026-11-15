# Kev server for the trl-for-angels app

Runs the two Kev models the app needs, on your own computer, behind one front door:

| Path | Model | Role |
|---|---|---|
| `/answerer/v1/systemone` | `jaredpalmer/kev-0.6b` (base) | answers TRL's yes/no questions about a founder |
| `/decider/v1/systemone` | the production model (`DECIDER_MODEL`) | outcome and years distributions, **raw**: the app applies the per-question temperatures from `model.json` |

Both are Kev's own server (`kev.serve`, Kev commit `2074cc4`), in fp32 on the CPU. A free
Cloudflare tunnel gives the app a web address for it. `GET /health` says whether both have
loaded, and whether the decider is still base Kev standing in for the production model.

Hugging Face Spaces that run code now need a paid PRO plan, so this runs on your PC for the
demo instead. The trained model itself is stored free on Hugging Face.

## Windows: one-time setup (about 10 minutes)

You need about **8 GB of free memory**: each model takes roughly 3 GB. Open **PowerShell**:

```powershell
# 1. uv, a Python installer
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen PowerShell, then go to this folder (`kev_server` in the downloaded repo):

```powershell
# 2. A Python 3.13 environment with CPU PyTorch and Kev
uv venv --python 3.13
uv pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
uv pip install "kev[serve] @ https://github.com/jaredpalmer/kev/archive/2074cc44256200bb37540103fa4572901faa10f3.tar.gz" "httpx>=0.28,<1"

# 3. The tunnel program
winget install --id Cloudflare.cloudflared
```

## Each time you demo

Window 1, in this folder:

```powershell
$env:KEV_API_KEY = "<your passcode>"            # the same passcode the app's backend has
$env:DECIDER_MODEL = "Sidi3355/trl-for-angels-kev-prod"   # the production model (D3)
uv run python serve.py
```

The first start downloads the models (about 2.5 GB); later starts take about a minute.
Wait until it prints `Application startup complete`.

Window 2:

```powershell
cloudflared tunnel --url http://localhost:7860
```

It prints an address like `https://<random-words>.trycloudflare.com`. That's Kev's address
for the app. It changes every time you start the tunnel, so give the new one to the app's
backend each time. Check it in a browser: `<address>/health` should say `"ready": true`.

Keep the PC awake and both windows open while you use the app.

## Other ways to run it

- **macOS or Linux:** the same steps, with `export` instead of `$env:`, and
  `brew install cloudflared` (macOS) for the tunnel.
- **Docker** (any always-on server): `docker build -t kev-server .` and run it with
  `-p 7860:7860 -e KEV_API_KEY=... -e DECIDER_MODEL=...`.
- **NVIDIA GPU:** set `$env:DEVICE = "cuda"` and install the CUDA build of PyTorch instead.
