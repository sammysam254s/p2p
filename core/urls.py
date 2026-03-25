from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    # Borrower-specific URLs
    path('borrower/', views.borrower_dashboard, name='borrower_dashboard'),
    path('borrower/loans/', views.borrower_loans, name='borrower_loans'),
    path('borrower/collaterals/', views.borrower_collaterals, name='borrower_collaterals'),
    path('borrower/documents/', views.borrower_documents, name='borrower_documents'),
    path('agent/', views.agent_panel, name='agent_panel'),
    path('marketplace/', views.marketplace, name='marketplace'),
    path('loan/<str:loan_id>/', views.loan_detail, name='loan_detail'),
    
    # KYC URLs
    path('kyc/', views.kyc_verification, name='kyc_verification'),
    
    # Loan management URLs
    path('loan/<str:loan_id>/pay/', views.loan_payment, name='loan_payment'),
    path('loan/<str:loan_id>/contract/', views.download_contract, name='download_contract'),
    
    # Contract verification URLs
    path('verify-contract/<str:contract_id>/', views.verify_contract, name='verify_contract'),
    
    # Wallet URLs
    path('wallet/deposit/', views.wallet_deposit, name='wallet_deposit'),
    path('wallet/withdraw/', views.wallet_withdraw, name='wallet_withdraw'),
    path('wallet/transactions/', views.wallet_transactions, name='wallet_transactions'),
    
    # Agent URLs
    path('verify-collateral/<str:collateral_id>/', views.verify_collateral, name='verify_collateral'),
    
    # API endpoints
    path('api/check-username/', views.check_username_api, name='check_username_api'),
    
    # Admin URLs
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/borrowers/', views.admin_borrower_view, name='admin_borrower_view'),
    path('admin/lenders/', views.admin_lender_view, name='admin_lender_view'),
    path('admin/agents/', views.admin_agent_view, name='admin_agent_view'),
    path('admin/users/', views.admin_users_management, name='admin_users_management'),
    path('admin/commissions/', views.admin_commissions_payouts, name='admin_commissions_payouts'),
    path('admin/payments/', views.admin_payments_management, name='admin_payments_management'),
    path('admin/wallets/', views.admin_wallet_management, name='admin_wallet_management'),
    path('admin/contracts/', views.admin_contracts_management, name='admin_contracts_management'),
]