'use server'

import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'

export async function verifyCollateral(formData: FormData) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return redirect('/login')

  // Check if agent
  const { data: profile } = await supabase.from('users').select('role').eq('id', user.id).single()
  if (profile?.role !== 'agent' && profile?.role !== 'admin') {
    return redirect('/')
  }

  const collateral_id = formData.get('collateral_id') as string
  const verified_value = parseFloat(formData.get('verified_value') as string)
  const agent_notes = formData.get('agent_notes') as string

  if (!collateral_id || isNaN(verified_value)) {
    return redirect('/agent?error=Invalid verification data')
  }

  // 1. Update Collateral
  const { error: colError } = await supabase
    .from('collateral')
    .update({ 
      status: 'verified',
      market_value: verified_value,
      agent_notes: agent_notes
    })
    .eq('id', collateral_id)
    .select()
    .single()

  if (colError) {
    console.error("Collateral verification error:", colError)
    return redirect('/agent?error=Failed to update collateral')
  }

  // 2. Update linked loan to 'listed'
  const { error: loanError } = await supabase
    .from('loans')
    .update({ status: 'listed' })
    .eq('collateral_id', collateral_id)

  if (loanError) {
    console.error("Loan update error:", loanError)
    return redirect('/agent?error=Failed to list loan')
  }

  return redirect('/agent?message=Collateral verified and loan listed successfully')
}
