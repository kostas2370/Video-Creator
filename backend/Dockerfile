# Two stages: the builder owns the compilers and the git checkouts, and only the
# finished virtualenv is carried into the runtime image.
FROM node:24.22.3-bookworm-slim AS node-runtime

FROM python:3.11-slim AS builder

ARG WITH_SADTALKER=true

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


RUN if [ "$WITH_SADTALKER" = "true" ]; then pip install \
      torch==2.14.1 \
      torchvision==0.29.1 \
      --index-url https://download.pytorch.org/whl/cpu; fi

COPY requirements/build.txt ./
RUN pip install -r build.txt

COPY requirements/ ./requirements/


RUN case "$WITH_SADTALKER" in \
      true) requirements_file=requirements/requirements.txt ;; \
      false) requirements_file=requirements/runtime.txt ;; \
      *) exit 2 ;; \
    esac \
    && PIP_CONSTRAINT=requirements/constraints.txt pip install --no-build-isolation -r "$requirements_file"

COPY --from=node-runtime /usr/local/bin/node /opt/venv/lib/python3.11/site-packages/nodejs_wheel/bin/node
RUN rm -rf /opt/venv/lib/python3.11/site-packages/nodejs_wheel/lib/node_modules


FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN /usr/local/bin/python -m pip install --no-cache-dir --upgrade pip 'setuptools>=83' 'wheel>=0.46.2'

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
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

COPY scripts/startdjango.sh /startdjango
COPY scripts/setupdjango.sh /setupdjango
COPY scripts/startceleryrender.sh /startceleryrender
COPY scripts/startceleryworker.sh /startceleryworker
COPY scripts/startcelerybeat.sh /startcelerybeat

RUN sed -i 's/\r$//g' /startdjango /setupdjango /startceleryworker /startcelerybeat /startceleryrender \
  && chmod +x /startdjango /setupdjango /startceleryworker /startcelerybeat /startceleryrender

EXPOSE 8000
