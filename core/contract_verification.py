"""
Contract Verification System for P2P Secure-Lend Kenya
Handles QR code verification and contract authenticity checking
"""

import uuid
from datetime import datetime, timedelta
from core.services import supabase_service
from core.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

class ContractVerificationService:
    """Service for contract verification and QR code management"""
    
    def __init__(self):
        pass
    
    def create_contract_record(self, loan_id, contract_id, pdf_url, borrower_id, lender_ids):
        """
        Create a contract verification record in Supabase
        
        Args:
            loan_id: UUID of the loan
            contract_id: Unique contract identifier
            pdf_url: Supabase Storage URL to the PDF file
            borrower_id: UUID of borrower
            lender_ids: List of lender UUIDs
        """
        try:
            # Get loan details
            loan = supabase_service.get_loan_with_details(loan_id)
            if not loan:
                return None
            
            # Calculate due date
            duration_months = loan.get('duration_months', 3)
            due_date = datetime.now() + timedelta(days=duration_months * 30)
            
            # Create contract record in Supabase
            contract_data = {
                'id': contract_id,
                'loan_id': loan_id,
                'borrower_id': borrower_id,
                'lender_ids': lender_ids,  # Store as JSON array
                'pdf_url': pdf_url,  # Supabase Storage URL
                'principal_amount': float(loan.get('principal_amount', 0)),
                'total_repayment': float(loan.get('calculate_total_repayment', 0)),
                'due_date': due_date.isoformat(),
                'status': 'active',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            result = supabase.table('loan_contracts').insert(contract_data).execute()
            
            if result.data:
                logger.info(f"Contract record created in Supabase: {contract_id}")
                return result.data[0]
            else:
                logger.error(f"Failed to create contract record in Supabase: {contract_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating contract record in Supabase: {str(e)}")
            return None
    
    def verify_contract(self, contract_id):
        """
        Verify contract by ID and return contract details
        
        Args:
            contract_id: Unique contract identifier
            
        Returns:
            Dict with contract details or None if not found
        """
        try:
            # Get contract from database
            result = supabase.table('loan_contracts').select('*').eq('id', contract_id).execute()
            
            if not result.data:
                return None
            
            contract = result.data[0]
            
            # Get borrower details
            borrower = supabase_service.get_user_by_id(contract['borrower_id'])
            
            # Get lender details
            lenders = []
            for lender_id in contract.get('lender_ids', []):
                lender = supabase_service.get_user_by_id(lender_id)
                if lender:
                    lenders.append(lender)
            
            # Get loan details
            loan = supabase_service.get_loan_with_details(contract['loan_id'])
            
            # Calculate days until due
            due_date = datetime.fromisoformat(contract['due_date'].replace('Z', '+00:00'))
            days_until_due = (due_date - datetime.now()).days
            
            verification_data = {
                'contract_id': contract_id,
                'loan_id': contract['loan_id'],
                'borrower': {
                    'name': borrower.get('username') if borrower else 'Unknown',
                    'email': borrower.get('email') if borrower else 'N/A',
                    'national_id': borrower.get('national_id') if borrower else 'N/A'
                },
                'lenders': [
                    {
                        'name': lender.get('username', 'Unknown'),
                        'email': lender.get('email', 'N/A')
                    } for lender in lenders
                ],
                'loan_details': {
                    'principal_amount': contract['principal_amount'],
                    'total_repayment': contract['total_repayment'],
                    'due_date': due_date.strftime('%B %d, %Y'),
                    'days_until_due': days_until_due,
                    'status': contract['status'],
                    'collateral': loan.get('collateral', {}).get('brand_model', 'N/A') if loan else 'N/A'
                },
                'contract_details': {
                    'created_date': datetime.fromisoformat(contract['created_at'].replace('Z', '+00:00')).strftime('%B %d, %Y'),
                    'pdf_url': contract['pdf_url'],
                    'is_overdue': days_until_due < 0,
                    'verification_time': datetime.now().strftime('%B %d, %Y at %I:%M %p')
                }
            }
            
            logger.info(f"Contract verified: {contract_id}")
            return verification_data
            
        except Exception as e:
            logger.error(f"Error verifying contract {contract_id}: {str(e)}")
            return None
    
    def get_all_contracts(self):
        """Get all contracts for admin management"""
        try:
            result = supabase.table('loan_contracts').select('*').order('created_at', desc=True).execute()
            
            if not result.data:
                return []
            
            contracts = []
            for contract in result.data:
                # Get borrower name
                borrower = supabase_service.get_user_by_id(contract['borrower_id'])
                borrower_name = borrower.get('username') if borrower else 'Unknown'
                
                # Count lenders
                lender_count = len(contract.get('lender_ids', []))
                
                # Calculate status
                due_date = datetime.fromisoformat(contract['due_date'].replace('Z', '+00:00'))
                days_until_due = (due_date - datetime.now()).days
                
                if days_until_due < 0:
                    status_display = f"Overdue ({abs(days_until_due)} days)"
                    status_class = "danger"
                elif days_until_due <= 7:
                    status_display = f"Due in {days_until_due} days"
                    status_class = "warning"
                else:
                    status_display = f"Due in {days_until_due} days"
                    status_class = "success"
                
                contracts.append({
                    'id': contract['id'],
                    'loan_id': contract['loan_id'],
                    'borrower_name': borrower_name,
                    'lender_count': lender_count,
                    'principal_amount': contract['principal_amount'],
                    'due_date': due_date.strftime('%b %d, %Y'),
                    'days_until_due': days_until_due,
                    'status_display': status_display,
                    'status_class': status_class,
                    'created_at': datetime.fromisoformat(contract['created_at'].replace('Z', '+00:00')).strftime('%b %d, %Y'),
                    'pdf_url': contract['pdf_url']
                })
            
            return contracts
            
        except Exception as e:
            logger.error(f"Error getting contracts: {str(e)}")
            return []
    
    def update_contract_status(self, contract_id, status):
        """Update contract status"""
        try:
            result = supabase.table('loan_contracts').update({
                'status': status,
                'updated_at': datetime.now().isoformat()
            }).eq('id', contract_id).execute()
            
            return result.data is not None
            
        except Exception as e:
            logger.error(f"Error updating contract status: {str(e)}")
            return False


# Global service instance
contract_verification_service = ContractVerificationService()