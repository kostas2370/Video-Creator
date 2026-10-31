FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 HF_HOME=/models
WORKDIR /service
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
EXPOSE 9000
CMD ["python", "server.py"]
