#!/bin/bash

# Скрипт инициализации при первом запуске
# Создание директорий и скачивание модели Vosk

echo "Инициализация проекта..."

# Создание директорий
mkdir -p /app/data/ics_files
mkdir -p /app/voice

# Проверка наличия модели Vosk
if [ ! -d "/app/voice/vosk-model-small-ru-0.22" ]; then
    echo "Скачивание модели Vosk..."
    wget https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip -O /tmp/vosk-model-small-ru.zip
    unzip -o /tmp/vosk-model-small-ru.zip -d /app/voice/
    rm /tmp/vosk-model-small-ru.zip
    echo "Модель Vosk загружена"
else
    echo "Модель Vosk уже существует"
fi

echo "Инициализация завершена"
