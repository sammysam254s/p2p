import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { approveLoan, rejectLoan } from '../actions'

export default async function AdminLoansPage({
  searchParams,
}: { searchParams: { message?: string; error?: string; status?: string } }) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const statusFilter = searchParams.status || 'all'

  let query = supabase
    .from('loans')
    .select('id, principal_amount, status, interest_rate, duration_months, created_at, borrower:users!loans_borrower_id_fkey(username)')
    .order('created_at', { ascending: false })

  if (statusFilter !== 'all') {
    query = query.eq('status', statusFilter)
  }

  const { data: loans } = await query

  const statusColor: Record<string, string> = {
    pending_approval: 'warning',
    listed: 'primary',
    active: 'success',
    completed: 'secondary',
    rejected: 'danger',
    defaulted: 'dark',
  }

  const statuses = ['all', 'pending_approval', 'listed', 'active', 'completed', 'rejected']

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="fw-bold mb-0"><i className="fas fa-file-invoice-dollar me-2 text-primary"></i>Loan Management</h2>
          <p className="text-muted mb-0">{loans?.length ?? 0} loans found</p>
        </div>
      </div>

      {searchParams.message && (
        <div className="alert alert-success mb-3">
          <i className="fas fa-check-circle me-2"></i>{searchParams.message}
        </div>
      )}

      {/* Filter Tabs */}
      <div className="d-flex gap-2 mb-4 flex-wrap">
        {statuses.map(s => (
          <a
            key={s}
            href={`/admin/loans${s !== 'all' ? `?status=${s}` : ''}`}
            className={`btn btn-sm ${statusFilter === s ? 'btn-primary' : 'btn-outline-secondary'}`}
          >
            {s === 'all' ? 'All' : s.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
          </a>
        ))}
      </div>

      <div className="card border-0 shadow-sm">
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-dark">
                <tr>
                  <th className="ps-4">Loan ID</th>
                  <th>Borrower</th>
                  <th>Amount</th>
                  <th>Rate</th>
                  <th>Duration</th>
                  <th>Status</th>
                  <th>Date</th>
                  <th className="pe-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loans?.map((loan: any) => (
                  <tr key={loan.id}>
                    <td className="ps-4">
                      <a href={`/loan/${loan.id}`} className="text-decoration-none fw-bold">
                        #{loan.id.substring(0, 8).toUpperCase()}
                      </a>
                    </td>
                    <td>{loan.borrower?.username || 'N/A'}</td>
                    <td className="fw-bold">KES {parseFloat(loan.principal_amount).toLocaleString()}</td>
                    <td>{loan.interest_rate ?? 13}%</td>
                    <td>{loan.duration_months}m</td>
                    <td>
                      <span className={`badge bg-${statusColor[loan.status] || 'secondary'}`}>
                        {loan.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="text-muted"><small>{new Date(loan.created_at).toLocaleDateString()}</small></td>
                    <td className="pe-4">
                      <div className="d-flex gap-1">
                        <a href={`/loan/${loan.id}`} className="btn btn-sm btn-outline-info">
                          <i className="fas fa-eye"></i>
                        </a>
                        <a href={`/api/contract/${loan.id}`} className="btn btn-sm btn-outline-secondary" target="_blank" rel="noopener">
                          <i className="fas fa-file-pdf"></i>
                        </a>
                        {loan.status === 'pending_approval' && (
                          <>
                            <form action={approveLoan} className="d-inline">
                              <input type="hidden" name="loan_id" value={loan.id} />
                              <button type="submit" className="btn btn-sm btn-success">Approve</button>
                            </form>
                            <form action={rejectLoan} className="d-inline">
                              <input type="hidden" name="loan_id" value={loan.id} />
                              <button type="submit" className="btn btn-sm btn-danger">Reject</button>
                            </form>
                          </>
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
