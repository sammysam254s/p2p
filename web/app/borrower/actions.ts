'use server'

import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'

export async function applyForLoan(formData: FormData) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return redirect('/login')

  const item_type = formData.get('item_type') as string
  const brand_model = formData.get('brand_model') as string
  const market_value = parseFloat(formData.get('market_value') as string)
  
  const principal_amount = parseFloat(formData.get('principal_amount') as string)
  const duration_months = parseInt(formData.get('duration_months') as string, 10)

  // Basic validation for 30/50 rule:
  // Loan cannot exceed 50% of the devalued collateral (which is 70% of market value)
  const devalued_amount = market_value * 0.70
  const max_loan_amount = devalued_amount * 0.50

  if (principal_amount > max_loan_amount) {
    return redirect(`/borrower/loan-apply?error=Requested amount exceeds maximum allowed based on collateral value. Max: KES ${max_loan_amount.toFixed(2)}`)
  }

  // 1. Create Collateral
  const { data: collateral, error: colError } = await supabase.from('collateral').insert({
    user_id: user.id,
    item_type,
    brand_model,
    market_value,
    status: 'pending'
  }).select().single()

  if (colError || !collateral) {
    console.error("Collateral insertion error:", colError)
    return redirect('/borrower/loan-apply?error=Failed to process collateral details')
  }

  // 2. Create Loan
  const { error: loanError } = await supabase.from('loans').insert({
    borrower_id: user.id,
    collateral_id: collateral.id,
    principal_amount,
    interest_rate: 13, // Fixed 13% based on requirements
    duration_months,
    funded_amount: 0,
    status: 'pending_collateral'
  })

  if (loanError) {
    console.error("Loan insertion error:", loanError)
    return redirect('/borrower/loan-apply?error=Failed to create loan application')
  }

  return redirect('/borrower?message=Loan application submitted successfully. Pending collateral verification.')
}
