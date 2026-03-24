-- Quick Admin Setup for sammyseth260@gmail.com
-- Run this in your Supabase SQL Editor

-- Update role constraint to include admin
ALTER TABLE public.users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE public.users ADD CONSTRAINT users_role_check 
    CHECK (role IN ('borrower', 'lender', 'agent', 'admin'));

-- Add missing columns if they don't exist
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS wallet_balance DECIMAL(12,2) DEFAULT 0.00;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS total_earnings DECIMAL(12,2) DEFAULT 0.00;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS commission_rate DECIMAL(5,2) DEFAULT 0.50;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS is_promoted_admin BOOLEAN DEFAULT false;

-- Create or update admin user
DO $$
BEGIN
    -- Try to update existing user by email
    UPDATE public.users SET
        role = 'admin',
        is_staff = true,
        is_superuser = true,
        is_promoted_admin = true,
        updated_at = NOW()
    WHERE email = 'sammyseth260@gmail.com';
    
    -- If no rows were updated, insert new user
    IF NOT FOUND THEN
        INSERT INTO public.users (
            username, email, first_name, last_name, role, 
            phone_number, national_id, is_active, is_staff, 
            is_superuser, wallet_balance, total_earnings, 
            commission_rate, is_promoted_admin
        ) VALUES (
            'sammyseth260', 'sammyseth260@gmail.com', 'Sammy', 'Seth', 'admin',
            '254700000001', 'ADMIN001', true, true, true,
            0.00, 0.00, 0.00, true
        );
    END IF;
END $$;

-- Verify admin user
SELECT username, email, role, is_staff, is_superuser, is_promoted_admin, created_at
FROM public.users 
WHERE email = 'sammyseth260@gmail.com';