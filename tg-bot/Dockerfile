FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    sox \
    libsox-dev \
    libsox-fmt-all \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x init.sh

# Создаём директории, но не скачиваем модель при сборке
RUN mkdir -p /app/data/ics_files /app/voice

CMD ["sh", "-c", "./init.sh && python bot.py"]
