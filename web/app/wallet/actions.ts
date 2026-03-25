'use server'

import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'

export async function depositFunds(formData: FormData) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return redirect('/login')

  const amount = parseFloat(formData.get('amount') as string)
  if (isNaN(amount) || amount < 10) {
    return redirect('/wallet?error=Minimum deposit amount is KES 10')
  }
  if (amount > 100000) {
    return redirect('/wallet?error=Maximum deposit amount is KES 100,000')
  }

  const { data: profile } = await supabase
    .from('users')
    .select('wallet_balance')
    .eq('id', user.id)
    .single()

  const newBalance = (profile?.wallet_balance || 0) + amount

  await supabase.from('users').update({ wallet_balance: newBalance }).eq('id', user.id)

  // Record transaction
  await supabase.from('wallet_transactions').insert({
    user_id: user.id,
    transaction_type: 'credit',
    amount,
    description: `Simulated deposit via M-Pesa`,
    balance_after: newBalance
  })

  return redirect(`/wallet?message=KES ${amount.toFixed(2)} deposited successfully`)
}

export async function withdrawFunds(formData: FormData) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return redirect('/login')

  const amount = parseFloat(formData.get('amount') as string)
  
  const { data: profile } = await supabase
    .from('users')
    .select('wallet_balance')
    .eq('id', user.id)
    .single()

  const balance = profile?.wallet_balance || 0

  if (isNaN(amount) || amount < 100) {
    return redirect('/wallet?error=Minimum withdrawal amount is KES 100')
  }
  if (amount > balance) {
    return redirect('/wallet?error=Insufficient wallet balance')
  }

  const newBalance = balance - amount
  await supabase.from('users').update({ wallet_balance: newBalance }).eq('id', user.id)

  await supabase.from('wallet_transactions').insert({
    user_id: user.id,
    transaction_type: 'debit',
    amount,
    description: `Simulated withdrawal to M-Pesa`,
    balance_after: newBalance
  })

  return redirect(`/wallet?message=KES ${amount.toFixed(2)} withdrawn successfully`)
}
