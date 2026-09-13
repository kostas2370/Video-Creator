# Two stages: the builder owns the compilers and the git checkouts, and only the
# finished virtualenv is carried into the runtime image.
FROM python:3.9-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      # two requirements are installed straight from git
      git \
      # headers for any sdist that has no wheel for this interpreter
      libjpeg-dev \
      zlib1g-dev \
  && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN python -m pip install --upgrade pip

# CPU-only torch, installed before anything that depends on it.
#
# The default PyPI wheels pull the CUDA runtime in as separate nvidia-* packages
# (cudnn 770MB + cublas 581MB + cusolver 338MB + the rest, roughly 2.5GB) and none
# of it can ever run: no service in docker-compose reserves a GPU, and SadTalker
# checks torch.cuda.is_available() and falls back to CPU. See inference.py.
RUN pip install \
      torch==2.5.1+cpu \
      torchvision==0.20.1+cpu \
      torchaudio==2.5.1+cpu \
      --index-url https://download.pytorch.org/whl/cpu

COPY requirements/docker_requirements.txt requirements/constraints.txt ./

# The constraints stop coqui-tts, basicsr, facexlib or gfpgan quietly pulling a
# CUDA build of torch back in over the CPU one.
RUN PIP_CONSTRAINT=constraints.txt pip install -r docker_requirements.txt


FROM python:3.9-slim

# The original spelling of this was PYTHONBUFFERED, which Python ignores.
ENV PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg \
      imagemagick \
      espeak-ng \
      # opencv needs these; the slim image does not carry them
      libgl1 \
      libglib2.0-0 \
      libsm6 \
      libxext6 \
      libxrender1 \
  && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

COPY scripts/startdjango.sh /startdjango
COPY scripts/setupdjango.sh /setupdjango
COPY scripts/startceleryworker.sh /startceleryworker
COPY scripts/startcelerybeat.sh /startcelerybeat

RUN sed -i 's/\r$//g' /startdjango /setupdjango /startceleryworker /startcelerybeat \
  && chmod +x /startdjango /setupdjango /startceleryworker /startcelerybeat

EXPOSE 8000
