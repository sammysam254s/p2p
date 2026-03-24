-- P2P Secure-Lend Kenya Database Schema for Supabase
-- Run this in your Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom user table (extending Supabase auth.users)
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

-- Create Row Level Security (RLS) policies
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.collateral ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.loans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.investments ENABLE ROW LEVEL SECURITY;

-- Users can read their own data
CREATE POLICY "Users can view own profile" ON public.users
    FOR SELECT USING (auth.uid()::text = id::text);

-- Users can update their own data
CREATE POLICY "Users can update own profile" ON public.users
    FOR UPDATE USING (auth.uid()::text = id::text);

-- Collateral policies
CREATE POLICY "Users can view own collateral" ON public.collateral
    FOR SELECT USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can insert own collateral" ON public.collateral
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own collateral" ON public.collateral
    FOR UPDATE USING (auth.uid()::text = user_id::text);

-- Agents can view all pending collateral
CREATE POLICY "Agents can view pending collateral" ON public.collateral
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id::text = auth.uid()::text 
            AND role = 'agent'
        )
    );

-- Agents can update collateral status
CREATE POLICY "Agents can update collateral status" ON public.collateral
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id::text = auth.uid()::text 
            AND role = 'agent'
        )
    );

-- Loan policies
CREATE POLICY "Borrowers can view own loans" ON public.loans
    FOR SELECT USING (auth.uid()::text = borrower_id::text);

CREATE POLICY "Borrowers can insert own loans" ON public.loans
    FOR INSERT WITH CHECK (auth.uid()::text = borrower_id::text);

-- Lenders can view listed loans
CREATE POLICY "Lenders can view listed loans" ON public.loans
    FOR SELECT USING (
        status = 'listed' OR 
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id::text = auth.uid()::text 
            AND role = 'lender'
        )
    );

-- Investment policies
CREATE POLICY "Lenders can view own investments" ON public.investments
    FOR SELECT USING (auth.uid()::text = lender_id::text);

CREATE POLICY "Lenders can insert own investments" ON public.investments
    FOR INSERT WITH CHECK (auth.uid()::text = lender_id::text);

-- Borrowers can view investments in their loans
CREATE POLICY "Borrowers can view loan investments" ON public.investments
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.loans 
            WHERE id = loan_id 
            AND borrower_id::text = auth.uid()::text
        )
    );

-- Create functions for business logic
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

-- Create view for loan details with calculations
CREATE OR REPLACE VIEW loan_details AS
SELECT 
    l.*,
    u.username as borrower_username,
    u.phone_number as borrower_phone,
    c.item_type,
    c.brand_model,
    c.market_value,
    c.status as collateral_status,
    c.verification_date,
    calculate_max_loan_amount(c.market_value) as max_loan_amount,
    calculate_platform_fee(l.principal_amount) as platform_fee,
    calculate_insurance_fee(l.principal_amount) as insurance_fee,
    calculate_monthly_interest(l.principal_amount, l.interest_rate) as monthly_interest,
    calculate_total_repayment(l.principal_amount, l.duration_months, l.interest_rate) as total_repayment,
    CASE 
        WHEN l.principal_amount > 0 THEN (l.funded_amount / l.principal_amount) * 100 
        ELSE 0 
    END as funding_percentage,
    CASE 
        WHEN l.status = 'listed' THEN GREATEST(0, 7 - EXTRACT(DAY FROM NOW() - l.created_at))
        ELSE 0 
    END as days_remaining
FROM public.loans l
JOIN public.users u ON l.borrower_id = u.id
JOIN public.collateral c ON l.collateral_id = c.id;

-- Insert sample data (optional - for testing)
-- You can uncomment these if you want sample data

/*
-- Sample users
INSERT INTO public.users (username, email, role, phone_number, national_id) VALUES
('john_borrower', 'john@example.com', 'borrower', '254712345678', '12345678'),
('jane_lender', 'jane@example.com', 'lender', '254787654321', '87654321'),
('agent_smith', 'agent@example.com', 'agent', '254700000000', '00000000');

-- Sample collateral
INSERT INTO public.collateral (user_id, item_type, brand_model, market_value, status) VALUES
((SELECT id FROM public.users WHERE username = 'john_borrower'), 'Smartphone', 'iPhone 14 Pro', 120000.00, 'verified');

-- Sample loan
INSERT INTO public.loans (borrower_id, collateral_id, principal_amount, duration_months, status) VALUES
((SELECT id FROM public.users WHERE username = 'john_borrower'), 
 (SELECT id FROM public.collateral WHERE brand_model = 'iPhone 14 Pro'), 
 40000.00, 3, 'listed');
*/