from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Collateral, Loan, Investment, WalletTransaction, Commission, Payment

# Customize the admin site header
admin.site.site_header = "P2P Secure-Lend Administration"
admin.site.site_title = "P2P Admin"
admin.site.index_title = "Welcome to P2P Secure-Lend Administration"

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Enhanced Custom User Admin with all functionality"""
    list_display = ['username', 'email', 'role', 'phone_number', 'national_id', 'wallet_balance', 'total_earnings', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'date_joined', 'is_promoted_admin', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'phone_number', 'national_id', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    fieldsets = UserAdmin.fieldsets + (
        ('P2P Platform Info', {
            'fields': ('role', 'phone_number', 'national_id', 'wallet_balance', 'total_earnings', 'commission_rate', 'is_promoted_admin')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('P2P Platform Info', {
            'fields': ('role', 'phone_number', 'national_id', 'commission_rate')
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login', 'total_earnings']
    
    actions = ['promote_to_admin', 'add_wallet_funds_1000', 'add_wallet_funds_5000', 'reset_wallet', 'activate_users', 'deactivate_users']
    
    def promote_to_admin(self, request, queryset):
        """Promote selected users to admin"""
        updated = queryset.update(role='admin', is_staff=True, is_superuser=True, is_promoted_admin=True)
        self.message_user(request, f'{updated} users promoted to admin.')
    promote_to_admin.short_description = "Promote selected users to admin"
    
    def add_wallet_funds_1000(self, request, queryset):
        """Add KES 1000 to selected users' wallets"""
        for user in queryset:
            user.add_to_wallet(1000, "Admin credit - KES 1000")
        self.message_user(request, f'Added KES 1000 to {queryset.count()} users.')
    add_wallet_funds_1000.short_description = "Add KES 1000 to wallet"
    
    def add_wallet_funds_5000(self, request, queryset):
        """Add KES 5000 to selected users' wallets"""
        for user in queryset:
            user.add_to_wallet(5000, "Admin credit - KES 5000")
        self.message_user(request, f'Added KES 5000 to {queryset.count()} users.')
    add_wallet_funds_5000.short_description = "Add KES 5000 to wallet"
    
    def reset_wallet(self, request, queryset):
        """Reset wallet balance to zero"""
        updated = queryset.update(wallet_balance=0)
        self.message_user(request, f'{updated} wallets reset to zero.')
    reset_wallet.short_description = "Reset wallet balance"
    
    def activate_users(self, request, queryset):
        """Activate selected users"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} users activated.')
    activate_users.short_description = "Activate selected users"
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} users deactivated.')
    deactivate_users.short_description = "Deactivate selected users"


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    """Enhanced Wallet Transaction Admin"""
    list_display = ['user', 'transaction_type', 'amount', 'description', 'balance_after', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['user__username', 'user__email', 'description']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        """Prevent manual addition of transactions"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing of transactions"""
        return False


@admin.register(Collateral)
class CollateralAdmin(admin.ModelAdmin):
    """Enhanced Collateral Admin"""
    list_display = ['brand_model', 'item_type', 'market_value', 'status', 'user', 'verified_by', 'get_max_loan_amount', 'created_at']
    list_filter = ['status', 'item_type', 'created_at', 'verification_date']
    search_fields = ['brand_model', 'item_type', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'get_max_loan_amount']
    ordering = ['-created_at']
    
    actions = ['verify_collateral', 'release_collateral', 'mark_pending']
    
    def get_max_loan_amount(self, obj):
        return f"KES {obj.calculate_max_loan_amount():,.2f}"
    get_max_loan_amount.short_description = 'Max Loan Amount'
    
    def verify_collateral(self, request, queryset):
        """Verify selected collateral"""
        from django.utils import timezone
        updated = queryset.update(status='verified', verification_date=timezone.now())
        self.message_user(request, f'{updated} collateral items verified.')
    verify_collateral.short_description = "Verify selected collateral"
    
    def release_collateral(self, request, queryset):
        """Release selected collateral"""
        updated = queryset.update(status='released')
        self.message_user(request, f'{updated} collateral items released.')
    release_collateral.short_description = "Release selected collateral"
    
    def mark_pending(self, request, queryset):
        """Mark selected collateral as pending"""
        updated = queryset.update(status='pending', verification_date=None)
        self.message_user(request, f'{updated} collateral items marked as pending.')
    mark_pending.short_description = "Mark as pending"


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    """Enhanced Loan Admin"""
    list_display = ['id', 'borrower', 'principal_amount', 'funded_amount', 'status', 'get_funding_percentage', 'interest_rate', 'duration_months', 'created_at']
    list_filter = ['status', 'duration_months', 'interest_rate', 'created_at']
    search_fields = ['borrower__username', 'borrower__email', 'collateral__brand_model', 'id']
    readonly_fields = ['created_at', 'updated_at', 'get_funding_percentage', 'calculate_total_repayment', 'calculate_platform_fee', 'calculate_insurance_fee']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Loan Details', {
            'fields': ('borrower', 'collateral', 'principal_amount', 'interest_rate', 'duration_months')
        }),
        ('Funding Information', {
            'fields': ('funded_amount', 'status', 'get_funding_percentage')
        }),
        ('Calculations', {
            'fields': ('calculate_platform_fee', 'calculate_insurance_fee', 'calculate_total_repayment'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_loans', 'list_loans', 'cancel_loans', 'mark_as_paid']
    
    def get_funding_percentage(self, obj):
        return f"{obj.get_funding_percentage():.1f}%"
    get_funding_percentage.short_description = 'Funding %'
    
    def calculate_total_repayment(self, obj):
        return f"KES {obj.calculate_total_repayment():,.2f}"
    calculate_total_repayment.short_description = 'Total Repayment'
    
    def calculate_platform_fee(self, obj):
        return f"KES {obj.calculate_platform_fee():,.2f}"
    calculate_platform_fee.short_description = 'Platform Fee'
    
    def calculate_insurance_fee(self, obj):
        return f"KES {obj.calculate_insurance_fee():,.2f}"
    calculate_insurance_fee.short_description = 'Insurance Fee'
    
    def activate_loans(self, request, queryset):
        """Activate selected loans"""
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} loans activated.')
    activate_loans.short_description = "Activate selected loans"
    
    def list_loans(self, request, queryset):
        """List selected loans"""
        updated = queryset.update(status='listed')
        self.message_user(request, f'{updated} loans listed.')
    list_loans.short_description = "List selected loans"
    
    def cancel_loans(self, request, queryset):
        """Cancel selected loans"""
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} loans cancelled.')
    cancel_loans.short_description = "Cancel selected loans"
    
    def mark_as_paid(self, request, queryset):
        """Mark selected loans as paid"""
        updated = queryset.update(status='paid')
        self.message_user(request, f'{updated} loans marked as paid.')
    mark_as_paid.short_description = "Mark as paid"


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    """Enhanced Investment Admin"""
    list_display = ['lender', 'loan', 'amount_invested', 'get_monthly_return', 'date']
    list_filter = ['date', 'loan__status']
    search_fields = ['lender__username', 'lender__email', 'loan__id', 'loan__borrower__username']
    readonly_fields = ['date', 'get_monthly_return']
    ordering = ['-date']
    
    def get_monthly_return(self, obj):
        return f"KES {obj.calculate_monthly_return():,.2f}"
    get_monthly_return.short_description = 'Monthly Return'
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing of investments"""
        return False


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    """Enhanced Commission Admin"""
    list_display = ['agent', 'loan', 'amount', 'status', 'created_at', 'paid_at']
    list_filter = ['status', 'created_at', 'paid_at']
    search_fields = ['agent__username', 'agent__email', 'loan__id', 'loan__borrower__username']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    actions = ['mark_as_paid', 'mark_as_pending']
    
    def mark_as_paid(self, request, queryset):
        """Mark selected commissions as paid"""
        from django.utils import timezone
        updated = queryset.update(status='paid', paid_at=timezone.now())
        self.message_user(request, f'{updated} commissions marked as paid.')
    mark_as_paid.short_description = "Mark as paid"
    
    def mark_as_pending(self, request, queryset):
        """Mark selected commissions as pending"""
        updated = queryset.update(status='pending', paid_at=None)
        self.message_user(request, f'{updated} commissions marked as pending.')
    mark_as_pending.short_description = "Mark as pending"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Enhanced Payment Admin"""
    list_display = ['loan', 'borrower', 'amount', 'payment_type', 'status', 'mpesa_transaction_id', 'created_at', 'completed_at']
    list_filter = ['payment_type', 'status', 'created_at']
    search_fields = ['loan__id', 'borrower__username', 'borrower__email', 'mpesa_transaction_id']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    actions = ['mark_as_completed', 'mark_as_failed', 'mark_as_pending']
    
    def mark_as_completed(self, request, queryset):
        """Mark selected payments as completed"""
        from django.utils import timezone
        updated = queryset.update(status='completed', completed_at=timezone.now())
        self.message_user(request, f'{updated} payments marked as completed.')
    mark_as_completed.short_description = "Mark as completed"
    
    def mark_as_failed(self, request, queryset):
        """Mark selected payments as failed"""
        updated = queryset.update(status='failed')
        self.message_user(request, f'{updated} payments marked as failed.')
    mark_as_failed.short_description = "Mark as failed"
    
    def mark_as_pending(self, request, queryset):
        """Mark selected payments as pending"""
        updated = queryset.update(status='pending', completed_at=None)
        self.message_user(request, f'{updated} payments marked as pending.')
    mark_as_pending.short_description = "Mark as pending"