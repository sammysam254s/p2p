-- Essential tables for P2P Secure-Lend Kenya
-- Run this in Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table with all new fields
CREATE TABLE public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(254) NOT NULL,
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
    date_joined TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Wallet transactions table
CREATE TABLE public.wallet_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    transaction_type VARCHAR(10) NOT NULL CHECK (transaction_type IN ('credit', 'debit')),
    amount DECIMAL(12,2) NOT NULL,
    description TEXT DEFAULT '',
    balance_after DECIMAL(12,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Collateral table with verified_by field
CREATE TABLE public.collateral (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    item_type VARCHAR(100) NOT NULL,
    brand_model VARCHAR(200) NOT NULL,
    market_value DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'verified', 'released')),
    verification_date TIMESTAMPTZ,
    verified_by_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Loans table with payment tracking
CREATE TABLE public.loans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    borrower_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    collateral_id UUID NOT NULL REFERENCES public.collateral(id) ON DELETE CASCADE,
    principal_amount DECIMAL(10,2) NOT NULL,
    interest_rate DECIMAL(5,2) DEFAULT 13.00,
    duration_months INTEGER NOT NULL,
    funded_amount DECIMAL(10,2) DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'pending_collateral' CHECK (status IN ('pending_collateral', 'listed', 'active', 'paid', 'cancelled', 'defaulted')),
    activated_at TIMESTAMPTZ,
    next_payment_date TIMESTAMPTZ,
    payments_made INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_collateral UNIQUE (collateral_id)
);

-- Investments table with returns tracking
CREATE TABLE public.investments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lender_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    amount_invested DECIMAL(10,2) NOT NULL,
    monthly_return DECIMAL(10,2) DEFAULT 0.00,
    total_returns_paid DECIMAL(10,2) DEFAULT 0.00,
    date TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_lender_loan UNIQUE (lender_id, loan_id)
);

-- Commissions table
CREATE TABLE public.commissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    commission_rate DECIMAL(5,2) NOT NULL,
    is_paid BOOLEAN DEFAULT false,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Payments table
CREATE TABLE public.payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    payment_type VARCHAR(20) NOT NULL CHECK (payment_type IN ('monthly', 'full', 'partial')),
    payment_date TIMESTAMPTZ DEFAULT NOW(),
    next_payment_date TIMESTAMPTZ,
    processed_by_id UUID REFERENCES public.users(id) ON DELETE SET NULL
);

-- Basic indexes
CREATE INDEX idx_users_username ON public.users(username);
CREATE INDEX idx_users_role ON public.users(role);
CREATE INDEX idx_users_email ON public.users(email);
CREATE INDEX idx_collateral_status ON public.collateral(status);
CREATE INDEX idx_loans_status ON public.loans(status);
CREATE INDEX idx_loans_borrower_id ON public.loans(borrower_id);
CREATE INDEX idx_wallet_transactions_user_id ON public.wallet_transactions(user_id);
CREATE INDEX idx_commissions_agent_id ON public.commissions(agent_id);
CREATE INDEX idx_commissions_is_paid ON public.commissions(is_paid);

-- Insert admin user
INSERT INTO public.users (username, email, role, phone_number, national_id, is_staff, wallet_balance, total_earnings) VALUES
('admin', 'sammyseth260@gmail.com', 'admin', '254700000001', 'ADMIN001', true, 0.00, 0.00);

-- Sample data for testing
INSERT INTO public.users (username, email, role, phone_number, national_id, wallet_balance, total_earnings) VALUES
('demo_borrower', 'borrower@demo.com', 'borrower', '254712345678', '12345678', 0.00, 0.00),
('demo_lender', 'lender@demo.com', 'lender', '254787654321', '87654321', 1000.00, 0.00),
('demo_agent', 'agent@demo.com', 'agent', '254700000000', '00000000', 0.00, 0.00);

-- Sample collateral
INSERT INTO public.collateral (user_id, item_type, brand_model, market_value, status) VALUES
((SELECT id FROM public.users WHERE username = 'demo_borrower'), 'Smartphone', 'iPhone 14 Pro', 120000.00, 'pending');

-- Sample loan
INSERT INTO public.loans (borrower_id, collateral_id, principal_amount, duration_months, status) VALUES
((SELECT id FROM public.users WHERE username = 'demo_borrower'), 
 (SELECT id FROM public.collateral WHERE brand_model = 'iPhone 14 Pro'), 
 40000.00, 3, 'pending_collateral');

-- Functions for business logic
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
    -- 2% of principal amount (updated from 1%)
    RETURN principal * 0.02;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION calculate_monthly_interest(principal DECIMAL, rate DECIMAL DEFAULT 13.00)
RETURNS DECIMAL AS $$
BEGIN
    -- Flat interest per month
    RETURN principal * (rate / 100);
END;
$$ LANGUAGE plpgsql;