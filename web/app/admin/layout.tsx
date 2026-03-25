import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { ReactNode } from 'react'

export default async function AdminLayout({ children }: { children: ReactNode }) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const { data: profile } = await supabase.from('users').select('role, username').eq('id', user.id).single()
  if (profile?.role !== 'admin') redirect('/')

  return (
    <div className="min-vh-100 d-flex flex-column bg-light">
      {/* Top navbar */}
      <nav className="navbar navbar-expand-lg shadow-sm" style={{ background: 'linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%)' }}>
        <div className="container-fluid px-4">
          <a className="navbar-brand d-flex align-items-center gap-2" href="/admin">
            <span style={{ background: 'linear-gradient(135deg,#00d4ff,#7c3aed)', borderRadius: '8px', padding: '4px 10px', fontWeight: 700, fontSize: '1.1rem', color: '#fff' }}>P2P</span>
            <span className="text-white fw-semibold">Admin Console</span>
          </a>

          <div className="d-flex align-items-center gap-3">
            <div className="d-flex gap-1">
              <a href="/admin" className="btn btn-sm btn-outline-light opacity-75">
                <i className="fas fa-tachometer-alt me-1"></i>Dashboard
              </a>
              <a href="/admin/users" className="btn btn-sm btn-outline-light opacity-75">
                <i className="fas fa-users me-1"></i>Users
              </a>
              <a href="/admin/loans" className="btn btn-sm btn-outline-light opacity-75">
                <i className="fas fa-file-invoice-dollar me-1"></i>Loans
              </a>
              <a href="/admin/kyc" className="btn btn-sm btn-outline-light opacity-75">
                <i className="fas fa-id-card me-1"></i>KYC
              </a>
              <a href="/admin/commissions" className="btn btn-sm btn-outline-light opacity-75">
                <i className="fas fa-percent me-1"></i>Commissions
              </a>
            </div>

            <div className="dropdown">
              <button className="btn btn-sm btn-outline-light opacity-75 dropdown-toggle" data-bs-toggle="dropdown">
                <i className="fas fa-user-shield me-1"></i>{profile?.username}
              </button>
              <ul className="dropdown-menu dropdown-menu-end">
                <li><a className="dropdown-item" href="/">View Site</a></li>
                <li><hr className="dropdown-divider" /></li>
                <li>
                  <form action="/api/auth/signout" method="post">
                    <button className="dropdown-item text-danger" type="submit">
                      <i className="fas fa-sign-out-alt me-2"></i>Logout
                    </button>
                  </form>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </nav>

      <main className="flex-grow-1 p-4">
        {children}
      </main>

      <footer className="text-center py-3 border-top bg-white">
        <small className="text-muted">P2P Secure-Lend Admin &copy; {new Date().getFullYear()}</small>
      </footer>
    </div>
  )
}
