FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
# Spaces run as uid 1000.
RUN useradd -m -u 1000 user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH HF_HOME=/home/user/.cache/huggingface \
    KEV_DTYPE=fp32 TOKENIZERS_PARALLELISM=false
WORKDIR /home/user/app
# CPU-only PyTorch (Kev needs torch >= 2.6, < 2.9), then Kev at the commit the research used.
RUN pip install --no-cache-dir torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir \
       "kev[serve] @ git+https://github.com/jaredpalmer/kev.git@2074cc4" "httpx>=0.28,<1"
COPY --chown=user . .
USER user
CMD ["bash", "start.sh"]
