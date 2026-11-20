# Two stages: the builder owns the compilers and the git checkouts, and only the
# finished virtualenv is carried into the runtime image.
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      git \
      libjpeg-dev \
      zlib1g-dev \
  && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN python -m pip install --upgrade pip


RUN pip install \
      torch==2.14.1 \
      torchvision==0.29.1 \
      --index-url https://download.pytorch.org/whl/cpu

COPY requirements/build.txt ./
RUN pip install -r build.txt

COPY requirements/requirements.txt requirements/constraints.txt ./


RUN PIP_CONSTRAINT=constraints.txt pip install --no-build-isolation -r requirements.txt


FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg \
      fonts-dejavu-core \
      # opencv needs these; the slim image does not carry them
      libgl1 \
      libglib2.0-0 \
      libsm6 \
      libxext6 \
      libxrender1 \
  && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

COPY scripts/release.sh /release
COPY scripts/healthcheck.py /healthcheck.py
COPY scripts/startdjango.sh /startdjango
COPY scripts/setupdjango.sh /setupdjango
COPY scripts/startceleryrender.sh /startceleryrender
COPY scripts/startceleryworker.sh /startceleryworker
COPY scripts/startcelerybeat.sh /startcelerybeat

RUN sed -i 's/\r$//g' /release /startdjango /setupdjango /startceleryworker /startcelerybeat /startceleryrender \
  && chmod +x /release /startdjango /setupdjango /startceleryworker /startcelerybeat /startceleryrender

EXPOSE 8000

# Production packages application code; development keeps its existing bind mount.
FROM runtime AS production
ENV ENV=prod \
    PYTHONDONTWRITEBYTECODE=1 \
    TMPDIR=/app/private-render-cache/tmp \
    XDG_CACHE_HOME=/app/private-render-cache/libraries \
    HOME=/tmp
COPY apps /app/apps
COPY assets /app/assets
COPY fixtures /app/fixtures
COPY vendor /app/vendor
COPY video_creator /app/video_creator
COPY manage.py __init__.py /app/
RUN groupadd --gid 10001 viddie \
    && useradd --uid 10001 --gid viddie --no-create-home viddie \
    && mkdir -p media private-clips private-publishing private-render-cache/tmp private-render-cache/libraries \
        checkpoints gfpgan/weights results staticfiles \
    && chown -R viddie:viddie media private-clips private-publishing \
        private-render-cache checkpoints gfpgan results staticfiles
USER viddie
CMD ["/startdjango"]

# Preserve the lightweight development image as the default build target.
FROM runtime AS development
