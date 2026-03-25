'use server'

import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'

export async function submitKyc(formData: FormData) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return redirect('/login')

  const full_name = formData.get('full_name') as string
  const id_number = formData.get('id_number') as string
  const date_of_birth = formData.get('date_of_birth') as string

  if (!full_name || !id_number || !date_of_birth) {
    return redirect('/kyc?error=Please fill in all required fields')
  }

  if (id_number.length < 6) {
    return redirect('/kyc?error=ID number must be at least 6 characters')
  }

  // Check for existing verified kyc
  const { data: existing } = await supabase
    .from('kyc_verifications')
    .select('status')
    .eq('user_id', user.id)
    .single()

  if (existing && existing.status === 'verified') {
    return redirect('/kyc?error=Your identity is already verified')
  }

  // Upload images to Supabase Storage (bucket: 'kyc-documents')
  const imageFields = ['id_front_image', 'id_back_image', 'selfie_image', 'signature_image']
  const uploadedUrls: Record<string, string> = {}

  for (const field of imageFields) {
    const file = formData.get(field) as File | null
    if (file && file.size > 0) {
      if (file.size > 5 * 1024 * 1024) {
        return redirect(`/kyc?error=File ${field} exceeds 5MB limit`)
      }
      const ext = file.name.split('.').pop() || 'jpg'
      const path = `${user.id}/${field}.${ext}`
      const { error: uploadError } = await supabase.storage
        .from('kyc-documents')
        .upload(path, file, { upsert: true, contentType: file.type })

      if (!uploadError) {
        const { data: urlData } = supabase.storage.from('kyc-documents').getPublicUrl(path)
        uploadedUrls[field] = urlData.publicUrl
      }
    }
  }

  // Upsert KYC record to 'under_review'
  const { error } = await supabase
    .from('kyc_verifications')
    .upsert({
      user_id: user.id,
      full_name,
      id_number,
      date_of_birth,
      status: 'under_review',
      id_front_image: uploadedUrls['id_front_image'] || null,
      id_back_image: uploadedUrls['id_back_image'] || null,
      selfie_image: uploadedUrls['selfie_image'] || null,
      signature_image: uploadedUrls['signature_image'] || null,
    }, { onConflict: 'user_id' })

  if (error) {
    console.error('KYC submission error:', error)
    return redirect('/kyc?error=Failed to submit KYC. Please try again.')
  }

  // Auto-verify for demo (in production, an AI/admin reviews the images)
  await supabase.from('kyc_verifications').update({
    status: 'verified',
    verified_at: new Date().toISOString()
  }).eq('user_id', user.id)

  await supabase.from('users').update({ kyc_verified: true }).eq('id', user.id)

  return redirect('/borrower?message=KYC verification completed successfully!')
}
