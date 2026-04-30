-- Migration: Make clients.phone optional
-- Date: 2026-04-29
-- Phone-поле клиента в текущей бизнес-логике не используется, делаем nullable.
-- Поле не удаляется на случай будущей реализации (уведомления, поиск).

ALTER TABLE clients ALTER COLUMN phone DROP NOT NULL;
