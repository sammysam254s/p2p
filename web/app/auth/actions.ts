'use server'

import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'

export async function login(formData: FormData) {
  const email = formData.get('email') as string
  const password = formData.get('password') as string

  const supabase = createClient()

  // Find user by username or email. The original form used "username" but 
  // Supabase Auth primariliy uses email. We'll try email first. If the user input
  // doesn't have an @, we'll try to find the email by querying the `users` table by username.
  let loginEmail = email
  if (email && !email.includes('@')) {
    const { data } = await supabase
      .from('users')
      .select('email')
      .eq('username', email)
      .single()
    
    if (data?.email) {
      loginEmail = data.email
    }
  }

  const { error } = await supabase.auth.signInWithPassword({
    email: loginEmail,
    password,
  })

  if (error) {
    return redirect('/login?error=Could not authenticate user')
  }

  // Redirect based on role (we fetch role from our custom users table)
  const { data: userData } = await supabase
    .from('users')
    .select('role')
    .eq('email', loginEmail)
    .single()

  if (userData?.role === 'borrower') return redirect('/borrower')
  if (userData?.role === 'lender') return redirect('/marketplace')
  if (userData?.role === 'agent') return redirect('/agent')
  if (userData?.role === 'admin') return redirect('/admin-dashboard')
  
  return redirect('/')
}

export async function signup(formData: FormData) {
  const email = formData.get('email') as string
  const password = formData.get('password') as string
  const username = formData.get('username') as string
  const role = formData.get('role') as string
  const phone_number = formData.get('phone_number') as string
  const national_id = formData.get('national_id') as string

  const supabase = createClient()
  
  // Create auth user
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
        data: {
            username,
            role,
            phone_number,
            national_id
        }
    }
  })

  if (error) {
    return redirect('/register?error=' + error.message)
  }

  // Insert into custom users table (if not handled by Supabase trigger)
  if (data.user) {
    const { error: insertError } = await supabase.from('users').insert({
      id: data.user.id,
      username,
      email,
      role,
      phone_number,
      national_id,
      wallet_balance: 0
    })

    if (insertError && insertError.code !== '23505') { // Ignore unique violation if trigger handled it
        console.error("Error inserting into custom users table:", insertError)
    }
  }

  return redirect('/login?message=Check email to continue sign in process')
}
