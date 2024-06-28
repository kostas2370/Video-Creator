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

RUN apt-get install espeak-ng -y
WORKDIR /app

COPY requirements/docker_requirements.txt .


RUN python -m pip install --upgrade pip
RUN pip install -r docker_requirements.txt


COPY startdjango.sh /startdjango


RUN sed -i 's/\r$//g' /startdjango
RUN chmod +x /startdjango



EXPOSE 8000