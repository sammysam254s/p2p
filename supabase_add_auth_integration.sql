-- Add Supabase Auth integration to users table
-- Run this in your Supabase SQL Editor

-- Add auth_user_id column to link with Supabase Auth users
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'auth_user_id') THEN
        ALTER TABLE public.users ADD COLUMN auth_user_id UUID;
        CREATE INDEX IF NOT EXISTS idx_users_auth_user_id ON public.users(auth_user_id);
    END IF;
END $$;

-- Create a function to sync Supabase Auth users with custom users table
CREATE OR REPLACE FUNCTION sync_auth_user()
RETURNS TRIGGER AS $$
BEGIN
    -- This function can be used to automatically sync auth users
    -- For now, it's just a placeholder for future enhancements
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Verify the update
SELECT 'Auth integration added successfully!' as status;
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'auth_user_id';