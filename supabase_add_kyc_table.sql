-- Add KYC Verifications table to Supabase
-- Run this in your Supabase SQL Editor

-- Create KYC verifications table
CREATE TABLE IF NOT EXISTS public.kyc_verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    full_name VARCHAR(200) NOT NULL,
    id_number VARCHAR(50) NOT NULL,
    date_of_birth DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'under_review', 'verified', 'rejected')),
    verification_score INTEGER DEFAULT 0 CHECK (verification_score >= 0 AND verification_score <= 100),
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure one KYC record per user
    CONSTRAINT unique_user_kyc UNIQUE (user_id)
);

-- Create indexes for KYC table
CREATE INDEX IF NOT EXISTS idx_kyc_user_id ON public.kyc_verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_kyc_status ON public.kyc_verifications(status);
CREATE INDEX IF NOT EXISTS idx_kyc_created_at ON public.kyc_verifications(created_at);

-- Create updated_at trigger for KYC table
CREATE TRIGGER update_kyc_verifications_updated_at BEFORE UPDATE ON public.kyc_verifications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS for KYC table
ALTER TABLE public.kyc_verifications ENABLE ROW LEVEL SECURITY;

-- Create RLS policy for KYC table
CREATE POLICY "Allow all KYC operations" ON public.kyc_verifications FOR ALL USING (true);

-- Verify KYC table creation
SELECT 'KYC table created successfully!' as status;
SELECT table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'kyc_verifications' 
ORDER BY ordinal_position;