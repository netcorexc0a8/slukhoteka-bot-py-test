# Slukhoteka - Система управления расписанием

Система управления расписанием специалистов и записи клиентов через Telegram и VK с единым расписанием, ролевым доступом и синхронизацией с внешними сервисами.

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                         Клиенты                             │
│  ┌──────────────┐              ┌──────────────┐             │
│  │ TG Client    │              │ VK Client    │             │
│  └──────────────┘              └──────────────┘             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Боты (Polling)                         │
│  ┌──────────────┐              ┌──────────────┐             │
│  │ slukhoteka-  │              │ slukhoteka-  │             │
│  │ tg-bot       │              │ vk-bot       │             │
│  └──────┬───────┘              └──────┬───────┘             │
└─────────┬──────────────────────────────┬────────────────────┘
          │                              │
          └──────────┬───────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Backend API (FastAPI)                          │
│         ┌────────────────────────────┐                      │
│         │  slukhoteka-backend        │                      │
│         │  - Auth & Roles            │                      │
│         │  - Schedule CRUD           │                      │
│         │  - Invite Codes            │                      │
│         │  - Export (Excel/ICS)      │                      │
│         │  - Sync (Yandex Disk)      │                      │
│         └────────────┬───────────────┘                      │
└──────────────────────┼──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              PostgreSQL DB                                  │
│         ┌────────────────────────────┐                      │
│         │  slukhoteka-db             │                      │
│         │  - global_users            │                      │
│         │  - platform_users          │                      │
│         │  - schedules               │                      │
│         │  - invite_codes            │                      │
│         └────────────────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Установка

### Требования

- Docker 20.10+
- Docker Compose 2.0+

### Шаги установки

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd slukhoteka-tg-bot-py_v2
```

2. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

3. Отредактируйте `.env` файл, заполнив необходимые значения:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
VK_BOT_TOKEN=your_vk_bot_token
VK_GROUP_ID=your_vk_group_id
YANDEX_DISK_TOKEN=your_yandex_disk_token
ADMIN_USER_PH=+79001234567
```

4. Запустите контейнеры:
```bash
docker compose up -d
```

5. Проверьте статус контейнеров:
```bash
docker compose ps
```

## 🚀 Использование

### Telegram Bot

1. Найдите бота в Telegram и отправьте команду `/start`
2. Нажмите кнопку "📱 Поделиться номером" для автоматической авторизации
3. Если ваш номер указан в `ADMIN_USER_PH`, вы получите роль `admin`, иначе `specialist`
4. Используйте меню для работы с расписанием

### VK Bot

1. Добавьте бота в вашу группу VK
2. Напишите `start` в диалоге с ботом
3. Бот попытается автоматически получить ваш номер телефона из профиля VK
4. Если номер не удалось получить автоматически, введите его в формате `+7XXXXXXXXXX`
5. Используйте меню для работы с расписанием

## 📋 Функционал

### Роли пользователей

#### Admin
- Полный доступ ко всем функциям
- Управление пользователями
- CRUD всех расписаний
- Экспорт всех данных
- Синхронизация
- Резервное копирование

#### Methodist
- CRUD всех расписаний
- Управление пользователями (кроме Admin)
- Экспорт всех данных
- Синхронизация

#### Specialist
- CRUD только своих расписаний
- Экспорт только своих данных
- Синхронизация

### Возможности

- **Автоматическая авторизация**: получение номера телефона из Telegram (через кнопку) и VK (из профиля)
- **Расписание**: просмотр, создание, изменение, перенос, удаление записей
- **Экспорт**: выгрузка в Excel и ICS формат
- **Синхронизация**: автоматическая и принудительная выгрузка на Яндекс Диск
- **Голосовые сообщения**: распознавание речи через Vosk (Telegram)
- **Inline календарь**: удобный выбор дат в обоих ботах

## 🐳 Docker контейнеры

- `slukhoteka-db`: PostgreSQL 15
- `slukhoteka-backend`: FastAPI приложение
- `slukhoteka-tg-bot`: Telegram бот на aiogram
- `slukhoteka-vk-bot`: VK бот на requests
- `slukhoteka-aggregator`: Фоновые задачи (синхронизация)

## 🔧 Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота | - |
| `VK_BOT_TOKEN` | Токен VK бота | - |
| `VK_GROUP_ID` | ID группы VK | - |
| `YANDEX_DISK_TOKEN` | Токен Яндекс Диска | - |
| `ADMIN_USER_PH` | Телефоны админов (через запятую) | - |
| `START_HOUR` | Начало рабочего дня | 0 |
| `END_HOUR` | Конец рабочего дня | 23 |
| `TIME_SLOT_DURATION` | Длительность слота (часы) | 1 |
| `COLOR_FREE` | Цвет свободного слота | 🟩 |
| `COLOR_BUSY` | Цвет занятого слота | 🟨 |

## 📊 API

Backend API доступен по адресу `http://localhost:8000`

Документация Swagger: `http://localhost:8000/docs`

### Основные эндпоинты

- `POST /api/v1/auth/login` - Авторизация
- `GET /api/v1/schedules` - Получить расписание
- `POST /api/v1/schedules` - Создать запись
- `PUT /api/v1/schedules/{id}` - Обновить запись
- `DELETE /api/v1/schedules/{id}` - Удалить запись
- `GET /api/v1/export/excel` - Экспорт в Excel

## 🔒 Безопасность

- Нормализация телефонов
- Ролевая система доступа
- Валидация данных на Backend
- Soft delete для расписаний

## 📝 Требования к хосту

### Минимальные требования
- CPU: 1 ядро
- RAM: 512 MB
- Диск: 5 GB
- OS: Linux (Ubuntu 20.04+)

### Рекомендуемые требования
- CPU: 2 ядра
- RAM: 1 GB
- Диск: 10 GB
- OS: Linux (Ubuntu 22.04+)

## 🛠️ Разработка

### Структура проекта

```
slukhoteka/
├── backend/          # FastAPI Backend
├── tg-bot/           # Telegram Bot
├── vk-bot/           # VK Bot
├── aggregator/       # Фоновые задачи
├── docker-compose.yml
├── .env.example
└── README.md
```

### Запуск в режиме разработки

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Telegram Bot
cd tg-bot
pip install -r requirements.txt
python bot.py

# VK Bot
cd vk-bot
pip install -r requirements.txt
python bot.py

# Aggregator
cd aggregator
pip install -r requirements.txt
python main.py
```

## 🐛 Troubleshooting

### Бот не отвечает

1. Проверьте логи контейнера:
```bash
docker compose logs slukhoteka-tg-bot
```

2. Проверьте, что токен бота правильный

3. Перезапустите контейнер:
```bash
docker compose restart slukhoteka-tg-bot
```

### Ошибка подключения к БД

1. Проверьте статус контейнера БД:
```bash
docker compose ps slukhoteka-db
```

2. Проверьте логи БД:
```bash
docker compose logs slukhoteka-db
```

3. Убедитесь, что параметры подключения в `.env` правильные

## 📄 Лицензия

MIT License

## 👥 Поддержка

Для вопросов и предложений создайте issue в репозитории.
