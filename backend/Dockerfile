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
      torch==2.5.1 \
      torchvision==0.20.1 \
      torchaudio==2.5.1 \
      --index-url https://download.pytorch.org/whl/cpu

RUN apt-get update && apt-get install -y --no-install-recommends \
      default-libmysqlclient-dev pkg-config \
  && rm -rf /var/lib/apt/lists/*

COPY requirements/build.txt ./
RUN pip install -r build.txt

COPY requirements/requirements.txt requirements/constraints.txt ./


RUN PIP_CONSTRAINT=constraints.txt pip install --no-build-isolation -r requirements.txt


FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg \
      imagemagick \
      # opencv needs these; the slim image does not carry them
      libgl1 \
      libglib2.0-0 \
      libsm6 \
      libxext6 \
      libxrender1 \
  && rm -rf /var/lib/apt/lists/*

# moviepy draws text by handing ImageMagick an `@/tmp/<file>` path, which Debian's
# policy.xml forbids — failing every subtitle. Drop that one rule only.
RUN for policy in /etc/ImageMagick-*/policy.xml; do \
      if [ -f "$policy" ]; then sed -i '/pattern="@\*"/d' "$policy"; fi; \
    done

RUN apt-get update && apt-get install -y --no-install-recommends libmariadb3 \
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
