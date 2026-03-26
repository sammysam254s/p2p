'use server'

import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'

export async function logout() {
  try {
    const supabase = createClient()
    await supabase.auth.signOut()
  } catch (e) {
    console.error('Logout error:', e)
  }
  return redirect('/login')
}
