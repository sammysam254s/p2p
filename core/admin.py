from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Collateral, Loan, Investment, WalletTransaction, Commission, Payment


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'phone_number', 'national_id', 'wallet_balance', 'is_active']
    list_filter = ['role', 'is_active', 'date_joined', 'is_promoted_admin']
    search_fields = ['username', 'email', 'phone_number', 'national_id']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'phone_number', 'national_id', 'wallet_balance', 'total_earnings', 'commission_rate', 'is_promoted_admin')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'phone_number', 'national_id', 'commission_rate')
        }),
    )


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'amount', 'balance_after', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['user__username', 'description']
    readonly_fields = ['created_at']


@admin.register(Collateral)
class CollateralAdmin(admin.ModelAdmin):
    list_display = ['brand_model', 'item_type', 'market_value', 'status', 'user', 'verified_by', 'created_at']
    list_filter = ['status', 'item_type', 'created_at']
    search_fields = ['brand_model', 'item_type', 'user__username']
    readonly_fields = ['created_at']
    
    def get_max_loan_amount(self, obj):
        return f"KES {obj.calculate_max_loan_amount():,.2f}"
    get_max_loan_amount.short_description = 'Max Loan Amount'


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['id', 'borrower', 'principal_amount', 'funded_amount', 'status', 'get_funding_percentage', 'next_payment_date', 'created_at']
    list_filter = ['status', 'duration_months', 'created_at']
    search_fields = ['borrower__username', 'collateral__brand_model']
    readonly_fields = ['created_at', 'get_funding_percentage', 'calculate_total_repayment']
    
    def get_funding_percentage(self, obj):
        return f"{obj.get_funding_percentage():.1f}%"
    get_funding_percentage.short_description = 'Funding %'
    
    def calculate_total_repayment(self, obj):
        return f"KES {obj.calculate_total_repayment():,.2f}"
    calculate_total_repayment.short_description = 'Total Repayment'


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ['lender', 'loan', 'amount_invested', 'monthly_return', 'total_returns_paid', 'date']
    list_filter = ['date']
    search_fields = ['lender__username', 'loan__id']
    readonly_fields = ['date']


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ['agent', 'loan', 'amount', 'commission_rate', 'is_paid', 'paid_at', 'created_at']
    list_filter = ['is_paid', 'created_at']
    search_fields = ['agent__username', 'loan__id']
    readonly_fields = ['created_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['loan', 'amount', 'payment_type', 'payment_date', 'next_payment_date', 'processed_by']
    list_filter = ['payment_type', 'payment_date']
    search_fields = ['loan__id', 'loan__borrower__username']
    readonly_fields = ['payment_date']