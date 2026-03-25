-- Update KYC Verifications table in Supabase (Safe for existing tables)
-- Run this in your Supabase SQL Editor

-- Add image columns to existing KYC table if they don't exist
DO $$ 
BEGIN
    -- Add image upload flags if they don't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'kyc_verifications' AND column_name = 'has_id_front_image') THEN
        ALTER TABLE public.kyc_verifications ADD COLUMN has_id_front_image BOOLEAN DEFAULT false;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'kyc_verifications' AND column_name = 'has_id_back_image') THEN
        ALTER TABLE public.kyc_verifications ADD COLUMN has_id_back_image BOOLEAN DEFAULT false;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'kyc_verifications' AND column_name = 'has_selfie_image') THEN
        ALTER TABLE public.kyc_verifications ADD COLUMN has_selfie_image BOOLEAN DEFAULT false;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'kyc_verifications' AND column_name = 'has_signature_image') THEN
        ALTER TABLE public.kyc_verifications ADD COLUMN has_signature_image BOOLEAN DEFAULT false;
    END IF;
    
    -- Add image URL columns if they don't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'kyc_verifications' AND column_name = 'id_front_image_url') THEN
        ALTER TABLE public.kyc_verifications ADD COLUMN id_front_image_url TEXT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'kyc_verifications' AND column_name = 'id_back_image_url') THEN
        ALTER TABLE public.kyc_verifications ADD COLUMN id_back_image_url TEXT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'kyc_verifications' AND column_name = 'selfie_image_url') THEN
        ALTER TABLE public.kyc_verifications ADD COLUMN selfie_image_url TEXT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'kyc_verifications' AND column_name = 'signature_image_url') THEN
        ALTER TABLE public.kyc_verifications ADD COLUMN signature_image_url TEXT;
    END IF;
END $$;

-- Create KYC table if it doesn't exist (for new installations)
CREATE TABLE IF NOT EXISTS public.kyc_verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    full_name VARCHAR(200) NOT NULL,
    id_number VARCHAR(50) NOT NULL,
    date_of_birth DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'under_review', 'verified', 'rejected')),
    verification_score INTEGER DEFAULT 0 CHECK (verification_score >= 0 AND verification_score <= 100),
    verified_at TIMESTAMPTZ,
    
    -- Image upload flags
    has_id_front_image BOOLEAN DEFAULT false,
    has_id_back_image BOOLEAN DEFAULT false,
    has_selfie_image BOOLEAN DEFAULT false,
    has_signature_image BOOLEAN DEFAULT false,
    
    -- Image URLs (for Supabase Storage)
    id_front_image_url TEXT,
    id_back_image_url TEXT,
    selfie_image_url TEXT,
    signature_image_url TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure one KYC record per user
    CONSTRAINT unique_user_kyc UNIQUE (user_id)
);

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_kyc_user_id ON public.kyc_verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_kyc_status ON public.kyc_verifications(status);
CREATE INDEX IF NOT EXISTS idx_kyc_created_at ON public.kyc_verifications(created_at);

-- Create updated_at trigger only if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_kyc_verifications_updated_at') THEN
        CREATE TRIGGER update_kyc_verifications_updated_at 
        BEFORE UPDATE ON public.kyc_verifications
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Enable RLS for KYC table
ALTER TABLE public.kyc_verifications ENABLE ROW LEVEL SECURITY;

-- Create RLS policy if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'kyc_verifications' AND policyname = 'Allow all KYC operations') THEN
        CREATE POLICY "Allow all KYC operations" ON public.kyc_verifications FOR ALL USING (true);
    END IF;
END $$;

-- Verify KYC table update
SELECT 'KYC table updated successfully with image fields!' as status;
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'kyc_verifications' 
ORDER BY ordinal_position;