-- Create Admin User for Secure-Lend Kenya
-- Run this in your Supabase SQL Editor after running the main schema

-- First, update the role constraint to include admin if not already done
ALTER TABLE public.users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE public.users ADD CONSTRAINT users_role_check 
    CHECK (role IN ('borrower', 'lender', 'agent', 'admin'));

-- Add admin-specific fields if they don't exist
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS wallet_balance DECIMAL(12,2) DEFAULT 0.00;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS total_earnings DECIMAL(12,2) DEFAULT 0.00;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS commission_rate DECIMAL(5,2) DEFAULT 0.50;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS is_promoted_admin BOOLEAN DEFAULT false;

-- Create or update the admin user
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
) ON CONFLICT (email) DO UPDATE SET
    role = 'admin',
    is_staff = true,
    is_superuser = true,
    is_promoted_admin = true,
    updated_at = NOW();

-- Also handle username conflict
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

-- Create RLS policies for admin access
-- Admin can view all users
CREATE POLICY "Admin can view all users" ON public.users
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id::text = auth.uid()::text 
            AND role = 'admin'
        )
    );

-- Admin can update all users
CREATE POLICY "Admin can update all users" ON public.users
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id::text = auth.uid()::text 
            AND role = 'admin'
        )
    );

-- Admin can view all collateral
CREATE POLICY "Admin can view all collateral" ON public.collateral
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id::text = auth.uid()::text 
            AND role = 'admin'
        )
    );

-- Admin can update all collateral
CREATE POLICY "Admin can update all collateral" ON public.collateral
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id::text = auth.uid()::text 
            AND role = 'admin'
        )
    );

-- Admin can view all loans
CREATE POLICY "Admin can view all loans" ON public.loans
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id::text = auth.uid()::text 
            AND role = 'admin'
        )
    );

-- Admin can update all loans
CREATE POLICY "Admin can update all loans" ON public.loans
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id::text = auth.uid()::text 
            AND role = 'admin'
        )
    );

-- Admin can view all investments
CREATE POLICY "Admin can view all investments" ON public.investments
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id::text = auth.uid()::text 
            AND role = 'admin'
        )
    );

-- Create wallet transactions table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.wallet_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('credit', 'debit')),
    amount DECIMAL(12,2) NOT NULL CHECK (amount > 0),
    description TEXT DEFAULT '',
    balance_after DECIMAL(12,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create commissions table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.commissions (
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

-- Create payments table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.payments (
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

-- Create indexes for new tables
CREATE INDEX IF NOT EXISTS idx_wallet_transactions_user_id ON public.wallet_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_wallet_transactions_created_at ON public.wallet_transactions(created_at);

CREATE INDEX IF NOT EXISTS idx_commissions_agent_id ON public.commissions(agent_id);
CREATE INDEX IF NOT EXISTS idx_commissions_loan_id ON public.commissions(loan_id);
CREATE INDEX IF NOT EXISTS idx_commissions_status ON public.commissions(status);

CREATE INDEX IF NOT EXISTS idx_payments_loan_id ON public.payments(loan_id);
CREATE INDEX IF NOT EXISTS idx_payments_borrower_id ON public.payments(borrower_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON public.payments(status);

-- Enable RLS on new tables
ALTER TABLE public.wallet_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.commissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;

-- RLS policies for wallet transactions
CREATE POLICY "Users can view own wallet transactions" ON public.wallet_transactions
    FOR SELECT USING (auth.uid()::text = user_id::text);

CREATE POLICY "Admin can view all wallet transactions" ON public.wallet_transactions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id::text = auth.uid()::text 
            AND role = 'admin'
        )
    );

-- RLS policies for commissions
CREATE POLICY "Agents can view own commissions" ON public.commissions
    FOR SELECT USING (auth.uid()::text = agent_id::text);

CREATE POLICY "Admin can view all commissions" ON public.commissions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id::text = auth.uid()::text 
            AND role = 'admin'
        )
    );

-- RLS policies for payments
CREATE POLICY "Borrowers can view own payments" ON public.payments
    FOR SELECT USING (auth.uid()::text = borrower_id::text);

CREATE POLICY "Admin can view all payments" ON public.payments
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id::text = auth.uid()::text 
            AND role = 'admin'
        )
    );

-- Verify the admin user was created
SELECT 
    username, 
    email, 
    role, 
    is_staff, 
    is_superuser, 
    is_promoted_admin,
    created_at
FROM public.users 
WHERE email = 'sammyseth260@gmail.com' OR username = 'sammyseth260';