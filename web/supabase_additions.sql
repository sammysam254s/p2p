-- P2P Secure-Lend: Additional Supabase SQL
-- Run these in the Supabase SQL Editor if not already present.

-- 1. system_settings table (for commission/fee configuration)
CREATE TABLE IF NOT EXISTS system_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed default values
INSERT INTO system_settings (key, value) VALUES
  ('platform_fee_percent', '1'),
  ('insurance_fee_percent', '1'),
  ('agent_commission_percent', '5')
ON CONFLICT (key) DO NOTHING;

-- 2. Add is_active column to users (for ban/activate)
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- 3. Ensure kyc_verifications stores image URLs
ALTER TABLE kyc_verifications
  ADD COLUMN IF NOT EXISTS id_front_image TEXT,
  ADD COLUMN IF NOT EXISTS id_back_image TEXT,
  ADD COLUMN IF NOT EXISTS selfie_image TEXT,
  ADD COLUMN IF NOT EXISTS signature_image TEXT;

-- 4. Supabase Storage: Create a 'kyc-documents' bucket (do this in Storage UI or via API)
-- Bucket should be PRIVATE; admin accesses files via signed URLs.
-- In Supabase Dashboard: Storage > New Bucket > kyc-documents > Private

-- 5. Row Level Security for system_settings
ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Admin can manage settings" ON system_settings
  FOR ALL TO authenticated
  USING ((SELECT role FROM users WHERE id = auth.uid()) = 'admin');
