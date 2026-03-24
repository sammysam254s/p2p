from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from .supabase_client import (
    supabase, user_service, collateral_service, 
    loan_service, investment_service
)


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


class SupabaseService:
    """Main service class that combines all Supabase operations"""
    
    def __init__(self):
        self.user_service = user_service
        self.collateral_service = collateral_service
        self.loan_service = loan_service
        self.investment_service = investment_service
        self.calculator = LoanCalculatorService()
    
    # User operations
    def create_user(self, username, email, password, role, phone_number, national_id, first_name="", last_name=""):
        """Create a new user"""
        return self.user_service.create_user(
            username, email, password, role, phone_number, national_id, first_name, last_name
        )
    
    def authenticate_user(self, username, password):
        """Authenticate user"""
        return self.user_service.authenticate_user(username, password)
    
    def get_user_by_username(self, username):
        """Get user by username"""
        return self.user_service.get_user_by_username(username)
    
    def get_user_by_email(self, email):
        """Get user by email"""
        return self.user_service.get_user_by_email(email)
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        return self.user_service.get_user_by_id(user_id)
    
    def update_user(self, user_id, data):
        """Update user"""
        return self.user_service.update_user(user_id, data)
    
    def get_all_users(self):
        """Get all users"""
        return self.user_service.get_all_users()
    
    def get_users_by_role(self, role):
        """Get users by role"""
        return self.user_service.get_users_by_role(role)
    
    # Collateral operations
    def create_collateral(self, user_id, item_type, brand_model, market_value):
        """Create collateral"""
        return self.collateral_service.create_collateral(user_id, item_type, brand_model, market_value)
    
    def get_user_collaterals(self, user_id):
        """Get user's collaterals"""
        return self.collateral_service.get_user_collaterals(user_id)
    
    def get_pending_collaterals(self):
        """Get pending collaterals"""
        return self.collateral_service.get_pending_collaterals()
    
    def update_collateral_status(self, collateral_id, status, verified_by=None):
        """Update collateral status"""
        return self.collateral_service.update_collateral_status(collateral_id, status, verified_by)
    
    def get_collateral_by_id(self, collateral_id):
        """Get collateral by ID"""
        return self.collateral_service.get_collateral_by_id(collateral_id)
    
    # Loan operations
    def create_loan(self, borrower_id, collateral_id, principal_amount, interest_rate=13.00, duration_months=3):
        """Create loan"""
        return self.loan_service.create_loan(borrower_id, collateral_id, principal_amount, interest_rate, duration_months)
    
    def get_loans_by_borrower(self, borrower_id):
        """Get borrower's loans"""
        return self.loan_service.get_loans_by_borrower(borrower_id)
    
    def get_listed_loans(self):
        """Get listed loans"""
        return self.loan_service.get_listed_loans()
    
    def get_all_loans(self):
        """Get all loans"""
        return self.loan_service.get_all_loans()
    
    def update_loan_status(self, loan_id, status):
        """Update loan status"""
        return self.loan_service.update_loan_status(loan_id, status)
    
    def update_loan_funding(self, loan_id, funded_amount):
        """Update loan funding"""
        return self.loan_service.update_loan_funding(loan_id, funded_amount)
    
    def get_loan_by_id(self, loan_id):
        """Get loan by ID"""
        return self.loan_service.get_loan_by_id(loan_id)
    
    # Investment operations
    def create_investment(self, lender_id, loan_id, amount_invested):
        """Create investment"""
        return self.investment_service.create_investment(lender_id, loan_id, amount_invested)
    
    def get_investments_by_loan(self, loan_id):
        """Get loan investments"""
        return self.investment_service.get_investments_by_loan(loan_id)
    
    def get_investments_by_lender(self, lender_id):
        """Get lender investments"""
        return self.investment_service.get_investments_by_lender(lender_id)
    
    def get_all_investments(self):
        """Get all investments"""
        return self.investment_service.get_all_investments()
    
    # Complex operations
    def get_loan_with_details(self, loan_id):
        """Get loan with all related details"""
        loan = self.get_loan_by_id(loan_id)
        if not loan:
            return None
        
        # Get collateral details
        collateral = self.get_collateral_by_id(loan['collateral_id'])
        if collateral:
            loan['collateral'] = collateral
        
        # Get borrower details
        borrower = self.get_user_by_id(loan['borrower_id'])
        if borrower:
            loan['borrower'] = borrower
        
        # Get investments
        investments = self.get_investments_by_loan(loan_id)
        loan['investments'] = investments or []
        
        # Calculate loan metrics
        loan['max_loan_amount'] = float(self.calculator.calculate_max_loan_amount(collateral['market_value'])) if collateral else 0
        loan['platform_fee'] = float(self.calculator.calculate_platform_fee(loan['principal_amount']))
        loan['insurance_fee'] = float(self.calculator.calculate_insurance_fee(loan['principal_amount']))
        loan['monthly_interest'] = float(self.calculator.calculate_monthly_interest(loan['principal_amount'], loan['interest_rate']))
        loan['total_repayment'] = float(self.calculator.calculate_total_repayment(loan['principal_amount'], loan['duration_months'], loan['interest_rate']))
        
        # Calculate funding percentage
        if loan['principal_amount'] > 0:
            loan['funding_percentage'] = (loan['funded_amount'] / loan['principal_amount']) * 100
        else:
            loan['funding_percentage'] = 0
        
        return loan
    
    def get_dashboard_stats(self):
        """Get dashboard statistics"""
        all_users = self.get_all_users() or []
        all_loans = self.get_all_loans() or []
        all_investments = self.get_all_investments() or []
        
        stats = {
            'total_users': len(all_users),
            'total_borrowers': len([u for u in all_users if u.get('role') == 'borrower']),
            'total_lenders': len([u for u in all_users if u.get('role') == 'lender']),
            'total_agents': len([u for u in all_users if u.get('role') == 'agent']),
            'total_loans': len(all_loans),
            'active_loans': len([l for l in all_loans if l.get('status') == 'active']),
            'listed_loans': len([l for l in all_loans if l.get('status') == 'listed']),
            'total_investments': len(all_investments),
            'total_funded_amount': sum([float(i.get('amount_invested', 0)) for i in all_investments]),
            'total_loan_amount': sum([float(l.get('principal_amount', 0)) for l in all_loans])
        }
        
        return stats


# Global service instance
supabase_service = SupabaseService()