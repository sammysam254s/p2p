-- Update existing Supabase tables to add new fields
-- Run this in Supabase SQL Editor to update existing tables

-- Add new columns to users table
ALTER TABLE public.users 
ADD COLUMN IF NOT EXISTS wallet_balance DECIMAL(12,2) DEFAULT 0.00,
ADD COLUMN IF NOT EXISTS total_earnings DECIMAL(12,2) DEFAULT 0.00,
ADD COLUMN IF NOT EXISTS commission_rate DECIMAL(5,2) DEFAULT 0.50,
ADD COLUMN IF NOT EXISTS is_promoted_admin BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS is_staff BOOLEAN DEFAULT false;

-- Update role constraint to include admin
ALTER TABLE public.users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE public.users ADD CONSTRAINT users_role_check 
CHECK (role IN ('borrower', 'lender', 'agent', 'admin'));

-- Add verified_by field to collateral table
ALTER TABLE public.collateral 
ADD COLUMN IF NOT EXISTS verified_by_id UUID REFERENCES public.users(id) ON DELETE SET NULL;

-- Add new fields to loans table
ALTER TABLE public.loans 
ADD COLUMN IF NOT EXISTS activated_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS next_payment_date TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS payments_made INTEGER DEFAULT 0;

-- Update loans status constraint to include new statuses
ALTER TABLE public.loans DROP CONSTRAINT IF EXISTS loans_status_check;
ALTER TABLE public.loans ADD CONSTRAINT loans_status_check 
CHECK (status IN ('pending_collateral', 'listed', 'active', 'paid', 'cancelled', 'defaulted'));

-- Add new fields to investments table
ALTER TABLE public.investments 
ADD COLUMN IF NOT EXISTS monthly_return DECIMAL(10,2) DEFAULT 0.00,
ADD COLUMN IF NOT EXISTS total_returns_paid DECIMAL(10,2) DEFAULT 0.00;

-- Create wallet_transactions table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.wallet_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    transaction_type VARCHAR(10) NOT NULL CHECK (transaction_type IN ('credit', 'debit')),
    amount DECIMAL(12,2) NOT NULL,
    description TEXT DEFAULT '',
    balance_after DECIMAL(12,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create commissions table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.commissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    commission_rate DECIMAL(5,2) NOT NULL,
    is_paid BOOLEAN DEFAULT false,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create payments table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    payment_type VARCHAR(20) NOT NULL CHECK (payment_type IN ('monthly', 'full', 'partial')),
    payment_date TIMESTAMPTZ DEFAULT NOW(),
    next_payment_date TIMESTAMPTZ,
    processed_by_id UUID REFERENCES public.users(id) ON DELETE SET NULL
);

-- Add new indexes
CREATE INDEX IF NOT EXISTS idx_wallet_transactions_user_id ON public.wallet_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_commissions_agent_id ON public.commissions(agent_id);
CREATE INDEX IF NOT EXISTS idx_commissions_is_paid ON public.commissions(is_paid);
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);

-- Insert admin user if it doesn't exist
INSERT INTO public.users (username, email, role, phone_number, national_id, is_staff, wallet_balance, total_earnings)
SELECT 'admin', 'sammyseth260@gmail.com', 'admin', '254700000001', 'ADMIN001', true, 0.00, 0.00
WHERE NOT EXISTS (
    SELECT 1 FROM public.users WHERE email = 'sammyseth260@gmail.com'
);

-- Update existing demo users with wallet balances
UPDATE public.users 
SET wallet_balance = 1000.00, total_earnings = 0.00 
WHERE username = 'demo_lender' AND wallet_balance = 0;

UPDATE public.users 
SET wallet_balance = 0.00, total_earnings = 0.00 
WHERE username IN ('demo_borrower', 'demo_agent') AND wallet_balance IS NULL;

-- Update platform fee function to 2%
CREATE OR REPLACE FUNCTION calculate_platform_fee(principal DECIMAL)
RETURNS DECIMAL AS $$
BEGIN
    -- 2% of principal amount (updated from 1%)
    RETURN principal * 0.02;
END;
$$ LANGUAGE plpgsql;

-- Create other business logic functions
CREATE OR REPLACE FUNCTION calculate_max_loan_amount(market_val DECIMAL)
RETURNS DECIMAL AS $$
BEGIN
    -- 30/50 rule: 30% devaluation, then 50% of devalued amount
    RETURN (market_val * 0.70) * 0.50;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION calculate_monthly_interest(principal DECIMAL, rate DECIMAL DEFAULT 13.00)
RETURNS DECIMAL AS $$
BEGIN
    -- Flat interest per month
    RETURN principal * (rate / 100);
END;
$$ LANGUAGE plpgsql;