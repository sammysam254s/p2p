-- Secure Admin Setup for P2P Secure-Lend Kenya
-- This script creates the admin user ONLY if it doesn't exist
-- Run this ONCE during initial setup

-- Create admin user only if it doesn't exist
DO $$
DECLARE
    admin_exists BOOLEAN := FALSE;
BEGIN
    -- Check if admin user already exists
    SELECT EXISTS(
        SELECT 1 FROM public.users 
        WHERE email = 'sammyseth260@gmail.com' OR username = 'sammyseth260'
    ) INTO admin_exists;
    
    -- Only create if admin doesn't exist
    IF NOT admin_exists THEN
        INSERT INTO public.users (
            username, 
            email, 
            first_name, 
            last_name, 
            role, 
            phone_number, 
            national_id, 
            is_active, 
            is_staff, 
            is_superuser,
            wallet_balance,
            total_earnings,
            commission_rate,
            is_promoted_admin
        ) VALUES (
            'sammyseth260',
            'sammyseth260@gmail.com',
            'Sammy',
            'Seth',
            'admin',
            '254700000001',
            'ADMIN001',
            true,
            true,
            true,
            0.00,
            0.00,
            0.00,
            true
        );
        
        RAISE NOTICE 'Admin user created successfully';
    ELSE
        RAISE NOTICE 'Admin user already exists - skipping creation';
    END IF;
END $$;

-- Create a function to prevent admin email/username modification
CREATE OR REPLACE FUNCTION prevent_admin_modification()
RETURNS TRIGGER AS $$
BEGIN
    -- Prevent modification of admin user's critical fields
    IF OLD.email = 'sammyseth260@gmail.com' OR OLD.username = 'sammyseth260' THEN
        -- Allow only specific field updates for admin
        NEW.email := OLD.email;
        NEW.username := OLD.username;
        NEW.role := 'admin';
        NEW.is_staff := true;
        NEW.is_superuser := true;
        NEW.is_promoted_admin := true;
        
        -- Log the attempt
        RAISE NOTICE 'Admin user modification attempted - critical fields protected';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to protect admin user
DROP TRIGGER IF EXISTS protect_admin_user ON public.users;
CREATE TRIGGER protect_admin_user
    BEFORE UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION prevent_admin_modification();

-- Create a function to prevent admin user deletion
CREATE OR REPLACE FUNCTION prevent_admin_deletion()
RETURNS TRIGGER AS $$
BEGIN
    -- Prevent deletion of admin user
    IF OLD.email = 'sammyseth260@gmail.com' OR OLD.username = 'sammyseth260' THEN
        RAISE EXCEPTION 'Admin user cannot be deleted';
    END IF;
    
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to prevent admin deletion
DROP TRIGGER IF EXISTS protect_admin_deletion ON public.users;
CREATE TRIGGER protect_admin_deletion
    BEFORE DELETE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION prevent_admin_deletion();

-- Verify admin user exists
SELECT 
    'Admin user verification:' as status,
    username, 
    email, 
    role, 
    is_staff, 
    is_superuser, 
    is_promoted_admin,
    created_at
FROM public.users 
WHERE email = 'sammyseth260@gmail.com' OR username = 'sammyseth260';

-- Show security measures in place
SELECT 'Security measures active:' as status;
SELECT 'Admin modification protection: ENABLED' as protection;
SELECT 'Admin deletion protection: ENABLED' as protection;