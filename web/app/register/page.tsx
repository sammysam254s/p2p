import { signup } from '@/app/auth/actions'
import { SubmitButton } from '@/app/components/SubmitButton'

export default function RegisterPage({
  searchParams,
}: {
  searchParams: { error: string }
}) {
  return (
    <div className="row justify-content-center">
      <div className="col-md-8 col-lg-6">
        <div className="card">
          <div className="card-body p-4">
            <div className="text-center mb-4">
              <i className="fas fa-user-plus fa-3x text-primary mb-3"></i>
              <h3>Create Account</h3>
              <p className="text-muted">Join P2P Secure-Lend Kenya</p>
            </div>

            {searchParams.error && (
              <div className="alert alert-danger">
                <i className="fas fa-exclamation-triangle me-2"></i>
                {searchParams.error}
              </div>
            )}

            <form action={signup}>
              <div className="row">
                <div className="col-md-6 mb-3">
                  <label className="form-label" htmlFor="username">Username</label>
                  <div className="input-group">
                    <span className="input-group-text"><i className="fas fa-user"></i></span>
                    <input className="form-control" id="username" name="username" type="text" required />
                  </div>
                </div>

                <div className="col-md-6 mb-3">
                  <label className="form-label" htmlFor="email">Email</label>
                  <div className="input-group">
                    <span className="input-group-text"><i className="fas fa-envelope"></i></span>
                    <input className="form-control" id="email" name="email" type="email" required />
                  </div>
                </div>
              </div>

              <div className="mb-3">
                <label className="form-label" htmlFor="role">I want to:</label>
                <select id="role" name="role" className="form-control" required defaultValue="">
                  <option value="" disabled>Select your role</option>
                  <option value="borrower">Borrow Money (Provide Collateral)</option>
                  <option value="lender">Lend Money (Invest in Loans)</option>
                  <option value="agent">Work as Station Agent</option>
                </select>
              </div>

              <div className="row">
                <div className="col-md-6 mb-3">
                  <label className="form-label" htmlFor="phone_number">Phone Number</label>
                  <div className="input-group">
                    <span className="input-group-text"><i className="fas fa-phone"></i></span>
                    <input className="form-control" id="phone_number" name="phone_number" type="text" required />
                  </div>
                  <div className="form-text">M-Pesa number (e.g., 254712345678)</div>
                </div>

                <div className="col-md-6 mb-3">
                  <label className="form-label" htmlFor="national_id">National ID</label>
                  <div className="input-group">
                    <span className="input-group-text"><i className="fas fa-id-card"></i></span>
                    <input className="form-control" id="national_id" name="national_id" type="text" required />
                  </div>
                </div>
              </div>

              <div className="row">
                <div className="col-md-6 mb-3">
                  <label className="form-label" htmlFor="password">Password</label>
                  <div className="input-group">
                    <span className="input-group-text"><i className="fas fa-lock"></i></span>
                    <input className="form-control" id="password" name="password" type="password" required />
                  </div>
                </div>

                <div className="col-md-6 mb-3">
                  <label className="form-label" htmlFor="passwordConfirm">Confirm Password</label>
                  <div className="input-group">
                    <span className="input-group-text"><i className="fas fa-lock"></i></span>
                    <input className="form-control" id="passwordConfirm" name="passwordConfirm" type="password" required />
                  </div>
                </div>
              </div>

              <SubmitButton className="btn btn-primary w-100 mb-3" loadingText="Creating Account...">
                <i className="fas fa-user-plus me-2"></i>Create Account
              </SubmitButton>
            </form>

            <div className="text-center">
              <p className="mb-0">
                Already have an account?{' '}
                <a href="/login" className="text-primary">Sign in here</a>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
