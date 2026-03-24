-- Just add the admin user to existing Supabase setup
-- Run this if you only need to add the admin user

-- Insert admin user if it doesn't exist
INSERT INTO public.users (username, email, role, phone_number, national_id, is_active, date_joined, created_at)
SELECT 'admin', 'sammyseth260@gmail.com', 'admin', '254700000001', 'ADMIN001', true, NOW(), NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM public.users WHERE email = 'sammyseth260@gmail.com'
);

-- Also add admin role to existing role constraint if needed
DO $$
BEGIN
    -- Try to update the constraint to include admin role
    BEGIN
        ALTER TABLE public.users DROP CONSTRAINT IF EXISTS users_role_check;
        ALTER TABLE public.users ADD CONSTRAINT users_role_check 
        CHECK (role IN ('borrower', 'lender', 'agent', 'admin'));
    EXCEPTION
        WHEN OTHERS THEN
            -- If constraint doesn't exist or other error, continue
            NULL;
    END;
END $$;