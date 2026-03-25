import requests
import json
import uuid
from datetime import datetime, timezone
from django.conf import settings
from decouple import config
from decimal import Decimal


class SupabaseTable:
    """Table interface for chaining Supabase operations"""
    
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self._filters = {}
        self._columns = "*"
        self._order = None
        self._limit = None
    
    def select(self, columns="*"):
        """Select specific columns"""
        self._columns = columns
        return self
    
    def eq(self, column, value):
        """Add equality filter"""
        self._filters[column] = value
        return self
    
    def execute(self):
        """Execute the query"""
        if hasattr(self, '_insert_data'):
            # Insert operation
            return type('Result', (), {'data': self.client.insert(self.table_name, self._insert_data)})()
        elif hasattr(self, '_update_data'):
            # Update operation
            return type('Result', (), {'data': self.client.update(self.table_name, self._update_data, self._filters)})()
        elif hasattr(self, '_delete_flag'):
            # Delete operation
            return type('Result', (), {'data': self.client.delete(self.table_name, self._filters)})()
        else:
            # Select operation
            result = self.client.select(self.table_name, self._columns, self._filters, self._order, self._limit)
            return type('Result', (), {'data': result})()
    
    def insert(self, data):
        """Insert data"""
        self._insert_data = data
        return self
    
    def update(self, data):
        """Update data"""
        self._update_data = data
        return self
    
    def delete(self):
        """Delete data"""
        self._delete_flag = True
        return self


class SupabaseClient:
    def __init__(self):
        self.url = config('SUPABASE_URL')
        self.anon_key = config('SUPABASE_ANON_KEY')
        self.headers = {
            'apikey': self.anon_key,
            'Authorization': f'Bearer {self.anon_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
    
    def table(self, table_name):
        """Return a table interface for chaining operations"""
        return SupabaseTable(self, table_name)
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """Make HTTP request to Supabase REST API"""
        url = f"{self.url}/rest/v1/{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers, params=params)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            elif method == 'PATCH':
                response = requests.patch(url, headers=self.headers, json=data)
            elif method == 'DELETE':
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json() if response.content else None
            
        except requests.exceptions.RequestException as e:
            print(f"Supabase request error: {e}")
            return None
    
    def select(self, table, columns="*", filters=None, order=None, limit=None):
        """Select data from table - simplified without caching for now"""
        params = {'select': columns}
        
        if filters:
            for key, value in filters.items():
                params[key] = f'eq.{value}'
        
        if order:
            params['order'] = order
        
        if limit:
            params['limit'] = limit
            
        return self._make_request('GET', table, params=params)
    
    def insert(self, table, data):
        """Insert data into table"""
        if isinstance(data, list):
            return self._make_request('POST', table, data=data)
        else:
            return self._make_request('POST', table, data=[data])
    
    def update(self, table, data, filters):
        """Update data in table"""
        params = {}
        for key, value in filters.items():
            params[key] = f'eq.{value}'
        
        endpoint = f"{table}?" + "&".join([f"{k}={v}" for k, v in params.items()])
        return self._make_request('PATCH', endpoint, data=data)
    
    def delete(self, table, filters):
        """Delete data from table"""
        params = {}
        for key, value in filters.items():
            params[key] = f'eq.{value}'
        
        endpoint = f"{table}?" + "&".join([f"{k}={v}" for k, v in params.items()])
        return self._make_request('DELETE', endpoint)
    
    def rpc(self, function_name, params=None):
        """Call a Supabase stored procedure/function"""
        endpoint = f"rpc/{function_name}"
        return self._make_request('POST', endpoint, data=params or {})


class SupabaseUserService:
    """Service for user operations in Supabase"""
    
    def __init__(self):
        self.client = SupabaseClient()
    
    def create_user(self, username, email, password, role, phone_number, national_id, first_name="", last_name=""):
        """Create a new user"""
        user_data = {
            'id': str(uuid.uuid4()),
            'username': username,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'role': role,
            'phone_number': phone_number,
            'national_id': national_id,
            'is_active': True,
            'is_staff': role == 'admin',
            'is_superuser': role == 'admin',
            'wallet_balance': 0.00,
            'total_earnings': 0.00,
            'commission_rate': 0.50 if role == 'agent' else 0.00,
            'is_promoted_admin': role == 'admin',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        return self.client.insert('users', user_data)
    
    def get_user_by_username(self, username):
        """Get user by username - simplified without caching for now"""
        result = self.client.select('users', filters={'username': username})
        return result[0] if result else None
    
    def get_user_by_email(self, email):
        """Get user by email - simplified without caching for now"""
        result = self.client.select('users', filters={'email': email})
        return result[0] if result else None
    
    def get_user_by_id(self, user_id):
        """Get user by ID - simplified without caching for now"""
        result = self.client.select('users', filters={'id': user_id})
        return result[0] if result else None
    
    def update_user(self, user_id, data):
        """Update user data"""
        data['updated_at'] = datetime.now(timezone.utc).isoformat()
        return self.client.update('users', data, {'id': user_id})
    
    def authenticate_user(self, username, password):
        """Authenticate user (simplified - in production use Supabase Auth)"""
        user = self.get_user_by_username(username)
        if user and user.get('is_active'):
            # In a real implementation, you'd verify the password hash
            # For now, we'll just return the user if found
            return user
        return None
    
    def get_user_by_national_id(self, national_id):
        """Get user by national ID"""
        all_users = self.client.select('users')
        if all_users:
            for user in all_users:
                if user.get('national_id') == national_id:
                    return user
        return None
    
    def get_all_users(self):
        """Get all users"""
        return self.client.select('users', order='created_at.desc')
    
    def get_users_by_role(self, role):
        """Get users by role"""
        return self.client.select('users', filters={'role': role}, order='created_at.desc')


class SupabaseCollateralService:
    """Service for collateral operations"""
    
    def __init__(self):
        self.client = SupabaseClient()
    
    def create_collateral(self, user_id, item_type, brand_model, market_value):
        """Create collateral record"""
        collateral_data = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'item_type': item_type,
            'brand_model': brand_model,
            'market_value': float(market_value),
            'status': 'pending',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        return self.client.insert('collateral', collateral_data)
    
    def get_user_collaterals(self, user_id):
        """Get all collaterals for a user"""
        return self.client.select('collateral', filters={'user_id': user_id}, order='created_at.desc')
    
    def get_pending_collaterals(self):
        """Get all pending collateral items"""
        return self.client.select('collateral', filters={'status': 'pending'}, order='created_at.desc')
    
    def update_collateral_status(self, collateral_id, status, verified_by=None):
        """Update collateral status"""
        data = {
            'status': status,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        if status == 'verified':
            data['verification_date'] = datetime.now(timezone.utc).isoformat()
            if verified_by:
                data['verified_by'] = verified_by
        
        return self.client.update('collateral', data, {'id': collateral_id})
    
    def get_collateral_by_id(self, collateral_id):
        """Get collateral by ID"""
        result = self.client.select('collateral', filters={'id': collateral_id})
        return result[0] if result else None
    
    def get_all_collaterals(self):
        """Get all collaterals"""
        return self.client.select('collateral', order='created_at.desc')


class SupabaseLoanService:
    """Service for loan operations"""
    
    def __init__(self):
        self.client = SupabaseClient()
    
    def create_loan(self, borrower_id, collateral_id, principal_amount, interest_rate=13.00, duration_months=3):
        """Create a new loan"""
        loan_data = {
            'id': str(uuid.uuid4()),
            'borrower_id': borrower_id,
            'collateral_id': collateral_id,
            'principal_amount': float(principal_amount),
            'interest_rate': float(interest_rate),
            'duration_months': int(duration_months),
            'funded_amount': 0.00,
            'status': 'pending_collateral',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        return self.client.insert('loans', loan_data)
    
    def get_loans_by_borrower(self, borrower_id):
        """Get all loans for a borrower"""
        return self.client.select('loans', filters={'borrower_id': borrower_id}, order='created_at.desc')
    
    def get_listed_loans(self):
        """Get all loans with status 'listed'"""
        return self.client.select('loans', filters={'status': 'listed'}, order='created_at.desc')
    
    def get_all_loans(self):
        """Get all loans"""
        return self.client.select('loans', order='created_at.desc')
    
    def update_loan_status(self, loan_id, status):
        """Update loan status"""
        data = {
            'status': status,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        return self.client.update('loans', data, {'id': loan_id})
    
    def update_loan_funding(self, loan_id, funded_amount):
        """Update loan funded amount"""
        data = {
            'funded_amount': float(funded_amount),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        return self.client.update('loans', data, {'id': loan_id})
    
    def get_loan_by_id(self, loan_id):
        """Get loan by ID"""
        result = self.client.select('loans', filters={'id': loan_id})
        return result[0] if result else None


class SupabaseInvestmentService:
    """Service for investment operations"""
    
    def __init__(self):
        self.client = SupabaseClient()
    
    def create_investment(self, lender_id, loan_id, amount_invested):
        """Create a new investment"""
        investment_data = {
            'id': str(uuid.uuid4()),
            'lender_id': lender_id,
            'loan_id': loan_id,
            'amount_invested': float(amount_invested),
            'date': datetime.now(timezone.utc).isoformat(),
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        return self.client.insert('investments', investment_data)
    
    def get_investments_by_loan(self, loan_id):
        """Get all investments for a loan"""
        return self.client.select('investments', filters={'loan_id': loan_id}, order='date.desc')
    
    def get_investments_by_lender(self, lender_id):
        """Get all investments by a lender"""
        return self.client.select('investments', filters={'lender_id': lender_id}, order='date.desc')
    
    def get_all_investments(self):
        """Get all investments"""
        return self.client.select('investments', order='date.desc')


# Global instances
supabase = SupabaseClient()
user_service = SupabaseUserService()
collateral_service = SupabaseCollateralService()
loan_service = SupabaseLoanService()
investment_service = SupabaseInvestmentService()