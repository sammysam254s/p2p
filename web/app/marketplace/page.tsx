import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { investInLoan, walletDeposit } from './actions'

export default async function MarketplacePage({
  searchParams
}: { searchParams: { error?: string, message?: string } }) {
  const supabase = createClient()
  
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  // Fetch user profile
  const { data: profile } = await supabase
    .from('users')
    .select('*')
    .eq('id', user.id)
    .single()

  if (!profile) redirect('/login')

  if (profile.role !== 'lender' && profile.role !== 'admin') {
    redirect('/')
  }

  // Fetch listed loans
  const { data: listed_loans } = await supabase
    .from('loans')
    .select('*, collateral(*)')
    .eq('status', 'listed')
    .order('created_at', { ascending: false })

  // Fetch user investments
  const { data: my_investments } = await supabase
    .from('investments')
    .select('*, loan:loans(*, collateral(*))')
    .eq('lender_id', user.id)


  return (
    <>
      <div className="row">
          <div className="col-12">
              <h2><i className="fas fa-store me-2 text-primary"></i>Investment Marketplace</h2>
              <p className="text-muted">Invest in secured loans and earn 13% monthly returns</p>
          </div>
      </div>

      {profile.role === 'admin' && (
      <div className="row mb-4">
          <div className="col-12">
              <div className="alert alert-info">
                  <h5><i className="fas fa-crown me-2"></i>Admin Access</h5>
                  <p className="mb-0">You are viewing the lender marketplace as an administrator. You have full access to all features.</p>
              </div>
          </div>
      </div>
      )}

      {searchParams.error && (
        <div className="alert alert-danger mb-4">
          <i className="fas fa-exclamation-triangle me-2"></i>
          {searchParams.error}
        </div>
      )}

      {searchParams.message && (
        <div className="alert alert-success mb-4">
          <i className="fas fa-check-circle me-2"></i>
          {searchParams.message}
        </div>
      )}

      {/* Investment Summary */}
      <div className="row mb-4">
          <div className="col-md-4 mb-3 mb-md-0">
              <div className="card text-center shadow-sm h-100">
                  <div className="card-body">
                      <i className="fas fa-chart-line fa-2x text-success mb-2"></i>
                      <h5>Available Loans</h5>
                      <h3 className="text-success">{listed_loans?.length || 0}</h3>
                  </div>
              </div>
          </div>
          <div className="col-md-4 mb-3 mb-md-0">
              <div className="card text-center shadow-sm h-100">
                  <div className="card-body">
                      <i className="fas fa-wallet fa-2x text-primary mb-2"></i>
                      <h5>Your Wallet Balance</h5>
                      <h3 className="text-primary">KES {(profile.wallet_balance || 0).toFixed(2)}</h3>
                      <small className="text-muted">Available for investments</small>
                      
                      {/* Using HTML details/summary as a lightweight dropdown hack so we don't need bootstrap JS modal */}
                      <details className="mt-2 text-start bg-light p-2 rounded">
                        <summary className="text-success fw-bold" style={{cursor: 'pointer'}}>+ Deposit Funds</summary>
                        <form action={walletDeposit} className="mt-2">
                           <input type="number" name="amount" min="10" placeholder="Amount (KES)" className="form-control form-control-sm mb-2" required />
                           <button type="submit" className="btn btn-sm btn-success w-100">Simulate Deposit</button>
                        </form>
                      </details>
                  </div>
              </div>
          </div>
          <div className="col-md-4 mb-3 mb-md-0">
              <div className="card text-center shadow-sm h-100">
                  <div className="card-body">
                      <i className="fas fa-shield-alt fa-2x text-info mb-2"></i>
                      <h5>Security</h5>
                      <h3 className="text-info">100% <small>collateralized</small></h3>
                  </div>
              </div>
          </div>
      </div>

      {/* Available Loans */}
      <div className="row mb-5">
          <div className="col-12">
              <div className="card shadow-sm">
                  <div className="card-header bg-white py-3">
                      <h5 className="mb-0"><i className="fas fa-coins me-2 text-warning"></i>Available Investment Opportunities</h5>
                  </div>
                  <div className="card-body bg-light">
                      {listed_loans && listed_loans.length > 0 ? (
                          <div className="row">
                              {listed_loans.map((loan) => {
                                  const principal = parseFloat(loan.principal_amount)
                                  const funded = parseFloat(loan.funded_amount)
                                  const progress = principal > 0 ? (funded / principal) * 100 : 0
                                  const monthlyReturn = principal * 0.13
                                  
                                  return (
                                  <div className="col-md-6 col-lg-4 mb-4" key={loan.id}>
                                      <div className="card h-100 shadow-sm border-0">
                                          <div className="card-header bg-primary text-white py-2">
                                              <h6 className="mb-0"><i className="fas fa-lock me-2"></i>Loan #{loan.id.substring(0,8)}</h6>
                                          </div>
                                          <div className="card-body">
                                              <div className="mb-3">
                                                  <h6 className="text-muted">Collateral</h6>
                                                  <p className="mb-1 fw-bold">{loan.collateral?.brand_model || 'Unknown'}</p>
                                                  <small className="text-muted">{loan.collateral?.item_type || 'Asset'}</small>
                                              </div>
                                              
                                              <div className="row mb-3">
                                                  <div className="col-6">
                                                      <small className="text-muted">Amount Needed</small>
                                                      <h5 className="text-primary fw-bold">KES {principal.toFixed(2)}</h5>
                                                  </div>
                                                  <div className="col-6">
                                                      <small className="text-muted">Duration</small>
                                                      <h5 className="fw-bold">{loan.duration_months} mth</h5>
                                                  </div>
                                              </div>
                                              
                                              <div className="mb-3">
                                                  <div className="d-flex justify-content-between mb-1">
                                                      <small className="text-muted">Funding Progress</small>
                                                      <small className="text-muted">{progress.toFixed(1)}%</small>
                                                  </div>
                                                  <div className="progress mb-2" style={{height: '8px'}}>
                                                      <div className="progress-bar bg-success" style={{ width: `${progress}%` }}></div>
                                                  </div>
                                                  <div className="d-flex justify-content-between">
                                                      <small className="text-success fw-bold">KES {funded.toFixed(2)} funded</small>
                                                  </div>
                                              </div>
                                              
                                              <div className="alert alert-success py-2 mb-0 border-0 bg-success bg-opacity-10">
                                                  <small className="fw-bold text-success">Expected Returns:</small><br/>
                                                  <small className="text-dark">Monthly: KES {monthlyReturn.toFixed(2)}</small>
                                              </div>
                                          </div>
                                          
                                          <div className="card-footer bg-white border-0 pt-0 pb-3">
                                              {progress < 100 ? (
                                                  <form action={investInLoan}>
                                                      <input type="hidden" name="loan_id" value={loan.id} />
                                                      <div className="input-group mb-2 shadow-sm">
                                                          <span className="input-group-text bg-light border-0">KES</span>
                                                          <input type="number" name="investment_amount" className="form-control border-0 bg-light" placeholder="Amount" min="100" max={principal - funded} step="0.01" required />
                                                      </div>
                                                      <button type="submit" className="btn btn-success w-100 fw-bold shadow-sm">
                                                          <i className="fas fa-hand-holding-usd me-2"></i>Invest Now
                                                      </button>
                                                  </form>
                                              ) : (
                                                  <button className="btn btn-secondary w-100" disabled>
                                                      <i className="fas fa-check me-2"></i>Fully Funded
                                                  </button>
                                              )}
                                          </div>
                                      </div>
                                  </div>
                              )})}
                          </div>
                      ) : (
                          <div className="text-center py-5">
                              <i className="fas fa-search fa-4x text-muted mb-3 opacity-50"></i>
                              <h4 className="text-muted fw-bold">No Investment Opportunities</h4>
                              <p className="text-muted">Check back later for new loan listings</p>
                          </div>
                      )}
                  </div>
              </div>
          </div>
      </div>

      {/* My Investments */}
      {my_investments && my_investments.length > 0 && (
        <div className="row mb-5">
            <div className="col-12">
                <div className="card shadow-sm border-0">
                    <div className="card-header bg-success text-white py-3">
                        <h5 className="mb-0"><i className="fas fa-file-contract me-2"></i>My Investment Contracts</h5>
                    </div>
                    <div className="card-body">
                        <div className="row">
                            {my_investments.map((inv) => (
                              <div className="col-md-6 col-lg-4 mb-3" key={inv.id}>
                                  <div className="card border-success border-2 shadow-sm h-100">
                                      <div className="card-body">
                                          <div className="d-flex align-items-center mb-3">
                                              <i className="fas fa-file-pdf fa-2x text-danger me-3"></i>
                                              <div>
                                                  <h6 className="mb-1 fw-bold">Loan #{inv.loan_id.substring(0,8)}</h6>
                                                  <small className="text-muted">{inv.loan?.collateral?.brand_model || 'Asset'}</small>
                                              </div>
                                          </div>
                                          
                                          <div className="row mb-3 gx-2">
                                              <div className="col-6">
                                                  <div className="text-center bg-success bg-opacity-10 p-2 rounded">
                                                      <div className="fw-bold text-success">KES {parseFloat(inv.amount_invested).toFixed(2)}</div>
                                                      <small className="text-muted" style={{fontSize: '0.75rem'}}>My Investment</small>
                                                  </div>
                                              </div>
                                              <div className="col-6">
                                                  <div className="text-center bg-primary bg-opacity-10 p-2 rounded">
                                                      <div className="fw-bold text-primary">KES {parseFloat(inv.loan?.principal_amount || 0).toFixed(2)}</div>
                                                      <small className="text-muted" style={{fontSize: '0.75rem'}}>Total Loan</small>
                                                  </div>
                                              </div>
                                          </div>
                                          
                                          <div className="text-center">
                                              <a href={`/loan/${inv.loan_id}`} className="btn btn-outline-primary btn-sm w-100">
                                                  <i className="fas fa-eye me-1"></i>View Details
                                              </a>
                                          </div>
                                      </div>
                                  </div>
                              </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
      )}
    </>
  )
}
