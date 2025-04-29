FROM python:3.9

ENV PYTHONBUFFERED 1

RUN apt-get update \
  # dependencies for building Python packages
  && apt-get install -y build-essential \
  # psycopg2 dependencies
  && apt-get install -y libpq-dev \
  # Translations dependencies
  && apt-get install -y gettext \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

RUN apt-get update && apt-get install -y imagemagick

RUN apt-get install -y git


RUN apt-get install espeak-ng -y
WORKDIR /app

COPY requirements/docker_requirements.txt .




RUN python -m pip install --upgrade pip




RUN pip install -r docker_requirements.txt --ignore-installed



COPY scripts/startdjango.sh /startdjango
COPY scripts/setupdjango.sh /setupdjango
COPY scripts/startceleryworker.sh /startceleryworker



RUN sed -i 's/\r$//g' /setupdjango
RUN chmod +x /setupdjango



RUN sed -i 's/\r$//g' /startceleryworker
RUN chmod +x /startceleryworker



EXPOSE 8000