import { applyForLoan } from '@/app/borrower/actions'
import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { SubmitButton } from '@/app/components/SubmitButton'

export default async function LoanApplyPage({
  searchParams
}: { searchParams: { error?: string }}) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) redirect('/login')

  const { data: profile } = await supabase
    .from('users')
    .select('kyc_verified')
    .eq('id', user.id)
    .single()

  if (!profile?.kyc_verified) {
    redirect('/borrower?error=Please complete KYC verification before applying')
  }

  return (
    <div className="row justify-content-center">
      <div className="col-md-8 col-lg-6">
        <div className="card shadow-sm border-0 mt-4">
          <div className="card-header bg-primary text-white py-3">
            <h5 className="mb-0"><i className="fas fa-file-invoice-dollar me-2"></i>Apply for Loan</h5>
          </div>
          <div className="card-body p-4">
            {searchParams.error && (
              <div className="alert alert-danger mb-4">
                <i className="fas fa-exclamation-triangle me-2"></i>
                {searchParams.error}
              </div>
            )}

            <form action={applyForLoan}>
              <h6 className="text-primary mb-3">Collateral Information</h6>
              <div className="row mb-3">
                  <div className="col-md-6 mb-3 mb-md-0">
                      <label htmlFor="item_type" className="form-label text-muted fw-bold">Item Type</label>
                      <select name="item_type" id="item_type" className="form-select border-0 shadow-sm" required defaultValue="">
                          <option value="" disabled>Select Item Type</option>
                          <option value="electronics">Electronics (Phones, Laptops)</option>
                          <option value="vehicle">Vehicle (Car, Motorcycle)</option>
                          <option value="appliances">Home Appliances</option>
                          <option value="other">Other Asset</option>
                      </select>
                  </div>
                  <div className="col-md-6">
                      <label htmlFor="brand_model" className="form-label text-muted fw-bold">Brand/Model</label>
                      <input type="text" className="form-control border-0 shadow-sm" id="brand_model" name="brand_model" placeholder="e.g., iPhone 13 Pro" required />
                  </div>
              </div>
              <div className="row mb-4">
                  <div className="col-md-6 mb-3 mb-md-0">
                      <label htmlFor="market_value" className="form-label text-muted fw-bold">Market Value (KES)</label>
                      <input type="number" step="0.01" className="form-control border-0 shadow-sm" id="market_value" name="market_value" placeholder="e.g., 50000" required />
                  </div>
                  <div className="col-md-6 d-flex align-items-end pb-2">
                        <small className="text-muted"><i className="fas fa-info-circle me-1"></i> Max loan is 35% of market value (30/50 rule)</small>
                  </div>
              </div>
              
              <hr className="my-4 text-muted" />

              <h6 className="text-primary mb-3">Loan Information</h6>
              <div className="row mb-4">
                  <div className="col-md-6 mb-3 mb-md-0">
                      <label htmlFor="principal_amount" className="form-label text-muted fw-bold">Loan Amount (KES)</label>
                      <input type="number" step="0.01" className="form-control border-0 shadow-sm text-primary fw-bold" id="principal_amount" name="principal_amount" placeholder="e.g., 15000" required />
                  </div>
                  <div className="col-md-6">
                      <label htmlFor="duration_months" className="form-label text-muted fw-bold">Duration (Months)</label>
                      <select className="form-select border-0 shadow-sm" id="duration_months" name="duration_months" required defaultValue="1">
                          <option value="1">1 Month</option>
                          <option value="2">2 Months</option>
                          <option value="3">3 Months</option>
                          <option value="6">6 Months</option>
                      </select>
                  </div>
              </div>

              <div className="alert alert-info border-0 rounded-3 mb-4">
                  <h6 className="text-info-dark"><i className="fas fa-info-circle me-2"></i>Loan Terms:</h6>
                  <ul className="mb-0 small text-dark mt-2">
                      <li className="mb-1">Interest Rate: 13% per month (flat rate)</li>
                      <li className="mb-1">Platform Fee: 2% of loan amount</li>
                      <li className="mb-1">Insurance Fee: 1% of loan amount</li>
                      <li className="mb-1">Collateral must be physically verified by a station agent</li>
                      <li>Loan will be listed for 7 days for funding</li>
                  </ul>
              </div>

              <div className="d-grid gap-2 d-md-flex justify-content-md-end">
                <a href="/borrower" className="btn btn-light px-4 me-md-2">Cancel</a>
                <SubmitButton className="btn btn-primary px-5 shadow-sm" loadingText="Submitting...">Submit Application</SubmitButton>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
