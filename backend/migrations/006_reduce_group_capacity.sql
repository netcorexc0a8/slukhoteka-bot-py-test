-- Migration: Reduce max_participants for groups from 8 to 6
-- Date: 2026-04-30

-- Дефолт для новых групп
ALTER TABLE groups ALTER COLUMN max_participants SET DEFAULT 6;

-- Обновляем существующие группы, у которых max_participants = 8 (значение по умолчанию)
-- Группы, где админ явно поставил другое число — не трогаем.
UPDATE groups SET max_participants = 6 WHERE max_participants = 8;

-- Обновляем справочник услуг (поле services.max_participants)
UPDATE services SET max_participants = 6
WHERE service_type IN ('logorhythmics', 'reading') AND max_participants = 8;
