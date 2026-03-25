-- Fix multiple investments issue by removing unique constraint
-- Run this in your Supabase SQL Editor

-- Drop the unique constraint that prevents multiple investments from same lender to same loan
ALTER TABLE public.investments 
DROP CONSTRAINT IF EXISTS unique_lender_loan;

-- Verify the constraint is removed
SELECT 
    conname as constraint_name,
    contype as constraint_type
FROM pg_constraint 
WHERE conrelid = 'public.investments'::regclass
AND contype = 'u';

-- Show current investments table structure
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'investments'
ORDER BY ordinal_position;

SELECT 'Multiple investments constraint removed successfully!' as status;