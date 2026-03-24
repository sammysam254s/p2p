from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from .supabase_client import supabase


class LoanCalculatorService:
    """Service for loan calculations following the 30/50 rule"""
    
    @staticmethod
    def calculate_max_loan_amount(market_value):
        """Implements the 30/50 rule: 30% devaluation, then 50% of devalued amount"""
        market_value = Decimal(str(market_value))
        devalued_amount = market_value * Decimal('0.70')
        max_loan_amount = devalued_amount * Decimal('0.50')
        return max_loan_amount
    
    @staticmethod
    def calculate_platform_fee(principal_amount):
        """1% of principal amount"""
        return Decimal(str(principal_amount)) * Decimal('0.01')
    
    @staticmethod
    def calculate_insurance_fee(principal_amount):
        """1% of principal amount"""
        return Decimal(str(principal_amount)) * Decimal('0.01')
    
    @staticmethod
    def calculate_monthly_interest(principal_amount, interest_rate=13.00):
        """13% flat interest per month"""
        principal = Decimal(str(principal_amount))
        rate = Decimal(str(interest_rate))
        return principal * (rate / 100)
    
    @staticmethod
    def calculate_total_repayment(principal_amount, duration_months, interest_rate=13.00):
        """Principal + (Monthly Interest * Duration) + Platform Fee + Insurance Fee"""
        principal = Decimal(str(principal_amount))
        duration = int(duration_months)
        
        monthly_interest = LoanCalculatorService.calculate_monthly_interest(principal, interest_rate)
        total_interest = monthly_interest * duration
        platform_fee = LoanCalculatorService.calculate_platform_fee(principal)
        insurance_fee = LoanCalculatorService.calculate_insurance_fee(principal)
        
        return principal + total_interest + platform_fee + insurance_fee


class SupabaseDataService:
    """Service for interacting with Supabase database"""
    
    @staticmethod
    def create_user(user_data):
        """Create a new user in Supabase"""
        return supabase.insert('users', user_data)
    
    @staticmethod
    def get_user_by_username(username):
        """Get user by username"""
        result = supabase.select('users', filters={'username': username})
        return result[0] if result else None
    
    @staticmethod
    def create_collateral(collateral_data):
        """Create collateral record"""
        return supabase.insert('collateral', collateral_data)
    
    @staticmethod
    def get_pending_collaterals():
        """Get all pending collateral items"""
        return supabase.select('collateral', filters={'status': 'pending'})
    
    @staticmethod
    def update_collateral_status(collateral_id, status, verification_date=None):
        """Update collateral status"""
        data = {'status': status}
        if verification_date:
            data['verification_date'] = verification_date.isoformat()
        
        return supabase.update('collateral', data, {'id': collateral_id})
    
    @staticmethod
    def create_loan(loan_data):
        """Create a new loan"""
        return supabase.insert('loans', loan_data)
    
    @staticmethod
    def get_loans_by_borrower(borrower_id):
        """Get all loans for a borrower"""
        return supabase.select('loans', filters={'borrower_id': borrower_id})
    
    @staticmethod
    def get_listed_loans():
        """Get all loans with status 'listed'"""
        return supabase.select('loans', filters={'status': 'listed'})
    
    @staticmethod
    def update_loan_status(loan_id, status):
        """Update loan status"""
        return supabase.update('loans', {'status': status}, {'id': loan_id})
    
    @staticmethod
    def update_loan_funding(loan_id, funded_amount):
        """Update loan funded amount"""
        return supabase.update('loans', {'funded_amount': funded_amount}, {'id': loan_id})
    
    @staticmethod
    def create_investment(investment_data):
        """Create a new investment"""
        return supabase.insert('investments', investment_data)
    
    @staticmethod
    def get_investments_by_loan(loan_id):
        """Get all investments for a loan"""
        return supabase.select('investments', filters={'loan_id': loan_id})
    
    @staticmethod
    def get_loan_with_details(loan_id):
        """Get loan with collateral and borrower details"""
        # This would need to be implemented with proper joins in a real scenario
        # For now, we'll make separate calls
        loan = supabase.select('loans', filters={'id': loan_id})
        if loan:
            loan = loan[0]
            # Get collateral details
            collateral = supabase.select('collateral', filters={'id': loan['collateral_id']})
            if collateral:
                loan['collateral'] = collateral[0]
            
            # Get borrower details
            borrower = supabase.select('users', filters={'id': loan['borrower_id']})
            if borrower:
                loan['borrower'] = borrower[0]
            
            return loan
        return None