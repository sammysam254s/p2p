from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Collateral, Loan, Investment


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'phone_number', 'national_id', 'is_active']
    list_filter = ['role', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'phone_number', 'national_id']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'phone_number', 'national_id')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'phone_number', 'national_id')
        }),
    )


@admin.register(Collateral)
class CollateralAdmin(admin.ModelAdmin):
    list_display = ['brand_model', 'item_type', 'market_value', 'status', 'user', 'created_at']
    list_filter = ['status', 'item_type', 'created_at']
    search_fields = ['brand_model', 'item_type', 'user__username']
    readonly_fields = ['created_at']
    
    def get_max_loan_amount(self, obj):
        return f"KES {obj.calculate_max_loan_amount():,.2f}"
    get_max_loan_amount.short_description = 'Max Loan Amount'


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['id', 'borrower', 'principal_amount', 'funded_amount', 'status', 'get_funding_percentage', 'created_at']
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
    list_display = ['lender', 'loan', 'amount_invested', 'date']
    list_filter = ['date']
    search_fields = ['lender__username', 'loan__id']
    readonly_fields = ['date']