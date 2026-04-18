-- Migration: Add name column to global_users table
-- Date: 2026-04-08
-- Description: Add name field to GlobalUser model

-- Add name column to global_users table
ALTER TABLE global_users ADD COLUMN IF NOT EXISTS name VARCHAR(255);
