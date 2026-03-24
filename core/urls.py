from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('borrower/', views.borrower_dashboard, name='borrower_dashboard'),
    path('agent/', views.agent_panel, name='agent_panel'),
    path('marketplace/', views.marketplace, name='marketplace'),
    path('loan/<int:loan_id>/', views.loan_detail, name='loan_detail'),
]