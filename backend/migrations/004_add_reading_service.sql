-- NO_TRANSACTION
-- Migration: Add "Чтение" group subscription
-- ALTER TYPE ... ADD VALUE нельзя в транзакции, поэтому миграция выполняется в autocommit.

ALTER TYPE service_type_enum ADD VALUE IF NOT EXISTS 'reading';

INSERT INTO services (name, description, service_type, max_sessions, max_participants, duration_minutes, is_group, weekly_limit)
VALUES
    ('Чтение на 8 дней', 'Групповое занятие по чтению, ведёт один или несколько специалистов', 'reading', 8, 8, 60, TRUE, TRUE)
ON CONFLICT (service_type) DO NOTHING;