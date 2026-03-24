-- Essential tables for P2P Secure-Lend Kenya
-- Run this in Supabase SQL Editor if you want just the basic tables

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(254) NOT NULL,
    first_name VARCHAR(150) DEFAULT '',
    last_name VARCHAR(150) DEFAULT '',
    role VARCHAR(20) NOT NULL CHECK (role IN ('borrower', 'lender', 'agent')),
    phone_number VARCHAR(15) NOT NULL,
    national_id VARCHAR(20) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    date_joined TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Collateral table
CREATE TABLE public.collateral (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    item_type VARCHAR(100) NOT NULL,
    brand_model VARCHAR(200) NOT NULL,
    market_value DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'verified', 'released')),
    verification_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Loans table
CREATE TABLE public.loans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    borrower_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    collateral_id UUID NOT NULL REFERENCES public.collateral(id) ON DELETE CASCADE,
    principal_amount DECIMAL(10,2) NOT NULL,
    interest_rate DECIMAL(5,2) DEFAULT 13.00,
    duration_months INTEGER NOT NULL,
    funded_amount DECIMAL(10,2) DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'pending_collateral' CHECK (status IN ('pending_collateral', 'listed', 'active', 'paid', 'cancelled')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_collateral UNIQUE (collateral_id)
);

-- Investments table
CREATE TABLE public.investments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lender_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    amount_invested DECIMAL(10,2) NOT NULL,
    date TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_lender_loan UNIQUE (lender_id, loan_id)
);

-- Basic indexes
CREATE INDEX idx_users_username ON public.users(username);
CREATE INDEX idx_users_role ON public.users(role);
CREATE INDEX idx_collateral_status ON public.collateral(status);
CREATE INDEX idx_loans_status ON public.loans(status);
CREATE INDEX idx_loans_borrower_id ON public.loans(borrower_id);

-- Sample data for testing
INSERT INTO public.users (username, email, role, phone_number, national_id) VALUES
('demo_borrower', 'borrower@demo.com', 'borrower', '254712345678', '12345678'),
('demo_lender', 'lender@demo.com', 'lender', '254787654321', '87654321'),
('demo_agent', 'agent@demo.com', 'agent', '254700000000', '00000000');

-- Sample collateral
INSERT INTO public.collateral (user_id, item_type, brand_model, market_value, status) VALUES
((SELECT id FROM public.users WHERE username = 'demo_borrower'), 'Smartphone', 'iPhone 14 Pro', 120000.00, 'pending');

-- Sample loan
INSERT INTO public.loans (borrower_id, collateral_id, principal_amount, duration_months, status) VALUES
((SELECT id FROM public.users WHERE username = 'demo_borrower'), 
 (SELECT id FROM public.collateral WHERE brand_model = 'iPhone 14 Pro'), 
 40000.00, 3, 'pending_collateral');