-- Add contract management tables to Supabase
-- Run this in your Supabase SQL Editor

-- Create loan contracts table for PDF contract management
CREATE TABLE IF NOT EXISTS public.loan_contracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    borrower_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    lender_ids JSONB NOT NULL DEFAULT '[]', -- Array of lender UUIDs
    pdf_url TEXT NOT NULL,
    principal_amount DECIMAL(12,2) NOT NULL,
    total_repayment DECIMAL(12,2) NOT NULL,
    due_date TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'defaulted', 'cancelled')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure one contract per loan
    CONSTRAINT unique_loan_contract UNIQUE (loan_id)
);

-- Create contract verification logs table
CREATE TABLE IF NOT EXISTS public.contract_verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id UUID NOT NULL REFERENCES public.loan_contracts(id) ON DELETE CASCADE,
    verified_by_ip VARCHAR(45),
    verified_at TIMESTAMPTZ DEFAULT NOW(),
    user_agent TEXT,
    verification_method VARCHAR(20) DEFAULT 'qr_code' CHECK (verification_method IN ('qr_code', 'direct_link', 'admin_panel'))
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_loan_contracts_loan_id ON public.loan_contracts(loan_id);
CREATE INDEX IF NOT EXISTS idx_loan_contracts_borrower_id ON public.loan_contracts(borrower_id);
CREATE INDEX IF NOT EXISTS idx_loan_contracts_due_date ON public.loan_contracts(due_date);
CREATE INDEX IF NOT EXISTS idx_loan_contracts_status ON public.loan_contracts(status);
CREATE INDEX IF NOT EXISTS idx_loan_contracts_created_at ON public.loan_contracts(created_at);

CREATE INDEX IF NOT EXISTS idx_contract_verifications_contract_id ON public.contract_verifications(contract_id);
CREATE INDEX IF NOT EXISTS idx_contract_verifications_verified_at ON public.contract_verifications(verified_at);

-- Create updated_at trigger for contracts table
CREATE TRIGGER update_loan_contracts_updated_at 
    BEFORE UPDATE ON public.loan_contracts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS for contract tables
ALTER TABLE public.loan_contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.contract_verifications ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for contract tables
CREATE POLICY "Allow all operations on contracts" ON public.loan_contracts FOR ALL USING (true);
CREATE POLICY "Allow all operations on verifications" ON public.contract_verifications FOR ALL USING (true);

-- Create function to get contract summary
CREATE OR REPLACE FUNCTION get_contract_summary()
RETURNS TABLE (
    total_contracts BIGINT,
    active_contracts BIGINT,
    overdue_contracts BIGINT,
    total_value DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_contracts,
        COUNT(*) FILTER (WHERE status = 'active') as active_contracts,
        COUNT(*) FILTER (WHERE status = 'active' AND due_date < NOW()) as overdue_contracts,
        COALESCE(SUM(principal_amount), 0) as total_value
    FROM public.loan_contracts;
END;
$$ LANGUAGE plpgsql;

-- Create function to check contract due dates
CREATE OR REPLACE FUNCTION check_overdue_contracts()
RETURNS TABLE (
    contract_id UUID,
    loan_id UUID,
    borrower_id UUID,
    days_overdue INTEGER,
    principal_amount DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        lc.id as contract_id,
        lc.loan_id,
        lc.borrower_id,
        EXTRACT(DAY FROM (NOW() - lc.due_date))::INTEGER as days_overdue,
        lc.principal_amount
    FROM public.loan_contracts lc
    WHERE lc.status = 'active' 
    AND lc.due_date < NOW()
    ORDER BY lc.due_date ASC;
END;
$$ LANGUAGE plpgsql;

-- Verify the tables exist
SELECT 'Contract tables created successfully!' as status;

-- Show table structure
SELECT 
    table_name, 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name IN ('loan_contracts', 'contract_verifications')
ORDER BY table_name, ordinal_position;