from django.contrib.auth.models import AbstractUser
from django.db import models
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
import uuid


class KYCVerification(models.Model):
    """KYC verification model for user identity verification"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.OneToOneField('CustomUser', on_delete=models.CASCADE, related_name='kyc')
    
    # Personal Information
    full_name = models.CharField(max_length=200)
    id_number = models.CharField(max_length=20)
    date_of_birth = models.DateField()
    
    # Document Images
    id_front_image = models.ImageField(upload_to='kyc/id_front/', null=True, blank=True)
    id_back_image = models.ImageField(upload_to='kyc/id_back/', null=True, blank=True)
    selfie_image = models.ImageField(upload_to='kyc/selfies/', null=True, blank=True)
    signature_image = models.ImageField(upload_to='kyc/signatures/', null=True, blank=True)
    
    # Verification Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    verification_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    ai_verification_result = models.JSONField(default=dict, blank=True)
    
    # Verification Details
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_kycs')
    rejection_reason = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"KYC for {self.user.username} - {self.status}"
    
    def is_verified(self):
        return self.status == 'verified'
    
    def can_borrow(self):
        """Check if user can borrow based on KYC status"""
        return self.status == 'verified'


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('borrower', 'Borrower'),
        ('lender', 'Lender'),
        ('agent', 'Station Agent'),
        ('admin', 'Administrator'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=15, help_text="M-Pesa phone number")
    national_id = models.CharField(max_length=20, unique=True)
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.50, help_text="Commission percentage for agents")
    is_promoted_admin = models.BooleanField(default=False, help_text="Promoted to admin by another admin")
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def get_wallet_balance(self):
        return self.wallet_balance
    
    def has_verified_kyc(self):
        """Check if user has verified KYC"""
        try:
            return self.kyc.is_verified()
        except KYCVerification.DoesNotExist:
            return False
    
    def can_borrow(self):
        """Check if user can create loan applications"""
        return self.role == 'borrower' and self.has_verified_kyc()
    
    def add_to_wallet(self, amount, description=""):
        """Add money to user's wallet"""
        self.wallet_balance += Decimal(str(amount))
        self.total_earnings += Decimal(str(amount))
        self.save()
        
        # Create wallet transaction record
        WalletTransaction.objects.create(
            user=self,
            transaction_type='credit',
            amount=amount,
            description=description,
            balance_after=self.wallet_balance
        )
    
    def deduct_from_wallet(self, amount, description=""):
        """Deduct money from user's wallet"""
        if self.wallet_balance >= Decimal(str(amount)):
            self.wallet_balance -= Decimal(str(amount))
            self.save()
            
            WalletTransaction.objects.create(
                user=self,
                transaction_type='debit',
                amount=amount,
                description=description,
                balance_after=self.wallet_balance
            )
            return True
        return False


class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - KES {self.amount}"
    
    class Meta:
        ordering = ['-created_at']


class Collateral(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('released', 'Released'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    item_type = models.CharField(max_length=100, help_text="e.g., Smartphone, Laptop, Jewelry")
    brand_model = models.CharField(max_length=200, help_text="e.g., iPhone 14 Pro, MacBook Air M2")
    market_value = models.DecimalField(max_digits=10, decimal_places=2)
    agent_verified_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Value verified by agent")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    verification_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_collaterals')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.brand_model} - KES {self.get_current_value()}"
    
    def get_current_value(self):
        """Get the current market value (agent verified or original)"""
        return self.agent_verified_value if self.agent_verified_value else self.market_value
    
    def calculate_max_loan_amount(self):
        """Implements the 30/50 rule: 30% devaluation, then 50% of devalued amount"""
        current_value = self.get_current_value()
        devalued_amount = current_value * Decimal('0.70')
        max_loan_amount = devalued_amount * Decimal('0.50')
        return max_loan_amount


class Loan(models.Model):
    STATUS_CHOICES = [
        ('pending_collateral', 'Pending Collateral'),
        ('listed', 'Listed'),
        ('active', 'Active'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
        ('defaulted', 'Defaulted'),
    ]
    
    borrower = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    collateral = models.OneToOneField(Collateral, on_delete=models.CASCADE)
    principal_amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=13.00)
    duration_months = models.IntegerField()
    funded_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_collateral')
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    next_payment_date = models.DateTimeField(null=True, blank=True)
    payments_made = models.IntegerField(default=0)
    contract_pdf = models.FileField(upload_to='contracts/', null=True, blank=True)
    
    def __str__(self):
        return f"Loan #{self.id} - KES {self.principal_amount}"
    
    def calculate_platform_fee(self):
        """2% of principal amount"""
        return self.principal_amount * Decimal('0.02')
    
    def calculate_insurance_fee(self):
        """1% of principal amount"""
        return self.principal_amount * Decimal('0.01')
    
    def calculate_monthly_interest(self):
        """13% flat interest per month"""
        return self.principal_amount * (self.interest_rate / 100)
    
    def calculate_monthly_payment(self):
        """Calculate monthly payment amount"""
        monthly_interest = self.calculate_monthly_interest()
        platform_fee = self.calculate_platform_fee() / self.duration_months
        insurance_fee = self.calculate_insurance_fee() / self.duration_months
        principal_payment = self.principal_amount / self.duration_months
        return principal_payment + monthly_interest + platform_fee + insurance_fee
    
    def calculate_total_repayment(self):
        """Principal + (Monthly Interest * Duration) + Platform Fee + Insurance Fee"""
        monthly_interest = self.calculate_monthly_interest()
        total_interest = monthly_interest * self.duration_months
        platform_fee = self.calculate_platform_fee()
        insurance_fee = self.calculate_insurance_fee()
        return self.principal_amount + total_interest + platform_fee + insurance_fee
    
    def get_funding_percentage(self):
        """Calculate funding percentage"""
        if self.principal_amount > 0:
            return (self.funded_amount / self.principal_amount) * 100
        return 0
    
    def is_fully_funded(self):
        """Check if loan is 100% funded"""
        return self.funded_amount >= self.principal_amount
    
    def is_expired(self):
        """Check if 7-day funding window has expired"""
        if self.status == 'listed':
            expiry_date = self.created_at + timedelta(days=7)
            return timezone.now() > expiry_date
        return False
    
    def get_days_remaining(self):
        """Get days remaining for funding"""
        if self.status == 'listed':
            expiry_date = self.created_at + timedelta(days=7)
            remaining = expiry_date - timezone.now()
            return max(0, remaining.days)
        return 0
    
    def activate_loan(self):
        """Activate loan and set next payment date"""
        self.status = 'active'
        self.activated_at = timezone.now()
        self.next_payment_date = timezone.now() + timedelta(days=30)  # First payment in 30 days
        self.save()
    
    def get_next_payment_amount(self):
        """Get the amount due for next payment"""
        if self.status == 'active':
            return self.calculate_monthly_payment()
        return 0
    
    def get_days_until_payment(self):
        """Get days until next payment"""
        if self.next_payment_date and self.status == 'active':
            remaining = self.next_payment_date - timezone.now()
            return max(0, remaining.days)
        return 0


class Investment(models.Model):
    lender = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    amount_invested = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    monthly_return = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_returns_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    def __str__(self):
        return f"{self.lender.username} invested KES {self.amount_invested} in Loan #{self.loan.id}"
    
    def calculate_monthly_return(self):
        """Calculate monthly return for this investment"""
        loan_monthly_interest = self.loan.calculate_monthly_interest()
        investment_percentage = self.amount_invested / self.loan.principal_amount
        return loan_monthly_interest * investment_percentage
    
    class Meta:
        unique_together = ['lender', 'loan']


class Commission(models.Model):
    agent = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': 'agent'})
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Commission for {self.agent.username} - Loan #{self.loan.id} - KES {self.amount}"
    
    @classmethod
    def create_commission(cls, agent, loan):
        """Create commission for agent when loan is activated"""
        platform_fee = loan.calculate_platform_fee()
        commission_amount = platform_fee * (agent.commission_rate / 100)
        
        commission = cls.objects.create(
            agent=agent,
            loan=loan,
            amount=commission_amount,
            commission_rate=agent.commission_rate
        )
        return commission


class Payment(models.Model):
    PAYMENT_TYPES = [
        ('monthly', 'Monthly Payment'),
        ('full', 'Full Payment'),
        ('partial', 'Partial Payment'),
    ]
    
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    payment_date = models.DateTimeField(auto_now_add=True)
    next_payment_date = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"Payment for Loan #{self.loan.id} - KES {self.amount}"
    
    class Meta:
        ordering = ['-payment_date']