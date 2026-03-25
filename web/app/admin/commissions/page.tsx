import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { updateCommissions } from '../actions'

export default async function AdminCommissionsPage({
  searchParams,
}: { searchParams: { message?: string; error?: string } }) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  // Load current settings
  const { data: settings } = await supabase
    .from('system_settings')
    .select('key, value')
    .in('key', ['platform_fee_percent', 'insurance_fee_percent', 'agent_commission_percent'])

  const settingsMap: Record<string, string> = {}
  settings?.forEach((s: any) => { settingsMap[s.key] = s.value })

  const platformFee = parseFloat(settingsMap['platform_fee_percent'] || '1')
  const insuranceFee = parseFloat(settingsMap['insurance_fee_percent'] || '1')
  const agentCommission = parseFloat(settingsMap['agent_commission_percent'] || '5')

  return (
    <div>
      <div className="mb-4">
        <h2 className="fw-bold mb-0"><i className="fas fa-percent me-2 text-dark"></i>Commission & Fee Settings</h2>
        <p className="text-muted mb-0">Configure platform-wide fee and commission percentages</p>
      </div>

      {searchParams.message && (
        <div className="alert alert-success mb-3">
          <i className="fas fa-check-circle me-2"></i>{searchParams.message}
        </div>
      )}
      {searchParams.error && (
        <div className="alert alert-danger mb-3">
          <i className="fas fa-exclamation-triangle me-2"></i>{searchParams.error}
        </div>
      )}

      <div className="row g-4">
        {/* Settings Form */}
        <div className="col-md-6">
          <div className="card border-0 shadow-sm">
            <div className="card-header bg-white py-3">
              <h5 className="mb-0 fw-bold"><i className="fas fa-sliders-h me-2 text-primary"></i>Update Fee Structure</h5>
            </div>
            <div className="card-body p-4">
              <form action={updateCommissions}>
                <div className="mb-3">
                  <label htmlFor="platform_fee" className="form-label fw-bold text-muted">Platform Fee (%)</label>
                  <div className="input-group">
                    <input
                      type="number"
                      id="platform_fee"
                      name="platform_fee"
                      className="form-control"
                      defaultValue={platformFee}
                      min="0"
                      max="20"
                      step="0.1"
                      required
                    />
                    <span className="input-group-text">%</span>
                  </div>
                  <small className="text-muted">Charged on loan principal at disbursement</small>
                </div>

                <div className="mb-3">
                  <label htmlFor="insurance_fee" className="form-label fw-bold text-muted">Insurance Fee (%)</label>
                  <div className="input-group">
                    <input
                      type="number"
                      id="insurance_fee"
                      name="insurance_fee"
                      className="form-control"
                      defaultValue={insuranceFee}
                      min="0"
                      max="10"
                      step="0.1"
                      required
                    />
                    <span className="input-group-text">%</span>
                  </div>
                  <small className="text-muted">Collateral insurance fee on principal</small>
                </div>

                <div className="mb-4">
                  <label htmlFor="agent_commission" className="form-label fw-bold text-muted">Agent Commission (%)</label>
                  <div className="input-group">
                    <input
                      type="number"
                      id="agent_commission"
                      name="agent_commission"
                      className="form-control"
                      defaultValue={agentCommission}
                      min="0"
                      max="30"
                      step="0.5"
                      required
                    />
                    <span className="input-group-text">%</span>
                  </div>
                  <small className="text-muted">Commission agents earn on successful loan referrals</small>
                </div>

                <button type="submit" className="btn btn-primary w-100">
                  <i className="fas fa-save me-2"></i>Save Settings
                </button>
              </form>
            </div>
          </div>
        </div>

        {/* Live Preview */}
        <div className="col-md-6">
          <div className="card border-0 shadow-sm">
            <div className="card-header bg-white py-3">
              <h5 className="mb-0 fw-bold"><i className="fas fa-calculator me-2 text-success"></i>Fee Preview (KES 100,000 Loan)</h5>
            </div>
            <div className="card-body">
              <table className="table table-borderless mb-0">
                <tbody>
                  <tr>
                    <td className="text-muted">Principal Amount</td>
                    <td className="text-end fw-bold">KES 100,000.00</td>
                  </tr>
                  <tr>
                    <td className="text-muted">Platform Fee ({platformFee}%)</td>
                    <td className="text-end">KES {(100000 * platformFee / 100).toLocaleString('en-KE', { minimumFractionDigits: 2 })}</td>
                  </tr>
                  <tr>
                    <td className="text-muted">Insurance Fee ({insuranceFee}%)</td>
                    <td className="text-end">KES {(100000 * insuranceFee / 100).toLocaleString('en-KE', { minimumFractionDigits: 2 })}</td>
                  </tr>
                  <tr>
                    <td className="text-muted">Agent Commission ({agentCommission}%)</td>
                    <td className="text-end">KES {(100000 * agentCommission / 100).toLocaleString('en-KE', { minimumFractionDigits: 2 })}</td>
                  </tr>
                  <tr className="border-top">
                    <td className="fw-bold text-primary pt-3">Total Deductions</td>
                    <td className="text-end fw-bold text-primary pt-3">
                      KES {(100000 * (platformFee + insuranceFee) / 100).toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                </tbody>
              </table>

              <div className="alert alert-info border-0 bg-info bg-opacity-10 mt-3 mb-0">
                <small className="text-dark">
                  <i className="fas fa-info-circle me-2 text-info"></i>
                  Agent commission is paid from platform revenue, not deducted from borrower.
                </small>
              </div>
            </div>
          </div>

          {/* Current values display */}
          <div className="card border-0 shadow-sm mt-3">
            <div className="card-body">
              <h6 className="fw-bold mb-3"><i className="fas fa-database me-2 text-secondary"></i>Current Stored Values</h6>
              <div className="d-flex gap-3">
                <div className="text-center">
                  <div className="fs-4 fw-bold text-primary">{platformFee}%</div>
                  <small className="text-muted">Platform Fee</small>
                </div>
                <div className="text-center">
                  <div className="fs-4 fw-bold text-success">{insuranceFee}%</div>
                  <small className="text-muted">Insurance</small>
                </div>
                <div className="text-center">
                  <div className="fs-4 fw-bold text-warning">{agentCommission}%</div>
                  <small className="text-muted">Agent Commission</small>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
