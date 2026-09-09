FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    libglib2.0-0 \
    libxcb1 \
    libxcb-render0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    libgl1 \
    libx11-6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.in .
RUN pip install --no-cache-dir -r requirements.in

COPY src/ ./src

CMD ["python", "src/main.py"]