FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.in .
RUN pip install --no-cache-dir -r requirements.in

COPY src/ ./src

CMD ["fastmcp", "run", "src/server.py", "--transport", "sse", "--port", "9001"]