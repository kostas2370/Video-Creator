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


WORKDIR /app

COPY ../production_requirements.txt .


RUN python -m pip install --upgrade pip
RUN pip install -r production_requirements.txt


COPY startdjango.sh /startdjango


RUN sed -i 's/\r$//g' /startdjango
RUN chmod +x /startdjango



EXPOSE 8000