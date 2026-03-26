import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { submitKyc } from './actions'
import { SubmitButton } from '@/app/components/SubmitButton'

export default async function KycPage({
  searchParams
}: { searchParams: { error?: string } }) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const { data: kyc } = await supabase
    .from('kyc_verifications')
    .select('*')
    .eq('user_id', user.id)
    .single()

  const kycStatus = kyc?.status || 'pending'
  const canSubmit = kycStatus !== 'verified' && kycStatus !== 'under_review'

  return (
    <>
      <div className="row mb-3">
        <div className="col-12">
          <h2><i className="fas fa-id-card me-2 text-primary"></i>KYC Verification</h2>
          <p className="text-muted">Complete your identity verification to access all platform features</p>
        </div>
      </div>

      {searchParams.error && (
        <div className="alert alert-danger mb-4">
          <i className="fas fa-exclamation-triangle me-2"></i>{searchParams.error}
        </div>
      )}

      {/* KYC Status Card */}
      <div className="row mb-4">
        <div className="col-12">
          <div className="card shadow-sm border-0">
            <div className="card-body">
              <h5 className="fw-bold"><i className="fas fa-info-circle me-2 text-info"></i>Verification Status</h5>

              {kycStatus === 'verified' && (
                <div className="alert alert-success">
                  <i className="fas fa-check-circle me-2"></i>
                  <strong>✅ Verified Successfully!</strong> Your identity has been verified and you can now apply for loans.
                  {kyc?.verified_at && (
                    <small className="d-block mt-1">Verified on: {new Date(kyc.verified_at).toLocaleString()}</small>
                  )}
                </div>
              )}
              {kycStatus === 'under_review' && (
                <div className="alert alert-info">
                  <i className="fas fa-clock me-2"></i>
                  <strong>⏳ Processing Your Verification</strong> Your documents are being processed automatically.
                  <small className="d-block mt-1">Expected completion: Within 1-2 minutes. Refresh this page to see updates.</small>
                </div>
              )}
              {kycStatus === 'rejected' && (
                <div className="alert alert-danger">
                  <i className="fas fa-times-circle me-2"></i>
                  <strong>❌ Verification Failed</strong> Please review the requirements and resubmit your documents.
                </div>
              )}
              {kycStatus === 'pending' && (
                <div className="alert alert-warning">
                  <i className="fas fa-exclamation-triangle me-2"></i>
                  <strong>⚠️ Verification Required</strong> Complete identity verification to unlock loan applications and all borrower features.
                  <small className="d-block mt-1">This is a mandatory security requirement for all borrowers.</small>
                </div>
              )}

              <div className="mt-3">
                <h6><i className="fas fa-lightbulb me-2 text-warning"></i>Verification Tips:</h6>
                <ul className="mb-0 small text-muted">
                  <li>Ensure your ID is valid and not expired</li>
                  <li>All information must match exactly as on your national ID</li>
                  <li>Upload clear, well-lit photos of your documents</li>
                  <li>Verification is processed automatically within minutes</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* KYC Form */}
      {canSubmit && (
        <div className="row">
          <div className="col-md-8 mx-auto">
            <div className="card shadow-sm border-0">
              <div className="card-header bg-white py-3">
                <h5 className="mb-0 fw-bold"><i className="fas fa-upload me-2 text-primary"></i>Submit Verification Documents</h5>
              </div>
              <div className="card-body p-4">
                <form action={submitKyc} encType="multipart/form-data">

                  <h6 className="text-primary mb-3">Personal Information</h6>
                  <div className="row mb-3">
                    <div className="col-md-6 mb-3">
                      <label htmlFor="full_name" className="form-label fw-bold text-muted">Full Name</label>
                      <input type="text" className="form-control border-0 shadow-sm" id="full_name" name="full_name" placeholder="As it appears on ID" required />
                    </div>
                    <div className="col-md-6 mb-3">
                      <label htmlFor="id_number" className="form-label fw-bold text-muted">National ID Number</label>
                      <input type="text" className="form-control border-0 shadow-sm" id="id_number" name="id_number" placeholder="e.g. 12345678" required />
                    </div>
                  </div>
                  <div className="row mb-4">
                    <div className="col-md-6">
                      <label htmlFor="date_of_birth" className="form-label fw-bold text-muted">Date of Birth</label>
                      <input type="date" className="form-control border-0 shadow-sm" id="date_of_birth" name="date_of_birth" required />
                    </div>
                  </div>

                  <h6 className="text-primary mb-3">Document Images</h6>
                  <div className="row mb-3">
                    <div className="col-md-6 mb-3">
                      <label className="form-label fw-bold text-muted">ID Front Image</label>
                      <input type="file" className="form-control border-0 shadow-sm" name="id_front_image" accept="image/*" required />
                      <small className="text-muted">Clear photo of ID front side (max 5MB)</small>
                    </div>
                    <div className="col-md-6 mb-3">
                      <label className="form-label fw-bold text-muted">ID Back Image</label>
                      <input type="file" className="form-control border-0 shadow-sm" name="id_back_image" accept="image/*" required />
                      <small className="text-muted">Clear photo of ID back side (max 5MB)</small>
                    </div>
                    <div className="col-md-6 mb-3">
                      <label className="form-label fw-bold text-muted">Selfie Photo</label>
                      <input type="file" className="form-control border-0 shadow-sm" name="selfie_image" accept="image/*" required />
                      <small className="text-muted">Clear selfie showing your face (max 5MB)</small>
                    </div>
                    <div className="col-md-6 mb-3">
                      <label className="form-label fw-bold text-muted">Signature Image</label>
                      <input type="file" className="form-control border-0 shadow-sm" name="signature_image" accept="image/*" required />
                      <small className="text-muted">Sign on white paper, photograph it (max 5MB)</small>
                    </div>
                  </div>

                  <div className="alert alert-info border-0 bg-info bg-opacity-10 mb-4">
                    <h6 className="text-info-dark fw-bold"><i className="fas fa-info-circle me-2"></i>Photo Guidelines:</h6>
                    <ul className="mb-0 small text-dark">
                      <li>All images must be clear, well-lit and in JPG/PNG format</li>
                      <li>ID photos should show all text visibly</li>
                      <li>Selfie should show your face without sunglasses</li>
                      <li>All 4 images are mandatory — maximum 5MB each</li>
                    </ul>
                  </div>

                  <div className="d-grid">
                    <SubmitButton className="btn btn-primary btn-lg shadow-sm fw-bold" loadingText="Submitting...">
                      <i className="fas fa-check me-2"></i>Submit for Verification
                    </SubmitButton>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
