-- Add document-related tables to Supabase
-- Run this in your Supabase SQL Editor

-- Create KYC verifications table
CREATE TABLE IF NOT EXISTS public.kyc_verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    full_name VARCHAR(200) NOT NULL,
    id_number VARCHAR(50) NOT NULL,
    date_of_birth DATE NOT NULL,
    id_front_image TEXT, -- URL or base64 data
    id_back_image TEXT,  -- URL or base64 data
    selfie_image TEXT,   -- URL or base64 data
    signature_image TEXT, -- URL or base64 data
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'verified', 'rejected')),
    verification_notes TEXT DEFAULT '',
    verified_by UUID REFERENCES public.users(id),
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure one KYC per user
    CONSTRAINT unique_user_kyc UNIQUE (user_id)
);

-- Add contract_pdf column to loans table if it doesn't exist
ALTER TABLE public.loans 
ADD COLUMN IF NOT EXISTS contract_pdf TEXT DEFAULT ''; -- URL or file path

-- Add agent_verified_value to collateral table if it doesn't exist
ALTER TABLE public.collateral 
ADD COLUMN IF NOT EXISTS agent_verified_value DECIMAL(10,2) DEFAULT NULL;

-- Create indexes for KYC table
CREATE INDEX IF NOT EXISTS idx_kyc_user_id ON public.kyc_verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_kyc_status ON public.kyc_verifications(status);
CREATE INDEX IF NOT EXISTS idx_kyc_id_number ON public.kyc_verifications(id_number);
CREATE INDEX IF NOT EXISTS idx_kyc_created_at ON public.kyc_verifications(created_at);

-- Create updated_at trigger for KYC table
CREATE TRIGGER update_kyc_updated_at BEFORE UPDATE ON public.kyc_verifications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS for KYC table
ALTER TABLE public.kyc_verifications ENABLE ROW LEVEL SECURITY;

-- Create RLS policy for KYC table
CREATE POLICY "Allow all operations on KYC" ON public.kyc_verifications FOR ALL USING (true);

-- Verify the tables exist
SELECT 'KYC and document tables created successfully!' as status;

-- Show table structure
SELECT 
    table_name, 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name IN ('kyc_verifications', 'loans', 'collateral')
ORDER BY table_name, ordinal_position;