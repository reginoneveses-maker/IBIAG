FROM node:22-bookworm-slim AS quote_runtime
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 && rm -rf /var/lib/apt/lists/*
COPY --from=quote_runtime /usr/local/bin/node /usr/local/bin/node
WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

EXPOSE 8000
# No proxy trust by default; opt in only to verified exact proxy addresses.
CMD ["python", "serve.py"]
