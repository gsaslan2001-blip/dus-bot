FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# System dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (cached layer)
COPY requirements-bot.txt ./
RUN pip install --no-cache-dir -r requirements-bot.txt

# Application code
COPY scripts/ ./scripts/
COPY bot/ ./bot/

# Run
CMD ["python", "-m", "bot.main"]
