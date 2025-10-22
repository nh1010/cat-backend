# syntax=docker/dockerfile:1

############################
# Base image with deps
############################
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for psycopg
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

############################
# Development image (reload)
############################
FROM base AS dev
ENV APP_ENV=development \
    PORT=5000
COPY src /app/src
COPY main.py /app/main.py
EXPOSE 5000
CMD ["python", "main.py"]

############################
# Production image
############################
FROM base AS prod
ENV APP_ENV=production \
    PORT=5000
COPY src /app/src
COPY main.py /app/main.py
EXPOSE 5000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "5000"]
