-- Migration: Subscriptions and Bookings system
-- Date: 2026-04-25
-- Description:
--   - Создаёт справочник services с 5 типами абонементов
--   - Создаёт client_subscriptions, groups, group_participants
--   - Создаёт bookings, booking_specialists
--   - Расширяет clients.phone до VARCHAR(50) (для legacy-фиктивных клиентов)
--   - Переносит данные из schedules в bookings как legacy
--   - Удаляет schedules
--
-- Транзакция управляется в migrate.py (autocommit=False).

-- =========================================================
-- 0. РАСШИРЯЕМ clients.phone (для legacy-меток)
-- =========================================================
ALTER TABLE clients ALTER COLUMN phone TYPE VARCHAR(50);

-- =========================================================
-- 1. SERVICES
-- =========================================================
DO $$ BEGIN
    CREATE TYPE service_type_enum AS ENUM (
        'diagnostics',
        'subscription_1',
        'subscription_4',
        'subscription_8',
        'logorhythmics'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    service_type service_type_enum NOT NULL UNIQUE,
    max_sessions INTEGER NOT NULL,
    max_participants INTEGER,
    duration_minutes INTEGER NOT NULL DEFAULT 60,
    is_group BOOLEAN NOT NULL DEFAULT FALSE,
    weekly_limit BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE
);

ALTER TABLE services ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE services ADD COLUMN IF NOT EXISTS max_sessions INTEGER;
ALTER TABLE services ADD COLUMN IF NOT EXISTS max_participants INTEGER;
ALTER TABLE services ADD COLUMN IF NOT EXISTS duration_minutes INTEGER NOT NULL DEFAULT 60;
ALTER TABLE services ADD COLUMN IF NOT EXISTS is_group BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE services ADD COLUMN IF NOT EXISTS weekly_limit BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE services ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE services ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE services ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE services ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX IF NOT EXISTS ix_services_service_type ON services(service_type);
CREATE INDEX IF NOT EXISTS ix_services_deleted_at ON services(deleted_at);

INSERT INTO services (name, description, service_type, max_sessions, max_participants, duration_minutes, is_group, weekly_limit)
VALUES
    ('Диагностика',           'Разовая консультация',                                           'diagnostics',     1, 1,    60, FALSE, FALSE),
    ('Абонемент на 1 день',   'Индивидуальное занятие, ведёт 1 специалист или методист',        'subscription_1',  1, 1,    60, FALSE, FALSE),
    ('Абонемент на 4 дня',    'Индивидуальное занятие, ведёт 1 специалист или методист',        'subscription_4',  4, 1,    60, FALSE, TRUE),
    ('Абонемент на 8 дней',   'Индивидуальное занятие, ведёт 1 специалист или методист',        'subscription_8',  8, 1,    60, FALSE, TRUE),
    ('Алгоритмика на 8 дней', 'Групповое занятие, ведёт один или несколько специалистов',       'logorhythmics',   8, 8,    60, TRUE,  TRUE)
ON CONFLICT (service_type) DO NOTHING;

-- =========================================================
-- 2. GROUPS
-- =========================================================
CREATE TABLE IF NOT EXISTS groups (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE RESTRICT,
    max_participants INTEGER NOT NULL DEFAULT 8,
    day_of_week INTEGER,
    time VARCHAR(5),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE
);

ALTER TABLE groups ADD COLUMN IF NOT EXISTS service_id INTEGER REFERENCES services(id) ON DELETE RESTRICT;
ALTER TABLE groups ADD COLUMN IF NOT EXISTS max_participants INTEGER NOT NULL DEFAULT 8;
ALTER TABLE groups ADD COLUMN IF NOT EXISTS day_of_week INTEGER;
ALTER TABLE groups ADD COLUMN IF NOT EXISTS time VARCHAR(5);
ALTER TABLE groups ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE groups ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE groups ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE groups ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX IF NOT EXISTS ix_groups_service_id ON groups(service_id);
CREATE INDEX IF NOT EXISTS ix_groups_deleted_at ON groups(deleted_at);

CREATE TABLE IF NOT EXISTS group_participants (
    id SERIAL PRIMARY KEY,
    group_id VARCHAR(100) NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    left_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (group_id, client_id)
);

ALTER TABLE group_participants ADD COLUMN IF NOT EXISTS joined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE group_participants ADD COLUMN IF NOT EXISTS left_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE group_participants ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS ix_group_participants_group_id ON group_participants(group_id);
CREATE INDEX IF NOT EXISTS ix_group_participants_client_id ON group_participants(client_id);

-- =========================================================
-- 3. CLIENT_SUBSCRIPTIONS
-- =========================================================
DO $$ BEGIN
    CREATE TYPE subscription_status_enum AS ENUM ('active', 'completed', 'expired', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS client_subscriptions (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE RESTRICT,
    assigned_specialist_id INTEGER REFERENCES global_users(id) ON DELETE SET NULL,
    group_id VARCHAR(100) REFERENCES groups(id) ON DELETE SET NULL,
    total_sessions INTEGER NOT NULL,
    used_sessions INTEGER NOT NULL DEFAULT 0,
    status subscription_status_enum NOT NULL DEFAULT 'active',
    purchased_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT chk_used_le_total CHECK (used_sessions >= 0 AND used_sessions <= total_sessions),
    CONSTRAINT chk_indiv_xor_group CHECK (
        (assigned_specialist_id IS NOT NULL AND group_id IS NULL)
        OR (assigned_specialist_id IS NULL AND group_id IS NOT NULL)
        OR (assigned_specialist_id IS NOT NULL AND group_id IS NOT NULL)
    )
);

ALTER TABLE client_subscriptions ADD COLUMN IF NOT EXISTS assigned_specialist_id INTEGER REFERENCES global_users(id) ON DELETE SET NULL;
ALTER TABLE client_subscriptions ADD COLUMN IF NOT EXISTS group_id VARCHAR(100) REFERENCES groups(id) ON DELETE SET NULL;
ALTER TABLE client_subscriptions ADD COLUMN IF NOT EXISTS total_sessions INTEGER;
ALTER TABLE client_subscriptions ADD COLUMN IF NOT EXISTS used_sessions INTEGER NOT NULL DEFAULT 0;
ALTER TABLE client_subscriptions ADD COLUMN IF NOT EXISTS status subscription_status_enum NOT NULL DEFAULT 'active';
ALTER TABLE client_subscriptions ADD COLUMN IF NOT EXISTS purchased_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE client_subscriptions ADD COLUMN IF NOT EXISTS valid_until TIMESTAMP WITH TIME ZONE;
ALTER TABLE client_subscriptions ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE client_subscriptions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE client_subscriptions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE client_subscriptions ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX IF NOT EXISTS ix_client_subscriptions_client_id ON client_subscriptions(client_id);
CREATE INDEX IF NOT EXISTS ix_client_subscriptions_service_id ON client_subscriptions(service_id);
CREATE INDEX IF NOT EXISTS ix_client_subscriptions_assigned_specialist_id ON client_subscriptions(assigned_specialist_id);
CREATE INDEX IF NOT EXISTS ix_client_subscriptions_group_id ON client_subscriptions(group_id);
CREATE INDEX IF NOT EXISTS ix_client_subscriptions_status ON client_subscriptions(status);
CREATE INDEX IF NOT EXISTS ix_client_subscriptions_deleted_at ON client_subscriptions(deleted_at);

-- =========================================================
-- 4. BOOKINGS
-- =========================================================
DO $$ BEGIN
    CREATE TYPE booking_type_enum AS ENUM ('individual', 'group');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE booking_status_enum AS ENUM (
        'scheduled',
        'completed',
        'cancelled',
        'missed',
        'specialist_cancelled'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    subscription_id INTEGER REFERENCES client_subscriptions(id) ON DELETE SET NULL,
    service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE RESTRICT,
    specialist_id INTEGER NOT NULL REFERENCES global_users(id) ON DELETE RESTRICT,
    group_id VARCHAR(100) REFERENCES groups(id) ON DELETE SET NULL,

    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,

    booking_type booking_type_enum NOT NULL,
    status booking_status_enum NOT NULL DEFAULT 'scheduled',

    notes TEXT,
    is_recurring BOOLEAN NOT NULL DEFAULT FALSE,
    recurrence_group_id VARCHAR(100),
    session_number INTEGER,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    cancelled_by INTEGER REFERENCES global_users(id) ON DELETE SET NULL,

    CONSTRAINT chk_time_order CHECK (end_time > start_time)
);

ALTER TABLE bookings ADD COLUMN IF NOT EXISTS subscription_id INTEGER REFERENCES client_subscriptions(id) ON DELETE SET NULL;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS service_id INTEGER REFERENCES services(id) ON DELETE RESTRICT;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS group_id VARCHAR(100) REFERENCES groups(id) ON DELETE SET NULL;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS booking_type booking_type_enum;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS status booking_status_enum NOT NULL DEFAULT 'scheduled';
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS is_recurring BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS recurrence_group_id VARCHAR(100);
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS session_number INTEGER;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS cancelled_by INTEGER REFERENCES global_users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_bookings_client_id ON bookings(client_id);
CREATE INDEX IF NOT EXISTS ix_bookings_subscription_id ON bookings(subscription_id);
CREATE INDEX IF NOT EXISTS ix_bookings_service_id ON bookings(service_id);
CREATE INDEX IF NOT EXISTS ix_bookings_specialist_id ON bookings(specialist_id);
CREATE INDEX IF NOT EXISTS ix_bookings_group_id ON bookings(group_id);
CREATE INDEX IF NOT EXISTS ix_bookings_start_time ON bookings(start_time);
CREATE INDEX IF NOT EXISTS ix_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS ix_bookings_recurrence_group_id ON bookings(recurrence_group_id);
CREATE INDEX IF NOT EXISTS ix_bookings_deleted_at ON bookings(deleted_at);
CREATE INDEX IF NOT EXISTS ix_bookings_sub_starttime ON bookings(subscription_id, start_time)
    WHERE deleted_at IS NULL AND status NOT IN ('cancelled', 'specialist_cancelled');

-- =========================================================
-- 5. BOOKING_SPECIALISTS (m2m)
-- =========================================================
CREATE TABLE IF NOT EXISTS booking_specialists (
    booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    specialist_id INTEGER NOT NULL REFERENCES global_users(id) ON DELETE CASCADE,
    PRIMARY KEY (booking_id, specialist_id)
);

CREATE INDEX IF NOT EXISTS ix_booking_specialists_specialist_id ON booking_specialists(specialist_id);

-- =========================================================
-- 6. МИГРАЦИЯ ДАННЫХ ИЗ schedules
-- =========================================================
-- Алгоритм:
--   1. Для каждой schedule находим/создаём клиента у того же специалиста
--      (по нормализованному имени).
--   2. На каждую schedule создаём отдельную subscription_1 (1/1, completed)
--      и booking, который ссылается на свою подписку.
--   3. Привязка по schedule.id → не зависит от уникальности created_at.
DO $$
DECLARE
    schedules_exists BOOLEAN;
    legacy_service_id INTEGER;
    rec RECORD;
    v_client_id INTEGER;
    v_subscription_id INTEGER;
    v_legacy_phone VARCHAR(50);
    v_clean_name VARCHAR(255);
BEGIN
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'schedules'
    ) INTO schedules_exists;

    IF NOT schedules_exists THEN
        RAISE NOTICE 'Table schedules does not exist, skipping legacy migration';
        RETURN;
    END IF;

    SELECT id INTO legacy_service_id FROM services WHERE service_type = 'subscription_1';

    FOR rec IN
        SELECT id, global_user_id, title, start_time, end_time,
               COALESCE(is_recurring, FALSE) AS is_recurring,
               recurrence_group_id, description,
               created_at, updated_at, deleted_at
        FROM schedules
        WHERE deleted_at IS NULL
        ORDER BY id
    LOOP
        v_clean_name := COALESCE(NULLIF(TRIM(rec.title), ''), 'Без имени');

        -- Ищем существующего клиента у этого специалиста
        SELECT id INTO v_client_id
        FROM clients
        WHERE global_user_id = rec.global_user_id
          AND LOWER(name) = LOWER(v_clean_name)
          AND deleted_at IS NULL
        LIMIT 1;

        -- Если нет — создаём фиктивного. phone уникальный за счёт schedule.id.
        IF v_client_id IS NULL THEN
            v_legacy_phone := 'legacy:' || rec.global_user_id || ':' || rec.id;
            INSERT INTO clients (global_user_id, name, phone, is_active, created_at, updated_at)
            VALUES (rec.global_user_id, v_clean_name, v_legacy_phone, TRUE, NOW(), NOW())
            RETURNING id INTO v_client_id;
        END IF;

        -- Создаём subscription_1 (полностью использованную) для historical-брони
        INSERT INTO client_subscriptions (
            client_id, service_id, assigned_specialist_id,
            total_sessions, used_sessions, status,
            purchased_at, notes, created_at, updated_at
        )
        VALUES (
            v_client_id, legacy_service_id, rec.global_user_id,
            1, 1, 'completed'::subscription_status_enum,
            rec.created_at,
            'Перенесено из schedules (legacy migration)',
            rec.created_at, NOW()
        )
        RETURNING id INTO v_subscription_id;

        -- Создаём booking
        INSERT INTO bookings (
            client_id, subscription_id, service_id, specialist_id,
            start_time, end_time, booking_type, status,
            notes, is_recurring, recurrence_group_id, session_number,
            created_at, updated_at, deleted_at
        )
        VALUES (
            v_client_id, v_subscription_id, legacy_service_id, rec.global_user_id,
            rec.start_time, rec.end_time,
            'individual'::booking_type_enum,
            'scheduled'::booking_status_enum,
            'Перенесено из schedules' || COALESCE(' | ' || rec.description, ''),
            rec.is_recurring, rec.recurrence_group_id, 1,
            rec.created_at, rec.updated_at, rec.deleted_at
        );
    END LOOP;

    RAISE NOTICE 'Legacy migration done.';

    DROP TABLE schedules;
    RAISE NOTICE 'Table schedules dropped.';
END $$;
