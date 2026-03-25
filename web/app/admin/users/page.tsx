import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { banUser, activateUser, changeUserRole } from '../actions'

export default async function AdminUsersPage({
  searchParams,
}: { searchParams: { message?: string; error?: string; q?: string } }) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const q = searchParams.q || ''

  let query = supabase
    .from('users')
    .select('id, username, email, role, is_active, kyc_verified, wallet_balance, created_at')
    .order('created_at', { ascending: false })

  if (q) {
    query = query.or(`username.ilike.%${q}%,email.ilike.%${q}%`)
  }

  const { data: users } = await query

  const roleBadge = (role: string) => {
    const map: Record<string, string> = { admin: 'danger', lender: 'info', agent: 'warning', borrower: 'primary' }
    return map[role] || 'secondary'
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="fw-bold mb-0"><i className="fas fa-users me-2 text-primary"></i>User Management</h2>
          <p className="text-muted mb-0">{users?.length ?? 0} users registered on the platform</p>
        </div>
      </div>

      {searchParams.message && (
        <div className="alert alert-success alert-dismissible fade show mb-3">
          <i className="fas fa-check-circle me-2"></i>{searchParams.message}
        </div>
      )}
      {searchParams.error && (
        <div className="alert alert-danger mb-3">
          <i className="fas fa-exclamation-triangle me-2"></i>{searchParams.error}
        </div>
      )}

      {/* Search */}
      <form className="mb-4" method="get">
        <div className="input-group shadow-sm" style={{ maxWidth: 400 }}>
          <input type="text" name="q" defaultValue={q} className="form-control" placeholder="Search by username or email..." />
          <button className="btn btn-primary" type="submit"><i className="fas fa-search"></i></button>
          {q && <a href="/admin/users" className="btn btn-outline-secondary">Clear</a>}
        </div>
      </form>

      <div className="card border-0 shadow-sm">
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-dark">
                <tr>
                  <th className="ps-4">User</th>
                  <th>Role</th>
                  <th>KYC</th>
                  <th>Wallet</th>
                  <th>Status</th>
                  <th>Joined</th>
                  <th className="pe-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users?.map((u: any) => (
                  <tr key={u.id}>
                    <td className="ps-4">
                      <div className="fw-bold">{u.username}</div>
                      <small className="text-muted">{u.email}</small>
                    </td>
                    <td>
                      <span className={`badge bg-${roleBadge(u.role)}`}>{u.role}</span>
                    </td>
                    <td>
                      {u.kyc_verified
                        ? <span className="badge bg-success"><i className="fas fa-check me-1"></i>Verified</span>
                        : <span className="badge bg-secondary">Unverified</span>}
                    </td>
                    <td className="fw-bold">KES {parseFloat(u.wallet_balance || 0).toLocaleString()}</td>
                    <td>
                      {u.is_active !== false
                        ? <span className="badge bg-success">Active</span>
                        : <span className="badge bg-danger">Banned</span>}
                    </td>
                    <td className="text-muted"><small>{new Date(u.created_at).toLocaleDateString()}</small></td>
                    <td className="pe-4">
                      <div className="d-flex gap-1 flex-wrap">
                        {/* Change role */}
                        <form action={changeUserRole}>
                          <input type="hidden" name="user_id" value={u.id} />
                          <select name="role" className="form-select form-select-sm" style={{ width: 'auto' }} defaultValue={u.role}>
                            <option value="borrower">Borrower</option>
                            <option value="lender">Lender</option>
                            <option value="agent">Agent</option>
                            <option value="admin">Admin</option>
                          </select>
                          <button className="btn btn-sm btn-outline-primary mt-1 w-100" type="submit">Set Role</button>
                        </form>

                        {u.is_active !== false ? (
                          <form action={banUser}>
                            <input type="hidden" name="user_id" value={u.id} />
                            <button className="btn btn-sm btn-outline-danger" type="submit">Ban</button>
                          </form>
                        ) : (
                          <form action={activateUser}>
                            <input type="hidden" name="user_id" value={u.id} />
                            <button className="btn btn-sm btn-outline-success" type="submit">Activate</button>
                          </form>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
