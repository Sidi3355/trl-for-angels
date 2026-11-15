FROM python:3.13-slim
# A non-root user (uid 1000, as Hugging Face Spaces and most hosts expect).
RUN useradd -m -u 1000 user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH HF_HOME=/home/user/.cache/huggingface \
    KEV_DTYPE=fp32 TOKENIZERS_PARALLELISM=false HOST=0.0.0.0
WORKDIR /home/user/app
# CPU-only PyTorch (Kev needs torch >= 2.6, < 2.9), then Kev at the commit the research used.
RUN pip install --no-cache-dir torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir \
       "kev[serve] @ https://github.com/jaredpalmer/kev/archive/2074cc44256200bb37540103fa4572901faa10f3.tar.gz" "httpx>=0.28,<1"
COPY --chown=user . .
USER user
CMD ["bash", "start.sh"]
