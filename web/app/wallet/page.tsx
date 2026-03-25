import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { depositFunds, withdrawFunds } from './actions'

export default async function WalletPage({
  searchParams
}: { searchParams: { error?: string, message?: string } }) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const { data: profile } = await supabase
    .from('users')
    .select('wallet_balance')
    .eq('id', user.id)
    .single()

  const balance = profile?.wallet_balance || 0

  // Fetch transaction history
  const { data: transactions } = await supabase
    .from('wallet_transactions')
    .select('*')
    .eq('user_id', user.id)
    .order('created_at', { ascending: false })
    .limit(50)

  return (
    <>
      <div className="row mb-2">
        <div className="col-12">
          <nav aria-label="breadcrumb">
            <ol className="breadcrumb">
              <li className="breadcrumb-item"><a href="/" className="text-decoration-none">Home</a></li>
              <li className="breadcrumb-item active">Wallet Management</li>
            </ol>
          </nav>
          <h2><i className="fas fa-wallet me-2 text-success"></i>Wallet Management</h2>
          <p className="text-muted">Manage your wallet balance and transaction history</p>
        </div>
      </div>

      <div className="alert alert-info alert-dismissible fade show mb-4">
        <i className="fas fa-info-circle me-2"></i>
        <strong>🎮 Demo Mode Active:</strong> This is a simulation environment. No real money is processed.
      </div>

      {searchParams.error && (
        <div className="alert alert-danger mb-4">
          <i className="fas fa-exclamation-triangle me-2"></i>{searchParams.error}
        </div>
      )}
      {searchParams.message && (
        <div className="alert alert-success mb-4">
          <i className="fas fa-check-circle me-2"></i>{searchParams.message}
        </div>
      )}

      {/* Wallet Summary */}
      <div className="row mb-4">
        <div className="col-md-4 mb-3">
          <div className="card text-center shadow-sm h-100 border-0">
            <div className="card-body py-4">
              <i className="fas fa-wallet fa-3x text-success mb-3"></i>
              <h3 className="text-success fw-bold">KES {balance.toFixed(2)}</h3>
              <p className="text-muted mb-0">Current Balance</p>
            </div>
          </div>
        </div>
        <div className="col-md-4 mb-3">
          <div className="card text-center shadow-sm h-100 border-0">
            <div className="card-body py-4">
              <i className="fas fa-arrow-down fa-3x text-primary mb-3"></i>
              <h5 className="text-primary">Deposit Funds</h5>
              <details className="mt-2 text-start">
                <summary className="btn btn-primary btn-sm px-4" style={{ listStyle: 'none', cursor: 'pointer' }}>
                  <i className="fas fa-plus me-1"></i>Deposit Now
                </summary>
                <div className="mt-2 p-3 bg-light rounded shadow-sm">
                  <form action={depositFunds}>
                    <div className="d-flex gap-1 mb-2 flex-wrap">
                      {[1000, 5000, 10000, 25000].map(q => (
                        <button key={q} type="submit" name="amount" value={String(q)} className="btn btn-outline-success btn-sm">
                          KES {q.toLocaleString()}
                        </button>
                      ))}
                    </div>
                    <div className="input-group input-group-sm">
                      <span className="input-group-text">KES</span>
                      <input type="number" name="amount" className="form-control" min="10" max="100000" placeholder="Custom amount" />
                      <button type="submit" className="btn btn-success">Go</button>
                    </div>
                  </form>
                </div>
              </details>
            </div>
          </div>
        </div>
        <div className="col-md-4 mb-3">
          <div className="card text-center shadow-sm h-100 border-0">
            <div className="card-body py-4">
              <i className="fas fa-arrow-up fa-3x text-warning mb-3"></i>
              <h5 className="text-warning">Withdraw Funds</h5>
              <details className={`mt-2 text-start ${balance <= 0 ? 'opacity-50' : ''}`}>
                <summary className={`btn btn-warning btn-sm px-4 ${balance <= 0 ? 'disabled' : ''}`} style={{ listStyle: 'none', cursor: 'pointer' }}>
                  <i className="fas fa-minus me-1"></i>Withdraw
                </summary>
                {balance > 0 && (
                  <div className="mt-2 p-3 bg-light rounded shadow-sm">
                    <form action={withdrawFunds}>
                      <p className="small text-muted mb-2">Available: KES {balance.toFixed(2)}</p>
                      <div className="input-group input-group-sm">
                        <span className="input-group-text">KES</span>
                        <input type="number" name="amount" className="form-control" min="100" max={balance} placeholder="Amount" required />
                        <button type="submit" className="btn btn-warning">Confirm</button>
                      </div>
                    </form>
                  </div>
                )}
              </details>
            </div>
          </div>
        </div>
      </div>

      {/* Transaction History */}
      <div className="row">
        <div className="col-12">
          <div className="card shadow-sm border-0">
            <div className="card-header bg-white d-flex justify-content-between align-items-center py-3">
              <h5 className="mb-0 fw-bold"><i className="fas fa-history me-2 text-primary"></i>Transaction History</h5>
              <a href="/marketplace" className="btn btn-info btn-sm">
                <i className="fas fa-chart-line me-1"></i>Start Investing
              </a>
            </div>
            <div className="card-body p-0">
              {transactions && transactions.length > 0 ? (
                <div className="table-responsive">
                  <table className="table table-hover align-middle mb-0">
                    <thead className="table-light">
                      <tr>
                        <th className="ps-4">Date & Time</th>
                        <th>Type</th>
                        <th>Description</th>
                        <th>Amount</th>
                        <th>Balance After</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transactions.map((tx) => (
                        <tr key={tx.id}>
                          <td className="ps-4">
                            <div>{new Date(tx.created_at).toLocaleDateString()}</div>
                            <small className="text-muted">{new Date(tx.created_at).toLocaleTimeString()}</small>
                          </td>
                          <td>
                            {tx.transaction_type === 'credit' ? (
                              <span className="badge bg-success"><i className="fas fa-arrow-down me-1"></i>Credit</span>
                            ) : (
                              <span className="badge bg-danger"><i className="fas fa-arrow-up me-1"></i>Debit</span>
                            )}
                          </td>
                          <td className="text-muted">{tx.description}</td>
                          <td>
                            {tx.transaction_type === 'credit' ? (
                              <span className="text-success fw-bold">+KES {parseFloat(tx.amount).toFixed(2)}</span>
                            ) : (
                              <span className="text-danger fw-bold">-KES {parseFloat(tx.amount).toFixed(2)}</span>
                            )}
                          </td>
                          <td className="fw-bold">KES {parseFloat(tx.balance_after).toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-5">
                  <i className="fas fa-receipt fa-4x text-muted mb-3 opacity-50"></i>
                  <h4 className="text-muted fw-bold">No Transactions Yet</h4>
                  <p className="text-muted">Your wallet transaction history will appear here</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
