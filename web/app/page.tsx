export default function Home() {
  return (
    <>
      <div className="hero-section text-center py-5 mb-4 text-white rounded" style={{ background: 'linear-gradient(135deg, var(--primary-green), var(--secondary-green))' }}>
          <div className="container">
              <h1 className="display-4 mb-4 fw-bold">
                  <i className="fas fa-leaf me-3"></i>P2P Secure-Lend Kenya
              </h1>
              <p className="lead mb-4">
                  Bridging digital lending with physical security. Get loans backed by collateral or invest in secured opportunities.
              </p>
              <div className="row justify-content-center">
                  <div className="col-md-8">
                      <div className="row">
                          <div className="col-md-4 mb-3">
                              <a href="/register" className="btn btn-light btn-lg w-100 fw-bold text-primary">
                                  <i className="fas fa-user-plus me-2"></i>Get Started
                              </a>
                          </div>
                          <div className="col-md-4 mb-3">
                              <a href="/login" className="btn btn-outline-light btn-lg w-100">
                                  <i className="fas fa-sign-in-alt me-2"></i>Sign In
                              </a>
                          </div>
                          <div className="col-md-4 mb-3">
                              <a href="#how-it-works" className="btn btn-outline-light btn-lg w-100">
                                  <i className="fas fa-info-circle me-2"></i>Learn More
                              </a>
                          </div>
                      </div>
                  </div>
              </div>
          </div>
      </div>

      <div className="container mb-5">
          <div className="row text-center mb-5">
              <div className="col-12">
                  <h2 className="text-primary mb-4 fw-bold">Why Choose P2P Secure-Lend?</h2>
              </div>
          </div>
          
          <div className="row">
              <div className="col-md-4 mb-4">
                  <div className="card h-100 text-center">
                      <div className="card-body">
                          <i className="fas fa-shield-alt fa-3x text-primary mb-3"></i>
                          <h5 className="card-title fw-bold">100% Secured</h5>
                          <p className="card-text text-muted">All loans are backed by physical collateral worth at least 200% of the loan amount, ensuring maximum security for lenders.</p>
                      </div>
                  </div>
              </div>
              
              <div className="col-md-4 mb-4">
                  <div className="card h-100 text-center">
                      <div className="card-body">
                          <i className="fas fa-percentage fa-3x text-primary mb-3"></i>
                          <h5 className="card-title fw-bold">High Returns</h5>
                          <p className="card-text text-muted">Earn 13% monthly interest on your investments. Our transparent fee structure ensures you know exactly what you'll earn.</p>
                      </div>
                  </div>
              </div>
              
              <div className="col-md-4 mb-4">
                  <div className="card h-100 text-center">
                      <div className="card-body">
                          <i className="fas fa-clock fa-3x text-primary mb-3"></i>
                          <h5 className="card-title fw-bold">Quick Process</h5>
                          <p className="card-text text-muted">Get your loan approved in minutes. Our streamlined verification process through station agents ensures fast turnaround.</p>
                      </div>
                  </div>
              </div>
          </div>
      </div>

      <div id="how-it-works" className="bg-white rounded shadow-sm py-5 mb-5 border">
          <div className="container">
              <div className="row text-center mb-5">
                  <div className="col-12">
                      <h2 className="text-primary mb-4 fw-bold">How It Works</h2>
                  </div>
              </div>
              
              <div className="row">
                  <div className="col-md-6 mb-4">
                      <div className="card h-100 border-0 shadow-sm">
                          <div className="card-header bg-primary text-white py-3">
                              <h5 className="mb-0 fw-bold"><i className="fas fa-hand-holding-usd me-2"></i>For Borrowers</h5>
                          </div>
                          <div className="card-body p-0">
                              <ol className="list-group list-group-flush border-0">
                                  <li className="list-group-item d-flex align-items-center py-3 border-bottom">
                                      <span className="badge bg-primary rounded-pill me-3 px-3 py-2">1</span>
                                      Submit your collateral details and loan application
                                  </li>
                                  <li className="list-group-item d-flex align-items-center py-3 border-bottom">
                                      <span className="badge bg-primary rounded-pill me-3 px-3 py-2">2</span>
                                      Visit a station agent to verify your collateral
                                  </li>
                                  <li className="list-group-item d-flex align-items-center py-3 border-bottom">
                                      <span className="badge bg-primary rounded-pill me-3 px-3 py-2">3</span>
                                      Your loan gets listed on the marketplace
                                  </li>
                                  <li className="list-group-item d-flex align-items-center py-3">
                                      <span className="badge bg-primary rounded-pill me-3 px-3 py-2">4</span>
                                      Receive funds once fully funded (within 7 days)
                                  </li>
                              </ol>
                          </div>
                      </div>
                  </div>
                  
                  <div className="col-md-6 mb-4">
                      <div className="card h-100 border-0 shadow-sm">
                          <div className="card-header bg-success text-white py-3">
                              <h5 className="mb-0 fw-bold"><i className="fas fa-chart-line me-2"></i>For Lenders</h5>
                          </div>
                          <div className="card-body p-0">
                              <ol className="list-group list-group-flush border-0">
                                  <li className="list-group-item d-flex align-items-center py-3 border-bottom">
                                      <span className="badge bg-success rounded-pill me-3 px-3 py-2">1</span>
                                      Browse verified loan opportunities on the marketplace
                                  </li>
                                  <li className="list-group-item d-flex align-items-center py-3 border-bottom">
                                      <span className="badge bg-success rounded-pill me-3 px-3 py-2">2</span>
                                      Review collateral details and loan terms
                                  </li>
                                  <li className="list-group-item d-flex align-items-center py-3 border-bottom">
                                      <span className="badge bg-success rounded-pill me-3 px-3 py-2">3</span>
                                      Invest any amount from KES 100 upwards
                                  </li>
                                  <li className="list-group-item d-flex align-items-center py-3">
                                      <span className="badge bg-success rounded-pill me-3 px-3 py-2">4</span>
                                      Earn 13% monthly returns on your investment
                                  </li>
                              </ol>
                          </div>
                      </div>
                  </div>
              </div>
          </div>
      </div>
    </>
  )
}
