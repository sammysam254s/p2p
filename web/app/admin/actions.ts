'use server'

import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'

async function requireAdmin() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')
  const { data: profile } = await supabase.from('users').select('role').eq('id', user.id).single()
  if (profile?.role !== 'admin') redirect('/')
  return supabase
}

export async function banUser(formData: FormData) {
  const supabase = await requireAdmin()
  const userId = formData.get('user_id') as string
  await supabase.from('users').update({ is_active: false }).eq('id', userId)
  redirect('/admin/users?message=User banned successfully')
}

export async function activateUser(formData: FormData) {
  const supabase = await requireAdmin()
  const userId = formData.get('user_id') as string
  await supabase.from('users').update({ is_active: true }).eq('id', userId)
  redirect('/admin/users?message=User activated successfully')
}

export async function changeUserRole(formData: FormData) {
  const supabase = await requireAdmin()
  const userId = formData.get('user_id') as string
  const role = formData.get('role') as string
  const validRoles = ['borrower', 'lender', 'agent', 'admin']
  if (!validRoles.includes(role)) redirect('/admin/users?error=Invalid role')
  await supabase.from('users').update({ role }).eq('id', userId)
  redirect('/admin/users?message=User role updated')
}

export async function approveLoan(formData: FormData) {
  const supabase = await requireAdmin()
  const loanId = formData.get('loan_id') as string
  await supabase.from('loans').update({ status: 'listed' }).eq('id', loanId)
  redirect('/admin/loans?message=Loan approved and listed on marketplace')
}

export async function rejectLoan(formData: FormData) {
  const supabase = await requireAdmin()
  const loanId = formData.get('loan_id') as string
  await supabase.from('loans').update({ status: 'rejected' }).eq('id', loanId)
  redirect('/admin/loans?message=Loan rejected')
}

export async function verifyKyc(formData: FormData) {
  const supabase = await requireAdmin()
  const kycUserId = formData.get('kyc_user_id') as string
  await supabase.from('kyc_verifications').update({
    status: 'verified',
    verified_at: new Date().toISOString()
  }).eq('user_id', kycUserId)
  await supabase.from('users').update({ kyc_verified: true }).eq('id', kycUserId)
  redirect('/admin/kyc?message=KYC verified successfully')
}

export async function rejectKyc(formData: FormData) {
  const supabase = await requireAdmin()
  const kycUserId = formData.get('kyc_user_id') as string
  await supabase.from('kyc_verifications').update({ status: 'rejected' }).eq('user_id', kycUserId)
  await supabase.from('users').update({ kyc_verified: false }).eq('id', kycUserId)
  redirect('/admin/kyc?message=KYC rejected')
}

export async function updateCommissions(formData: FormData) {
  const supabase = await requireAdmin()
  const platform_fee = parseFloat(formData.get('platform_fee') as string)
  const insurance_fee = parseFloat(formData.get('insurance_fee') as string)
  const agent_commission = parseFloat(formData.get('agent_commission') as string)

  if (isNaN(platform_fee) || isNaN(insurance_fee) || isNaN(agent_commission)) {
    redirect('/admin/commissions?error=Invalid values supplied')
  }

  await supabase.from('system_settings').upsert([
    { key: 'platform_fee_percent', value: platform_fee.toString() },
    { key: 'insurance_fee_percent', value: insurance_fee.toString() },
    { key: 'agent_commission_percent', value: agent_commission.toString() },
  ], { onConflict: 'key' })

  redirect('/admin/commissions?message=Commission settings updated successfully')
}
