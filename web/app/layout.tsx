import type { Metadata } from 'next'
import './globals.css'
import Script from 'next/script'
import { createClient } from '@/utils/supabase/server'
import { logout } from '@/app/auth/logout/actions'

export const metadata: Metadata = {
  title: 'P2P Secure-Lend Kenya',
  description: 'Bridging digital lending with physical security.',
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  // Try to fetch custom role from users table
  let role = ''
  let username = user?.email || ''
  
  if (user) {
    const { data } = await supabase
      .from('users')
      .select('role, username')
      .eq('id', user.id)
      .single()
      
    if (data) {
      role = data.role
      username = data.username
    }
  }

  return (
    <html lang="en">
      <head>
        <link rel="preload" href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" as="style" />
        <link rel="preload" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" as="style" />
        
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet" />
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet" />
      </head>
      <body>
        <nav className="navbar navbar-expand-lg navbar-dark bg-primary">
            <div className="container">
                <a className="navbar-brand" href="/">
                    <i className="fas fa-leaf me-2"></i>P2P Secure-Lend Kenya
                </a>
                
                {user ? (
                  <div className="navbar-nav ms-auto flex-row align-items-center">
                      <span className="navbar-text me-3 d-none d-md-inline">
                          <i className="fas fa-user me-1"></i>{username} ({role})
                      </span>
                      <form action={logout} className="m-0">
                        <button type="submit" className="btn btn-outline-light btn-sm">
                            <i className="fas fa-sign-out-alt me-1"></i>Logout
                        </button>
                      </form>
                  </div>
                ) : (
                  <div className="navbar-nav ms-auto flex-row align-items-center">
                      <a className="btn btn-outline-light btn-sm me-2" href="/login">
                          <i className="fas fa-sign-in-alt me-1"></i>Login
                      </a>
                      <a className="btn btn-light btn-sm" href="/register">
                          <i className="fas fa-user-plus me-1"></i>Register
                      </a>
                  </div>
                )}
            </div>
        </nav>
        <div className="container mt-4">
          {children}
        </div>
        <footer className="bg-dark text-light text-center py-3 mt-5">
            <div className="container">
                <p>&copy; 2026 P2P Secure-Lend Kenya. Bridging digital lending with physical security.</p>
            </div>
        </footer>
        <Script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js" strategy="lazyOnload" />
      </body>
    </html>
  )
}
