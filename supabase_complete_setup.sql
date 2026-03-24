-- Complete Supabase Setup for P2P Secure-Lend Kenya
-- Run this in your Supabase SQL Editor to set up everything

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing tables if they exist (be careful in production!)
DROP TABLE IF EXISTS public.payments CASCADE;
DROP TABLE IF EXISTS public.commissions CASCADE;
DROP TABLE IF EXISTS public.wallet_transactions CASCADE;
DROP TABLE IF EXISTS public.investments CASCADE;
DROP TABLE IF EXISTS public.loans CASCADE;
DROP TABLE IF EXISTS public.collateral CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;

-- Create users table
CREATE TABLE public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(254) UNIQUE NOT NULL,
    first_name VARCHAR(150) DEFAULT '',
    last_name VARCHAR(150) DEFAULT '',
    role VARCHAR(20) NOT NULL CHECK (role IN ('borrower', 'lender', 'agent', 'admin')),
    phone_number VARCHAR(15) NOT NULL,
    national_id VARCHAR(20) UNIQUE NOT NULL,
    wallet_balance DECIMAL(12,2) DEFAULT 0.00,
    total_earnings DECIMAL(12,2) DEFAULT 0.00,
    commission_rate DECIMAL(5,2) DEFAULT 0.50,
    is_promoted_admin BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    is_staff BOOLEAN DEFAULT false,
    is_superuser BOOLEAN DEFAULT false,
    date_joined TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create collateral table
CREATE TABLE public.collateral (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    item_type VARCHAR(100) NOT NULL,
    brand_model VARCHAR(200) NOT NULL,
    market_value DECIMAL(10,2) NOT NULL CHECK (market_value > 0),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'verified', 'released')),
    verified_by UUID REFERENCES public.users(id),
    verification_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create loans table
CREATE TABLE public.loans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    borrower_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    collateral_id UUID NOT NULL REFERENCES public.collateral(id) ON DELETE CASCADE,
    principal_amount DECIMAL(10,2) NOT NULL CHECK (principal_amount > 0),
    interest_rate DECIMAL(5,2) DEFAULT 13.00 CHECK (interest_rate > 0),
    duration_months INTEGER NOT NULL CHECK (duration_months > 0 AND duration_months <= 12),
    funded_amount DECIMAL(10,2) DEFAULT 0.00 CHECK (funded_amount >= 0),
    status VARCHAR(20) DEFAULT 'pending_collateral' CHECK (status IN ('pending_collateral', 'listed', 'active', 'paid', 'cancelled')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure collateral is used only once
    CONSTRAINT unique_collateral UNIQUE (collateral_id)
);

-- Create investments table
CREATE TABLE public.investments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lender_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    amount_invested DECIMAL(10,2) NOT NULL CHECK (amount_invested > 0),
    date TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent duplicate investments from same lender to same loan
    CONSTRAINT unique_lender_loan UNIQUE (lender_id, loan_id)
);

-- Create wallet transactions table
CREATE TABLE public.wallet_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('credit', 'debit')),
    amount DECIMAL(12,2) NOT NULL CHECK (amount > 0),
    description TEXT DEFAULT '',
    balance_after DECIMAL(12,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create commissions table
CREATE TABLE public.commissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL CHECK (amount >= 0),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'paid')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    paid_at TIMESTAMPTZ,
    
    -- Prevent duplicate commissions
    CONSTRAINT unique_agent_loan_commission UNIQUE (agent_id, loan_id)
);

-- Create payments table
CREATE TABLE public.payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    borrower_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL CHECK (amount > 0),
    payment_type VARCHAR(20) NOT NULL CHECK (payment_type IN ('monthly', 'full', 'partial')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
    mpesa_transaction_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Create indexes for better performance
CREATE INDEX idx_users_username ON public.users(username);
CREATE INDEX idx_users_email ON public.users(email);
CREATE INDEX idx_users_role ON public.users(role);
CREATE INDEX idx_users_national_id ON public.users(national_id);

CREATE INDEX idx_collateral_user_id ON public.collateral(user_id);
CREATE INDEX idx_collateral_status ON public.collateral(status);
CREATE INDEX idx_collateral_created_at ON public.collateral(created_at);

CREATE INDEX idx_loans_borrower_id ON public.loans(borrower_id);
CREATE INDEX idx_loans_collateral_id ON public.loans(collateral_id);
CREATE INDEX idx_loans_status ON public.loans(status);
CREATE INDEX idx_loans_created_at ON public.loans(created_at);

CREATE INDEX idx_investments_lender_id ON public.investments(lender_id);
CREATE INDEX idx_investments_loan_id ON public.investments(loan_id);
CREATE INDEX idx_investments_date ON public.investments(date);

CREATE INDEX idx_wallet_transactions_user_id ON public.wallet_transactions(user_id);
CREATE INDEX idx_wallet_transactions_created_at ON public.wallet_transactions(created_at);

CREATE INDEX idx_commissions_agent_id ON public.commissions(agent_id);
CREATE INDEX idx_commissions_loan_id ON public.commissions(loan_id);
CREATE INDEX idx_commissions_status ON public.commissions(status);

CREATE INDEX idx_payments_loan_id ON public.payments(loan_id);
CREATE INDEX idx_payments_borrower_id ON public.payments(borrower_id);
CREATE INDEX idx_payments_status ON public.payments(status);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_collateral_updated_at BEFORE UPDATE ON public.collateral
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_loans_updated_at BEFORE UPDATE ON public.loans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.collateral ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.loans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.investments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wallet_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.commissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for users
CREATE POLICY "Users can view own profile" ON public.users
    FOR SELECT USING (true); -- Allow all for now, can be restricted later

CREATE POLICY "Users can update own profile" ON public.users
    FOR UPDATE USING (true); -- Allow all for now

CREATE POLICY "Users can insert" ON public.users
    FOR INSERT WITH CHECK (true); -- Allow all for now

-- Create RLS policies for other tables (simplified for now)
CREATE POLICY "Allow all operations" ON public.collateral FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON public.loans FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON public.investments FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON public.wallet_transactions FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON public.commissions FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON public.payments FOR ALL USING (true);

-- Create business logic functions
CREATE OR REPLACE FUNCTION calculate_max_loan_amount(market_val DECIMAL)
RETURNS DECIMAL AS $$
BEGIN
    -- 30/50 rule: 30% devaluation, then 50% of devalued amount
    RETURN (market_val * 0.70) * 0.50;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION calculate_platform_fee(principal DECIMAL)
RETURNS DECIMAL AS $$
BEGIN
    -- 1% of principal amount
    RETURN principal * 0.01;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION calculate_insurance_fee(principal DECIMAL)
RETURNS DECIMAL AS $$
BEGIN
    -- 1% of principal amount
    RETURN principal * 0.01;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION calculate_monthly_interest(principal DECIMAL, rate DECIMAL DEFAULT 13.00)
RETURNS DECIMAL AS $$
BEGIN
    -- Flat interest per month
    RETURN principal * (rate / 100);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION calculate_total_repayment(principal DECIMAL, duration INTEGER, rate DECIMAL DEFAULT 13.00)
RETURNS DECIMAL AS $$
DECLARE
    monthly_interest DECIMAL;
    total_interest DECIMAL;
    platform_fee DECIMAL;
    insurance_fee DECIMAL;
BEGIN
    monthly_interest := calculate_monthly_interest(principal, rate);
    total_interest := monthly_interest * duration;
    platform_fee := calculate_platform_fee(principal);
    insurance_fee := calculate_insurance_fee(principal);
    
    RETURN principal + total_interest + platform_fee + insurance_fee;
END;
$$ LANGUAGE plpgsql;

-- Create admin user (commented out to allow registration)
-- Uncomment and run separately if needed
/*
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
) ON CONFLICT (username) DO UPDATE SET
    email = 'sammyseth260@gmail.com',
    role = 'admin',
    is_staff = true,
    is_superuser = true,
    is_promoted_admin = true,
    updated_at = NOW();
*/

-- Verify setup
SELECT 'Setup completed successfully!' as status;
SELECT 'Admin user:' as info, username, email, role, is_staff, is_superuser 
FROM public.users WHERE role = 'admin';