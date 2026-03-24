from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('borrower/', views.borrower_dashboard, name='borrower_dashboard'),
    path('agent/', views.agent_panel, name='agent_panel'),
    path('marketplace/', views.marketplace, name='marketplace'),
    path('loan/<int:loan_id>/', views.loan_detail, name='loan_detail'),
    
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
]