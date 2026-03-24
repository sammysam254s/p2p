from django.contrib.auth.models import AbstractUser
from django.db import models
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('borrower', 'Borrower'),
        ('lender', 'Lender'),
        ('agent', 'Station Agent'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=15, help_text="M-Pesa phone number")
    national_id = models.CharField(max_length=20, unique=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    verification_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.brand_model} - KES {self.market_value}"
    
    def calculate_max_loan_amount(self):
        """Implements the 30/50 rule: 30% devaluation, then 50% of devalued amount"""
        devalued_amount = self.market_value * Decimal('0.70')
        max_loan_amount = devalued_amount * Decimal('0.50')
        return max_loan_amount


class Loan(models.Model):
    STATUS_CHOICES = [
        ('pending_collateral', 'Pending Collateral'),
        ('listed', 'Listed'),
        ('active', 'Active'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    borrower = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    collateral = models.OneToOneField(Collateral, on_delete=models.CASCADE)
    principal_amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=13.00)
    duration_months = models.IntegerField()
    funded_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_collateral')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Loan #{self.id} - KES {self.principal_amount}"
    
    def calculate_platform_fee(self):
        """1% of principal amount"""
        return self.principal_amount * Decimal('0.01')
    
    def calculate_insurance_fee(self):
        """1% of principal amount"""
        return self.principal_amount * Decimal('0.01')
    
    def calculate_monthly_interest(self):
        """13% flat interest per month"""
        return self.principal_amount * (self.interest_rate / 100)
    
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


class Investment(models.Model):
    lender = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    amount_invested = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.lender.username} invested KES {self.amount_invested} in Loan #{self.loan.id}"
    
    class Meta:
        unique_together = ['lender', 'loan']  # Prevent duplicate investments from same lender