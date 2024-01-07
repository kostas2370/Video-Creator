FROM python:3.9.5

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


WORKDIR /app

COPY ../requirements.txt .


RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt


COPY startdjango.sh /startdjango
COPY startceleryworker.sh /startceleryworker
COPY startcelerybeat.sh /startcelerybeat

RUN sed -i 's/\r$//g' /startdjango
RUN chmod +x /startdjango
RUN sed -i 's/\r$//g' /startceleryworker
RUN chmod +x /startceleryworker
RUN sed -i 's/\r$//g' /startcelerybeat
RUN chmod +x /startcelerybeat


EXPOSE 8000