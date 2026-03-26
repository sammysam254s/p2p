import { login } from '@/app/auth/actions'
import { SubmitButton } from '@/app/components/SubmitButton'

export default function LoginPage({
  searchParams,
}: {
  searchParams: { error: string, message: string }
}) {
  return (
    <div className="row justify-content-center">
      <div className="col-md-6 col-lg-4">
        <div className="card">
          <div className="card-body p-4">
            <div className="text-center mb-4">
              <i className="fas fa-leaf fa-3x text-primary mb-3"></i>
              <h3>Welcome Back</h3>
              <p className="text-muted">Sign in to your account</p>
            </div>

            {searchParams.error && (
              <div className="alert alert-danger">
                <i className="fas fa-exclamation-triangle me-2"></i>
                {searchParams.error}
              </div>
            )}
            
            {searchParams.message && (
              <div className="alert alert-success">
                <i className="fas fa-check-circle me-2"></i>
                {searchParams.message}
              </div>
            )}

            <form action={login}>
              <div className="mb-3">
                <label className="form-label" htmlFor="email">Username or Email</label>
                <div className="input-group">
                  <span className="input-group-text"><i className="fas fa-user"></i></span>
                  <input
                    className="form-control"
                    id="email"
                    name="email"
                    type="text"
                    required
                  />
                </div>
              </div>

              <div className="mb-3">
                <label className="form-label" htmlFor="password">Password</label>
                <div className="input-group">
                  <span className="input-group-text"><i className="fas fa-lock"></i></span>
                  <input
                    className="form-control"
                    id="password"
                    name="password"
                    type="password"
                    required
                  />
                </div>
              </div>

              <SubmitButton className="btn btn-primary w-100 mb-3" loadingText="Signing In...">
                <i className="fas fa-sign-in-alt me-2"></i>Sign In
              </SubmitButton>
            </form>

            <div className="text-center">
              <p className="mb-0">
                Don't have an account?{' '}
                <a href="/register" className="text-primary">Register here</a>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
