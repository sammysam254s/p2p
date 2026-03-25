'use server'

import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'

export async function investInLoan(formData: FormData) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return redirect('/login')

  const loan_id = formData.get('loan_id') as string
  const investment_amount = parseFloat(formData.get('investment_amount') as string)

  if (!loan_id || isNaN(investment_amount) || investment_amount < 100) {
    return redirect(`/marketplace?error=Invalid investment amount. Minimum is KES 100`)
  }

  // Verify wallet balance
  const { data: profile } = await supabase
    .from('users')
    .select('wallet_balance')
    .eq('id', user.id)
    .single()

  if (!profile || profile.wallet_balance < investment_amount) {
    return redirect(`/marketplace?error=Insufficient wallet balance`)
  }

  // Perform investment logic (this ideally should be an RPC to ensure atomicity, 
  // but we'll do sequential operations for this port)
  
  // 1. Get loan details
  const { data: loan } = await supabase
    .from('loans')
    .select('principal_amount, funded_amount, status')
    .eq('id', loan_id)
    .single()

  if (!loan || loan.status !== 'listed') {
    return redirect(`/marketplace?error=Loan is no longer available`)
  }

  const remaining_needed = parseFloat(loan.principal_amount) - parseFloat(loan.funded_amount)
  if (investment_amount > remaining_needed) {
    return redirect(`/marketplace?error=Investment exceeds remaining needed amount`)
  }

  // 2. Create investment record
  const { error: investError } = await supabase.from('investments').insert({
    lender_id: user.id,
    loan_id,
    amount_invested: investment_amount
  })

  if (investError) {
    console.error("Investment error:", investError)
    return redirect(`/marketplace?error=Failed to process investment`)
  }

  // 3. Update wallet balance
  const new_balance = profile.wallet_balance - investment_amount
  await supabase.from('users').update({ wallet_balance: new_balance }).eq('id', user.id)

  // 4. Update loan funded amount
  const new_funded = parseFloat(loan.funded_amount) + investment_amount
  let new_status = 'listed'
  if (new_funded >= parseFloat(loan.principal_amount)) {
    new_status = 'active'
  }

  await supabase.from('loans').update({ 
    funded_amount: new_funded,
    status: new_status
  }).eq('id', loan_id)


  return redirect(`/marketplace?message=Investment successful!`)
}

export async function walletDeposit(formData: FormData) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return redirect('/login')

  const amount = parseFloat(formData.get('amount') as string)
  if (isNaN(amount) || amount < 10) {
    return redirect('?error=Invalid deposit amount')
  }

  const { data: profile } = await supabase
    .from('users')
    .select('wallet_balance')
    .eq('id', user.id)
    .single()

  const new_balance = (profile?.wallet_balance || 0) + amount

  const { error } = await supabase
    .from('users')
    .update({ wallet_balance: new_balance })
    .eq('id', user.id)

  if (error) {
    return redirect('?error=Failed to deposit funds')
  }

  return redirect('?message=Simulation: Funds deposited successfully!')
}
