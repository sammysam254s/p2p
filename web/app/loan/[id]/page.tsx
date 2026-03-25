import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'

export default async function LoanDetailPage({
  params
}: {
  params: { id: string }
}) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const { data: profile } = await supabase.from('users').select('role').eq('id', user.id).single()

  // Fetch loan with relations
  const { data: loan } = await supabase
    .from('loans')
    .select('*, borrower:users!loans_borrower_id_fkey(username), collateral(*), investments(*, lender:users!investments_lender_id_fkey(username))')
    .eq('id', params.id)
    .single()

  if (!loan) {
    return (
      <div className="container mt-5 text-center">
        <h3>Loan Not Found</h3>
        <p className="text-muted">The loan you are looking for does not exist.</p>
        <a href="/" className="btn btn-primary">Go Home</a>
      </div>
    )
  }

  // Calculations
  const principal = parseFloat(loan.principal_amount)
  const duration = loan.duration_months
  const interest_rate = loan.interest_rate || 13 // default 13%
  
  const total_interest = principal * (interest_rate / 100) * duration
  const platform_fee = principal * 0.01 // 1%
  const insurance_fee = principal * 0.01 // 1%
  const total_repayment = principal + total_interest + platform_fee + insurance_fee
  
  const funded = parseFloat(loan.funded_amount)
  const funding_percentage = principal > 0 ? (funded / principal) * 100 : 0
  
  const market_value = parseFloat(loan.collateral?.market_value || 0)
  const ltv_ratio = market_value > 0 ? (principal / market_value) * 100 : 0

  return (
    <>
      <div className="row">
          <div className="col-12">
              <nav aria-label="breadcrumb">
                  <ol className="breadcrumb">
                      <li className="breadcrumb-item">
                          {profile?.role === 'borrower' ? (
                              <a href="/borrower" className="text-decoration-none">Dashboard</a>
                          ) : profile?.role === 'lender' ? (
                              <a href="/marketplace" className="text-decoration-none">Marketplace</a>
                          ) : (
                              <a href="/" className="text-decoration-none">Home</a>
                          )}
                      </li>
                      <li className="breadcrumb-item active">Loan #{loan.id.substring(0,8)}</li>
                  </ol>
              </nav>
              
              <div className="d-flex justify-content-between align-items-center mb-4">
              <h2 className="mb-0"><i className="fas fa-file-contract me-2 text-primary"></i>Loan #{loan.id.substring(0,8)} Details</h2>
              <a href={`/api/contract/${loan.id}`} className="btn btn-outline-danger" target="_blank" rel="noopener">
                <i className="fas fa-file-pdf me-2"></i>Download Contract
              </a>
          </div>
          </div>
      </div>

      <div className="row">
          {/* Loan Overview */}
          <div className="col-md-8">
              <div className="card shadow-sm border-0 mb-4">
                  <div className="card-header bg-white py-3">
                      <h5 className="mb-0 fw-bold"><i className="fas fa-info-circle me-2 text-info"></i>Loan Overview</h5>
                  </div>
                  <div className="card-body">
                      <div className="row">
                          <div className="col-md-6">
                              <table className="table table-borderless">
                                  <tbody>
                                      <tr>
                                          <td className="text-muted">Borrower:</td>
                                          <td className="fw-bold">{loan.borrower?.username || 'Unknown'}</td>
                                      </tr>
                                      <tr>
                                          <td className="text-muted">Principal Amount:</td>
                                          <td className="fw-bold">KES {principal.toFixed(2)}</td>
                                      </tr>
                                      <tr>
                                          <td className="text-muted">Interest Rate:</td>
                                          <td className="fw-bold">{interest_rate}% per month</td>
                                      </tr>
                                      <tr>
                                          <td className="text-muted">Duration:</td>
                                          <td className="fw-bold">{duration} months</td>
                                      </tr>
                                      <tr>
                                          <td className="text-muted">Status:</td>
                                          <td><span className={`badge bg-${loan.status === 'active' ? 'success' : 'primary'}`}>{loan.status.replace('_', ' ').toUpperCase()}</span></td>
                                      </tr>
                                  </tbody>
                              </table>
                          </div>
                          <div className="col-md-6">
                              <table className="table table-borderless">
                                  <tbody>
                                      <tr>
                                          <td className="text-muted">Created:</td>
                                          <td className="fw-bold">{new Date(loan.created_at).toLocaleDateString()}</td>
                                      </tr>
                                      <tr>
                                          <td className="text-muted">Platform Fee:</td>
                                          <td className="fw-bold">KES {platform_fee.toFixed(2)}</td>
                                      </tr>
                                      <tr>
                                          <td className="text-muted">Insurance Fee:</td>
                                          <td className="fw-bold">KES {insurance_fee.toFixed(2)}</td>
                                      </tr>
                                      <tr>
                                          <td className="text-muted">Monthly Interest:</td>
                                          <td className="fw-bold">KES {(total_interest / duration).toFixed(2)}</td>
                                      </tr>
                                      <tr className="border-top">
                                          <td className="text-muted pt-3">Total Repayment:</td>
                                          <td className="pt-3"><strong className="text-primary fs-5">KES {total_repayment.toFixed(2)}</strong></td>
                                      </tr>
                                  </tbody>
                              </table>
                          </div>
                      </div>
                  </div>
              </div>

              {/* Collateral Details */}
              <div className="card shadow-sm border-0 mb-4">
                  <div className="card-header bg-white py-3">
                      <h5 className="mb-0 fw-bold"><i className="fas fa-shield-alt me-2 text-warning"></i>Collateral Details</h5>
                  </div>
                  <div className="card-body">
                      <div className="row">
                          <div className="col-md-6">
                              <h6 className="text-primary mb-3">Item Information</h6>
                              <table className="table table-borderless">
                                  <tbody>
                                      <tr>
                                          <td className="text-muted">Type:</td>
                                          <td className="fw-bold">{loan.collateral?.item_type}</td>
                                      </tr>
                                      <tr>
                                          <td className="text-muted">Brand & Model:</td>
                                          <td className="fw-bold">{loan.collateral?.brand_model}</td>
                                      </tr>
                                      <tr>
                                          <td className="text-muted">Market Value:</td>
                                          <td className="fw-bold">KES {market_value.toFixed(2)}</td>
                                      </tr>
                                      <tr>
                                          <td className="text-muted">Max Loan (35%):</td>
                                          <td className="fw-bold text-success">KES {(market_value * 0.35).toFixed(2)}</td>
                                      </tr>
                                  </tbody>
                              </table>
                          </div>
                          <div className="col-md-6">
                              <h6 className="text-primary mb-3">Verification Status</h6>
                              <table className="table table-borderless">
                                  <tbody>
                                      <tr>
                                          <td className="text-muted">Status:</td>
                                          <td><span className={`badge bg-${loan.collateral?.status === 'verified' ? 'success' : 'warning text-dark'}`}>{loan.collateral?.status.toUpperCase()}</span></td>
                                      </tr>
                                      <tr>
                                          <td className="text-muted">Loan-to-Value:</td>
                                          <td className="fw-bold">{ltv_ratio.toFixed(1)}%</td>
                                      </tr>
                                  </tbody>
                              </table>
                          </div>
                      </div>
                  </div>
              </div>

              {/* Investment History */}
              {loan.investments && loan.investments.length > 0 && (
              <div className="card shadow-sm border-0 mb-4">
                  <div className="card-header bg-white py-3">
                      <h5 className="mb-0 fw-bold"><i className="fas fa-history me-2 text-success"></i>Investment History</h5>
                  </div>
                  <div className="card-body p-0">
                      <div className="table-responsive">
                          <table className="table table-hover align-middle mb-0">
                              <thead className="table-light">
                                  <tr>
                                      <th className="ps-4">Investor</th>
                                      <th>Amount</th>
                                      <th>Date</th>
                                      <th>Share</th>
                                  </tr>
                              </thead>
                              <tbody>
                                  {loan.investments.map((inv: any) => {
                                      const invAmount = parseFloat(inv.amount_invested)
                                      return (
                                      <tr key={inv.id}>
                                          <td className="ps-4 fw-bold">{inv.lender?.username || 'Unknown'}</td>
                                          <td className="text-success fw-bold">KES {invAmount.toFixed(2)}</td>
                                          <td className="text-muted"><small>{new Date(inv.created_at).toLocaleDateString()}</small></td>
                                          <td><span className="badge bg-light text-dark border">{(principal > 0 ? (invAmount/principal)*100 : 0).toFixed(1)}%</span></td>
                                      </tr>
                                  )})}
                              </tbody>
                          </table>
                      </div>
                  </div>
              </div>
              )}
          </div>

          <div className="col-md-4">
              {/* Funding Status */}
              {loan.status === 'listed' && (
              <div className="card shadow-sm border-0 mb-4">
                  <div className="card-header bg-primary text-white py-3">
                      <h6 className="mb-0 fw-bold"><i className="fas fa-chart-pie me-2"></i>Funding Status</h6>
                  </div>
                  <div className="card-body text-center">
                      <div className="mb-3">
                          <h2 className="text-primary fw-bold display-5">{funding_percentage.toFixed(1)}%</h2>
                          <p className="text-muted">Funded</p>
                      </div>
                      
                      <div className="progress mb-4" style={{height: '12px'}}>
                          <div className="progress-bar bg-success" style={{width: `${funding_percentage}%`}}></div>
                      </div>
                      
                      <div className="row text-center mb-3">
                          <div className="col-6 border-end">
                              <h5 className="fw-bold mb-0">KES {principal.toFixed(2)}</h5>
                              <small className="text-muted">Total Needed</small>
                          </div>
                          <div className="col-6">
                              <h5 className="fw-bold text-success mb-0">KES {funded.toFixed(2)}</h5>
                              <small className="text-muted">Currently Funded</small>
                          </div>
                      </div>
                  </div>
              </div>
              )}

              {/* Loan Calculator */}
              <div className="card shadow-sm border-0">
                  <div className="card-header bg-info text-white py-3">
                      <h6 className="mb-0 fw-bold"><i className="fas fa-calculator me-2"></i>Repayment Breakdown</h6>
                  </div>
                  <div className="card-body">
                      <table className="table table-sm border-white">
                          <tbody>
                              <tr>
                                  <td className="text-muted border-0">Principal Amount:</td>
                                  <td className="text-end fw-bold border-0">KES {principal.toFixed(2)}</td>
                              </tr>
                              <tr>
                                  <td className="text-muted border-0">Interest ({interest_rate}% × {duration}m):</td>
                                  <td className="text-end border-0">KES {total_interest.toFixed(2)}</td>
                              </tr>
                              <tr>
                                  <td className="text-muted border-bottom">Fees (Platform + Insur.):</td>
                                  <td className="text-end border-bottom">KES {(platform_fee + insurance_fee).toFixed(2)}</td>
                              </tr>
                              <tr>
                                  <td className="pt-3 border-0"><strong className="text-primary">Total Repayment:</strong></td>
                                  <td className="text-end pt-3 border-0"><strong className="text-primary">KES {total_repayment.toFixed(2)}</strong></td>
                              </tr>
                          </tbody>
                      </table>
                      
                      <div className="alert alert-info mt-3 mb-0 border-0 bg-info bg-opacity-10 text-center">
                          <small className="text-dark"><strong>Monthly Payment:</strong> KES {(total_repayment / duration).toFixed(2)}</small>
                      </div>
                  </div>
              </div>
          </div>
      </div>
    </>
  )
}
