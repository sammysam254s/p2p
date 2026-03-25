import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'

export default async function AdminDashboard() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  // Stats
  const [
    { count: totalUsers },
    { count: totalLoans },
    { count: activeLoans },
    { count: pendingKyc },
    { count: pendingLoans },
    { data: recentLoans },
    { data: recentUsers },
  ] = await Promise.all([
    supabase.from('users').select('*', { count: 'exact', head: true }),
    supabase.from('loans').select('*', { count: 'exact', head: true }),
    supabase.from('loans').select('*', { count: 'exact', head: true }).eq('status', 'active'),
    supabase.from('kyc_verifications').select('*', { count: 'exact', head: true }).eq('status', 'under_review'),
    supabase.from('loans').select('*', { count: 'exact', head: true }).eq('status', 'pending_approval'),
    supabase.from('loans').select('id, principal_amount, status, created_at, borrower:users!loans_borrower_id_fkey(username)').order('created_at', { ascending: false }).limit(5),
    supabase.from('users').select('id, username, email, role, created_at').order('created_at', { ascending: false }).limit(5),
  ])

  const stats = [
    { label: 'Total Users', value: totalUsers ?? 0, icon: 'fas fa-users', color: '#7c3aed', bg: '#f3f0ff' },
    { label: 'Total Loans', value: totalLoans ?? 0, icon: 'fas fa-file-invoice-dollar', color: '#0f3460', bg: '#e8f0fe' },
    { label: 'Active Loans', value: activeLoans ?? 0, icon: 'fas fa-check-circle', color: '#16a34a', bg: '#f0fdf4' },
    { label: 'Pending KYC', value: pendingKyc ?? 0, icon: 'fas fa-id-card', color: '#d97706', bg: '#fff7ed', alert: (pendingKyc ?? 0) > 0 },
    { label: 'Loans Awaiting Approval', value: pendingLoans ?? 0, icon: 'fas fa-hourglass-half', color: '#dc2626', bg: '#fff1f2', alert: (pendingLoans ?? 0) > 0 },
  ]

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="fw-bold mb-0">Admin Dashboard</h2>
          <p className="text-muted mb-0">Platform overview and quick actions</p>
        </div>
        <small className="text-muted">{new Date().toLocaleDateString('en-KE', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</small>
      </div>

      {/* Stats Grid */}
      <div className="row g-3 mb-4">
        {stats.map(stat => (
          <div key={stat.label} className="col-6 col-md-4 col-lg">
            <div className="card border-0 shadow-sm h-100" style={{ borderLeft: `4px solid ${stat.color} !important` }}>
              <div className="card-body d-flex align-items-center gap-3">
                <div className="rounded-circle d-flex align-items-center justify-content-center" style={{ width: 48, height: 48, background: stat.bg, minWidth: 48 }}>
                  <i className={stat.icon} style={{ color: stat.color, fontSize: '1.2rem' }}></i>
                </div>
                <div>
                  <div className="fw-bold fs-4 lh-1">
                    {stat.value}
                    {stat.alert && <span className="badge bg-danger ms-2 fs-6">!</span>}
                  </div>
                  <small className="text-muted">{stat.label}</small>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="row g-3 mb-4">
        <div className="col-12">
          <div className="card border-0 shadow-sm">
            <div className="card-body d-flex flex-wrap gap-2">
              <a href="/admin/kyc" className="btn btn-warning btn-sm">
                <i className="fas fa-id-card me-2"></i>Review KYC ({pendingKyc ?? 0} pending)
              </a>
              <a href="/admin/loans" className="btn btn-primary btn-sm">
                <i className="fas fa-file-invoice-dollar me-2"></i>Approve Loans ({pendingLoans ?? 0} pending)
              </a>
              <a href="/admin/users" className="btn btn-outline-secondary btn-sm">
                <i className="fas fa-users me-2"></i>Manage Users
              </a>
              <a href="/admin/commissions" className="btn btn-outline-dark btn-sm">
                <i className="fas fa-percent me-2"></i>Commission Settings
              </a>
            </div>
          </div>
        </div>
      </div>

      <div className="row g-4">
        {/* Recent Loans */}
        <div className="col-md-6">
          <div className="card border-0 shadow-sm">
            <div className="card-header bg-white d-flex justify-content-between align-items-center py-3">
              <h6 className="mb-0 fw-bold"><i className="fas fa-clock me-2 text-primary"></i>Recent Loans</h6>
              <a href="/admin/loans" className="btn btn-sm btn-outline-primary">View All</a>
            </div>
            <div className="card-body p-0">
              <div className="table-responsive">
                <table className="table table-hover mb-0">
                  <thead className="table-light">
                    <tr>
                      <th className="ps-3">Borrower</th>
                      <th>Amount</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentLoans?.map((loan: any) => (
                      <tr key={loan.id}>
                        <td className="ps-3">{loan.borrower?.username || 'N/A'}</td>
                        <td className="fw-bold">KES {parseFloat(loan.principal_amount).toLocaleString()}</td>
                        <td>
                          <span className={`badge bg-${loan.status === 'active' ? 'success' : loan.status === 'pending_approval' ? 'warning text-dark' : 'secondary'}`}>
                            {loan.status.replace('_', ' ')}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Users */}
        <div className="col-md-6">
          <div className="card border-0 shadow-sm">
            <div className="card-header bg-white d-flex justify-content-between align-items-center py-3">
              <h6 className="mb-0 fw-bold"><i className="fas fa-user-plus me-2 text-success"></i>Recent Users</h6>
              <a href="/admin/users" className="btn btn-sm btn-outline-success">View All</a>
            </div>
            <div className="card-body p-0">
              <div className="table-responsive">
                <table className="table table-hover mb-0">
                  <thead className="table-light">
                    <tr>
                      <th className="ps-3">Username</th>
                      <th>Role</th>
                      <th>Joined</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentUsers?.map((u: any) => (
                      <tr key={u.id}>
                        <td className="ps-3 fw-bold">{u.username}</td>
                        <td>
                          <span className={`badge bg-${u.role === 'admin' ? 'danger' : u.role === 'lender' ? 'info' : u.role === 'agent' ? 'warning text-dark' : 'primary'}`}>
                            {u.role}
                          </span>
                        </td>
                        <td className="text-muted"><small>{new Date(u.created_at).toLocaleDateString()}</small></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
