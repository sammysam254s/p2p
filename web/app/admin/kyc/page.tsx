import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { verifyKyc, rejectKyc } from '../actions'

export default async function AdminKycPage({
  searchParams,
}: { searchParams: { message?: string; status?: string } }) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const statusFilter = searchParams.status || 'under_review'

  let query = supabase
    .from('kyc_verifications')
    .select('*, owner:users!kyc_verifications_user_id_fkey(username, email)')
    .order('created_at', { ascending: false })

  if (statusFilter !== 'all') {
    query = query.eq('status', statusFilter)
  }

  const { data: kycList } = await query

  const statusColor: Record<string, string> = {
    pending: 'secondary',
    under_review: 'warning',
    verified: 'success',
    rejected: 'danger',
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="fw-bold mb-0"><i className="fas fa-id-card me-2 text-warning"></i>KYC Review Queue</h2>
          <p className="text-muted mb-0">{kycList?.length ?? 0} records</p>
        </div>
      </div>

      {searchParams.message && (
        <div className="alert alert-success mb-3">
          <i className="fas fa-check-circle me-2"></i>{searchParams.message}
        </div>
      )}

      {/* Tabs */}
      <div className="d-flex gap-2 mb-4">
        {['under_review', 'verified', 'rejected', 'all'].map(s => (
          <a
            key={s}
            href={`/admin/kyc?status=${s}`}
            className={`btn btn-sm ${statusFilter === s ? 'btn-warning text-dark' : 'btn-outline-secondary'}`}
          >
            {s === 'under_review' ? 'Pending Review' : s.charAt(0).toUpperCase() + s.slice(1)}
          </a>
        ))}
      </div>

      <div className="row g-4">
        {kycList?.length === 0 && (
          <div className="col-12">
            <div className="alert alert-info text-center">
              <i className="fas fa-check-circle me-2"></i>No KYC records with status &quot;{statusFilter}&quot;.
            </div>
          </div>
        )}

        {kycList?.map((kyc: any) => (
          <div key={kyc.user_id} className="col-md-6 col-lg-4">
            <div className="card border-0 shadow-sm h-100">
              <div className="card-header d-flex justify-content-between align-items-center py-3">
                <div>
                  <div className="fw-bold">{kyc.owner?.username || 'N/A'}</div>
                  <small className="text-muted">{kyc.owner?.email}</small>
                </div>
                <span className={`badge bg-${statusColor[kyc.status] || 'secondary'}`}>{kyc.status.replace('_', ' ')}</span>
              </div>
              <div className="card-body">
                <table className="table table-sm table-borderless mb-2">
                  <tbody>
                    <tr>
                      <td className="text-muted">Full Name</td>
                      <td className="fw-bold">{kyc.full_name}</td>
                    </tr>
                    <tr>
                      <td className="text-muted">ID Number</td>
                      <td className="fw-bold">{kyc.id_number}</td>
                    </tr>
                    <tr>
                      <td className="text-muted">Date of Birth</td>
                      <td>{kyc.date_of_birth}</td>
                    </tr>
                    <tr>
                      <td className="text-muted">Submitted</td>
                      <td><small>{new Date(kyc.created_at).toLocaleString()}</small></td>
                    </tr>
                    {kyc.verified_at && (
                      <tr>
                        <td className="text-muted">Verified At</td>
                        <td><small>{new Date(kyc.verified_at).toLocaleString()}</small></td>
                      </tr>
                    )}
                  </tbody>
                </table>

                {/* Document previews */}
                {(kyc.id_front_image || kyc.selfie_image) && (
                  <div className="d-flex gap-2 flex-wrap mb-3">
                    {kyc.id_front_image && (
                      <a href={kyc.id_front_image} target="_blank" rel="noopener" className="btn btn-sm btn-outline-primary">
                        <i className="fas fa-id-card me-1"></i>ID Front
                      </a>
                    )}
                    {kyc.id_back_image && (
                      <a href={kyc.id_back_image} target="_blank" rel="noopener" className="btn btn-sm btn-outline-primary">
                        <i className="fas fa-id-card me-1"></i>ID Back
                      </a>
                    )}
                    {kyc.selfie_image && (
                      <a href={kyc.selfie_image} target="_blank" rel="noopener" className="btn btn-sm btn-outline-success">
                        <i className="fas fa-camera me-1"></i>Selfie
                      </a>
                    )}
                    {kyc.signature_image && (
                      <a href={kyc.signature_image} target="_blank" rel="noopener" className="btn btn-sm btn-outline-dark">
                        <i className="fas fa-signature me-1"></i>Signature
                      </a>
                    )}
                  </div>
                )}

                {kyc.status === 'under_review' && (
                  <div className="d-flex gap-2">
                    <form action={verifyKyc} className="flex-grow-1">
                      <input type="hidden" name="kyc_user_id" value={kyc.user_id} />
                      <button type="submit" className="btn btn-success btn-sm w-100">
                        <i className="fas fa-check me-1"></i>Verify
                      </button>
                    </form>
                    <form action={rejectKyc} className="flex-grow-1">
                      <input type="hidden" name="kyc_user_id" value={kyc.user_id} />
                      <button type="submit" className="btn btn-danger btn-sm w-100">
                        <i className="fas fa-times me-1"></i>Reject
                      </button>
                    </form>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
