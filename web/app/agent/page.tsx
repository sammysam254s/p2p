import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { verifyCollateral } from './actions'

export default async function AgentPanelPage({
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

  if (profile.role !== 'agent' && profile.role !== 'admin') {
    redirect('/')
  }

  // Fetch pending collaterals with linked user and loan
  const { data: pending_collaterals } = await supabase
    .from('collateral')
    .select('*, user:users(*), loan:loans(*)')
    .eq('status', 'pending')
    .order('created_at', { ascending: false })

  const total_pending = pending_collaterals?.length || 0

  return (
    <>
      <div className="row">
          <div className="col-12">
              <h2><i className="fas fa-shield-alt me-2 text-info"></i>Station Agent Panel</h2>
              <p className="text-muted">Verify and receive collateral items from borrowers</p>
          </div>
      </div>

      {profile.role === 'admin' && (
      <div className="row mb-4">
          <div className="col-12">
              <div className="alert alert-info">
                  <h5><i className="fas fa-crown me-2"></i>Admin Access</h5>
                  <p className="mb-0">You are viewing the agent panel as an administrator. You have full access to all features.</p>
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

      <div className="row">
          <div className="col-12">
              <div className="card shadow-sm border-0">
                  <div className="card-header bg-white py-3">
                      <h5 className="mb-0 fw-bold"><i className="fas fa-clock me-2 text-warning"></i>Pending Collateral Verification</h5>
                  </div>
                  <div className="card-body bg-light">
                      {pending_collaterals && pending_collaterals.length > 0 ? (
                          <>
                              <div className="alert alert-info mb-4 border-0 shadow-sm">
                                  <i className="fas fa-info-circle me-2"></i>
                                  <strong>{total_pending}</strong> collateral item(s) pending verification.
                              </div>
                              
                              <div className="table-responsive">
                                  <table className="table table-hover align-middle bg-white rounded shadow-sm">
                                      <thead className="table-light">
                                          <tr>
                                              <th>Borrower</th>
                                              <th>Item Details</th>
                                              <th>Loan Request</th>
                                              <th>Estimated Value</th>
                                              <th>Action</th>
                                          </tr>
                                      </thead>
                                      <tbody>
                                          {pending_collaterals.map((item) => {
                                              // Supabase joins arrays for 1:N relations, but loan is 1:1 linked to collateral.
                                              // The select('*, loan:loans(*)') will return an array of loans.
                                              const linkedLoan = Array.isArray(item.loan) && item.loan.length > 0 ? item.loan[0] : null
                                              
                                              return (
                                              <tr key={item.id}>
                                                  <td>
                                                      <div className="d-flex align-items-center">
                                                          <div className="avatar-sm bg-primary rounded-circle d-flex align-items-center justify-content-center me-2 p-2">
                                                              <i className="fas fa-user text-white"></i>
                                                          </div>
                                                          <div>
                                                              <div className="fw-bold">{item.user?.username || 'Unknown'}</div>
                                                              <small className="text-muted">{item.user?.email || ''}</small>
                                                          </div>
                                                      </div>
                                                  </td>
                                                  <td>
                                                      <div>
                                                          <span className="badge bg-info mb-1">{item.item_type}</span>
                                                          <div className="fw-bold">{item.brand_model}</div>
                                                      </div>
                                                  </td>
                                                  <td>
                                                      {linkedLoan ? (
                                                          <>
                                                            <div className="text-success fw-bold">KES {parseFloat(linkedLoan.principal_amount).toFixed(2)}</div>
                                                            <small className="badge bg-warning text-dark">{linkedLoan.duration_months} months</small>
                                                          </>
                                                      ) : (
                                                          <span className="text-muted">No loan found</span>
                                                      )}
                                                  </td>
                                                  <td>
                                                      <div className="text-primary fw-bold">KES {parseFloat(item.market_value).toFixed(2)}</div>
                                                      <small className="text-muted">Max loan: ~35% of value</small>
                                                  </td>
                                                  <td>
                                                      {/* Inline form for verification, since we are not using bootstrap JS for modals in Next.js right now. */}
                                                      <details className="dropdown">
                                                          <summary className="btn btn-success btn-sm custom-summary"><i className="fas fa-check me-1"></i>Verify</summary>
                                                          <div className="p-3 bg-white border rounded shadow-sm position-absolute" style={{right: 0, minWidth: '300px', zIndex: 1000}}>
                                                              <h6 className="fw-bold mb-3"><i className="fas fa-check-circle me-2 text-success"></i>Verify Collateral Form</h6>
                                                              <form action={verifyCollateral}>
                                                                  <input type="hidden" name="collateral_id" value={item.id} />
                                                                  <div className="mb-2">
                                                                      <label className="form-label small fw-bold">Verified Market Value (KES)</label>
                                                                      <input type="number" name="verified_value" className="form-control form-control-sm" defaultValue={item.market_value} min="1000" step="100" required />
                                                                  </div>
                                                                  <div className="mb-3">
                                                                      <label className="form-label small fw-bold">Agent Notes</label>
                                                                      <textarea name="agent_notes" className="form-control form-control-sm" rows={2} placeholder="Observations..."></textarea>
                                                                  </div>
                                                                  <button type="submit" className="btn btn-success btn-sm w-100 fw-bold">Confirm Verification</button>
                                                              </form>
                                                          </div>
                                                      </details>
                                                  </td>
                                              </tr>
                                          )})}
                                      </tbody>
                                  </table>
                              </div>
                          </>
                      ) : (
                          <div className="text-center py-5">
                              <i className="fas fa-check-circle fa-4x text-success mb-3 opacity-50"></i>
                              <h4 className="text-muted fw-bold">No Pending Verifications</h4>
                              <p className="text-muted">All collateral items have been processed.</p>
                          </div>
                      )}
                  </div>
              </div>
          </div>
      </div>

      {/* Instructions Card */}
      <div className="row mt-4 mb-5">
          <div className="col-12">
              <div className="card shadow-sm border-0">
                  <div className="card-header bg-info text-white py-3">
                      <h6 className="mb-0 fw-bold"><i className="fas fa-info-circle me-2"></i>Verification Process</h6>
                  </div>
                  <div className="card-body">
                      <div className="row">
                          <div className="col-md-6 mb-3 mb-md-0">
                              <h6 className="fw-bold text-primary">Before Verification:</h6>
                              <ul className="text-muted">
                                  <li>Physically inspect the item for authenticity</li>
                                  <li>Check for any damage or defects</li>
                                  <li>Verify the item matches the description</li>
                                  <li>Confirm the borrower's identity</li>
                              </ul>
                          </div>
                          <div className="col-md-6">
                              <h6 className="fw-bold text-success">After Verification:</h6>
                              <ul className="text-muted">
                                  <li>Store the item securely</li>
                                  <li>Issue a receipt to the borrower</li>
                                  <li>The loan will be listed on the marketplace</li>
                              </ul>
                          </div>
                      </div>
                      
                      <div className="alert alert-warning mt-3 mb-0 border-0">
                          <strong>Important:</strong> Only verify items that you have physically received and confirmed. 
                          Once verified, the loan becomes available for funding on the marketplace.
                      </div>
                  </div>
              </div>
          </div>
      </div>
    </>
  )
}
