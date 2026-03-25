import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'

export default async function BorrowerDashboard() {
  const supabase = createClient()
  
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) {
    redirect('/login')
  }

  // Fetch user profile
  const { data: profile } = await supabase
    .from('users')
    .select('*')
    .eq('id', user.id)
    .single()

  if (!profile) {
    redirect('/login')
  }

  // Access control
  if (profile.role !== 'borrower' && profile.role !== 'admin') {
    redirect('/')
  }

  // Fetch loans & collaterals
  const { data: loans } = await supabase
    .from('loans')
    .select('*, collateral(*)')
    .eq('borrower_id', user.id)
    .order('created_at', { ascending: false })

  // Calculate stats
  const totalLoans = loans?.length || 0
  let totalBorrowed = 0
  let totalOutstanding = 0

  loans?.forEach((loan) => {
    if (loan.status === 'active' || loan.status === 'paid') {
      totalBorrowed += parseFloat(loan.principal_amount)
    }
    if (loan.status === 'active') {
      // rough calculation based on Django's 13% interest
      const interest = parseFloat(loan.principal_amount) * 0.13 * loan.duration_months
      const totalRepayable = parseFloat(loan.principal_amount) + interest
      totalOutstanding += totalRepayable // Simplification for now
    }
  })

  return (
    <>
      <div className="row">
          <div className="col-12">
              <h2><i className="fas fa-hand-holding-usd me-2 text-primary"></i>Borrower Dashboard</h2>
              <p className="text-muted">Manage your loans and collateral</p>
          </div>
      </div>

      {profile.role === 'admin' && (
        <div className="row mb-4">
            <div className="col-12">
                <div className="alert alert-info">
                    <h5><i className="fas fa-crown me-2"></i>Admin Access</h5>
                    <p className="mb-0">You are viewing the borrower dashboard as an administrator.</p>
                </div>
            </div>
        </div>
      )}

      {/* KYC Alert */}
      <div className="row mb-4">
          <div className="col-12">
              <div className="d-flex justify-content-between align-items-center mb-3">
                  <h4><i className="fas fa-id-card me-2 text-warning"></i>Identity Verification Status</h4>
                  <a href="/kyc" className="btn btn-warning">
                      <i className="fas fa-id-card me-1"></i>
                      {profile.kyc_verified ? 'View KYC Details' : 'Complete KYC'}
                  </a>
              </div>
              
              {profile.kyc_verified ? (
                  <div className="alert alert-success alert-dismissible fade show">
                      <h5><i className="fas fa-check-circle me-2"></i>✅ Identity Verified Successfully!</h5>
                      <p className="mb-2">Your identity has been verified and you can now apply for loans and access all borrower features.</p>
                  </div>
              ) : (
                  <div className="alert alert-warning alert-dismissible fade show">
                      <h5><i className="fas fa-exclamation-triangle me-2"></i>Identity Verification Required</h5>
                      <p className="mb-2"><strong>Important:</strong> You must complete identity verification before applying for loans. This is a mandatory security requirement.</p>
                  </div>
              )}
          </div>
      </div>

      {/* Quick Stats */}
      <div className="row mb-4">
          <div className="col-md-3 mb-3">
              <div className="card shadow-sm h-100">
                  <div className="card-body text-center">
                      <i className="fas fa-wallet fa-2x text-success mb-2"></i>
                      <h4 className="text-success">KES {(profile.wallet_balance || 0).toFixed(2)}</h4>
                      <p className="text-muted mb-0">Wallet Balance</p>
                  </div>
              </div>
          </div>
          <div className="col-md-3 mb-3">
              <div className="card shadow-sm h-100">
                  <div className="card-body text-center">
                      <i className="fas fa-coins fa-2x text-primary mb-2"></i>
                      <h4 className="text-primary">{totalLoans}</h4>
                      <p className="text-muted mb-0">Total Loans</p>
                  </div>
              </div>
          </div>
          <div className="col-md-3 mb-3">
              <div className="card shadow-sm h-100">
                  <div className="card-body text-center">
                      <i className="fas fa-money-bill-wave fa-2x text-info mb-2"></i>
                      <h4 className="text-info">KES {totalBorrowed.toFixed(2)}</h4>
                      <p className="text-muted mb-0">Total Borrowed</p>
                  </div>
              </div>
          </div>
          <div className="col-md-3 mb-3">
              <div className="card shadow-sm h-100">
                  <div className="card-body text-center">
                      <i className="fas fa-exclamation-triangle fa-2x text-warning mb-2"></i>
                      <h4 className="text-warning">KES {totalOutstanding.toFixed(2)}</h4>
                      <p className="text-muted mb-0">Outstanding</p>
                  </div>
              </div>
          </div>
      </div>

      {/* Loans List */}
      <div className="row mb-4">
          <div className="col-12">
              <div className="card shadow-sm">
                  <div className="card-header bg-white d-flex justify-content-between align-items-center py-3">
                      <h5 className="mb-0 fw-bold"><i className="fas fa-list me-2"></i>My Loans</h5>
                      {profile.kyc_verified && (
                          <a href="/borrower/loan-apply" className="btn btn-primary btn-sm">
                              <i className="fas fa-plus me-1"></i>Apply for Loan
                          </a>
                      )}
                  </div>
                  <div className="card-body">
                      {loans && loans.length > 0 ? (
                          <div className="table-responsive">
                              <table className="table table-hover align-middle">
                                  <thead className="table-light">
                                      <tr>
                                          <th>Loan ID</th>
                                          <th>Amount (KES)</th>
                                          <th>Status</th>
                                          <th>Collateral</th>
                                          <th>Actions</th>
                                      </tr>
                                  </thead>
                                  <tbody>
                                      {loans.map((loan) => (
                                          <tr key={loan.id}>
                                              <td><small className="text-muted">#{loan.id.substring(0, 8)}</small></td>
                                              <td className="fw-bold">{parseFloat(loan.principal_amount).toFixed(2)}</td>
                                              <td>
                                                  <span className={`badge bg-${loan.status === 'active' ? 'success' : loan.status === 'pending_collateral' ? 'warning text-dark' : 'primary'}`}>
                                                      {loan.status.replace('_', ' ').toUpperCase()}
                                                  </span>
                                              </td>
                                              <td>{loan.collateral?.brand_model || 'N/A'}</td>
                                              <td>
                                                  <a href={`/loan/${loan.id}`} className="btn btn-outline-primary btn-sm">
                                                      <i className="fas fa-eye me-1"></i>View
                                                  </a>
                                              </td>
                                          </tr>
                                      ))}
                                  </tbody>
                              </table>
                          </div>
                      ) : (
                          <div className="text-center py-5">
                              <i className="fas fa-folder-open fa-3x text-muted mb-3"></i>
                              <h5 className="text-muted">No Loans Yet</h5>
                              {profile.kyc_verified ? (
                                  <p className="text-muted">Ready to apply for your first loan?</p>
                              ) : (
                                  <p className="text-muted">Complete KYC verification to start borrowing.</p>
                              )}
                          </div>
                      )}
                  </div>
              </div>
          </div>
      </div>
    </>
  )
}
