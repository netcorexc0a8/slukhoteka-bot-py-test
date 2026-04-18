-- Add recurrence fields to schedules table
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS recurrence_group_id VARCHAR(100);
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS is_recurring BOOLEAN DEFAULT FALSE;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS ix_schedules_recurrence_group_id ON schedules(recurrence_group_id);

-- Create clients table
CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    global_user_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_clients_global_user FOREIGN KEY (global_user_id) REFERENCES global_users(id) ON DELETE CASCADE
);

-- Create indexes for clients table
CREATE INDEX IF NOT EXISTS ix_clients_global_user_id ON clients(global_user_id);
CREATE INDEX IF NOT EXISTS ix_clients_phone ON clients(phone);
CREATE INDEX IF NOT EXISTS ix_clients_deleted_at ON clients(deleted_at);

-- Add relationship to global_users
ALTER TABLE global_users ADD COLUMN IF NOT EXISTS clients_ids INTEGER[] DEFAULT ARRAY[]::INTEGER[];
