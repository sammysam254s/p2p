"""
Management command to generate PDF contracts for already funded loans
Run with: python manage.py generate_missing_contracts
"""

from django.core.management.base import BaseCommand
from core.services import supabase_service
from core.supabase_client import supabase
from core.contract_pdf_service import contract_pdf_service
from core.contract_verification import contract_verification_service
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate PDF contracts for already funded loans that are missing contracts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regenerate contracts even if they already exist',
        )
        parser.add_argument(
            '--loan-id',
            type=str,
            help='Generate contract for specific loan ID only',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔄 Starting contract generation for funded loans...'))
        
        try:
            # Get all active loans from Supabase
            if options['loan_id']:
                # Generate for specific loan
                loans = [supabase_service.get_loan_with_details(options['loan_id'])]
                loans = [loan for loan in loans if loan]  # Filter out None
                self.stdout.write(f"📋 Processing specific loan: {options['loan_id']}")
            else:
                # Get all active loans
                all_loans = supabase_service.get_all_loans() or []
                loans = [loan for loan in all_loans if loan.get('status') == 'active']
                self.stdout.write(f"📋 Found {len(loans)} active loans")

            if not loans:
                self.stdout.write(self.style.WARNING('⚠️ No active loans found'))
                return

            generated_count = 0
            skipped_count = 0
            error_count = 0

            for loan in loans:
                try:
                    loan_id = loan['id']
                    self.stdout.write(f"\n🔍 Processing loan {loan_id}...")

                    # Check if contract already exists
                    existing_contract = supabase.table('loan_contracts').select('id').eq('loan_id', loan_id).execute()
                    
                    if existing_contract.data and not options['force']:
                        self.stdout.write(f"⏭️ Contract already exists for loan {loan_id}, skipping...")
                        skipped_count += 1
                        continue

                    # Get full loan details
                    full_loan_data = supabase_service.get_loan_with_details(loan_id)
                    if not full_loan_data:
                        self.stdout.write(self.style.ERROR(f"❌ Could not get loan details for {loan_id}"))
                        error_count += 1
                        continue

                    # Get borrower data
                    borrower_id = full_loan_data.get('borrower_id')
                    if not borrower_id:
                        self.stdout.write(self.style.ERROR(f"❌ No borrower ID for loan {loan_id}"))
                        error_count += 1
                        continue

                    borrower_data = supabase_service.get_user_by_id(borrower_id)
                    if not borrower_data:
                        self.stdout.write(self.style.ERROR(f"❌ Could not get borrower data for loan {loan_id}"))
                        error_count += 1
                        continue

                    # Get all lenders for this loan
                    loan_investments = supabase_service.get_investments_by_loan(loan_id) or []
                    if not loan_investments:
                        self.stdout.write(self.style.WARNING(f"⚠️ No investments found for loan {loan_id}"))
                        error_count += 1
                        continue

                    lenders_data = []
                    lender_ids = []

                    for investment in loan_investments:
                        lender = supabase_service.get_user_by_id(investment['lender_id'])
                        if lender:
                            lender['amount_invested'] = investment['amount_invested']
                            lenders_data.append(lender)
                            lender_ids.append(lender['id'])

                    if not lenders_data:
                        self.stdout.write(self.style.ERROR(f"❌ Could not get lender data for loan {loan_id}"))
                        error_count += 1
                        continue

                    # Get borrower KYC data
                    kyc_data = supabase_service.get_kyc_by_user_id(borrower_id) or {}

                    self.stdout.write(f"📄 Generating PDF contract for loan {loan_id}...")
                    self.stdout.write(f"   👤 Borrower: {borrower_data.get('username', 'N/A')}")
                    self.stdout.write(f"   💰 Amount: KES {full_loan_data.get('principal_amount', 0):,.2f}")
                    self.stdout.write(f"   🏦 Lenders: {len(lenders_data)}")

                    # Generate PDF contract
                    pdf_result = contract_pdf_service.generate_contract_pdf(
                        loan_data=full_loan_data,
                        borrower_data=borrower_data,
                        lenders_data=lenders_data,
                        kyc_data=kyc_data
                    )

                    if pdf_result.get('success'):
                        # Delete existing contract if force regeneration
                        if options['force'] and existing_contract.data:
                            supabase.table('loan_contracts').delete().eq('loan_id', loan_id).execute()
                            self.stdout.write(f"🗑️ Deleted existing contract for loan {loan_id}")

                        # Create contract verification record
                        contract_record = contract_verification_service.create_contract_record(
                            loan_id=loan_id,
                            contract_id=pdf_result['contract_id'],
                            pdf_url=pdf_result['url'],
                            borrower_id=borrower_id,
                            lender_ids=lender_ids
                        )

                        if contract_record:
                            self.stdout.write(self.style.SUCCESS(f"✅ Contract generated successfully for loan {loan_id}"))
                            self.stdout.write(f"   📁 File: {pdf_result['filename']}")
                            self.stdout.write(f"   🔗 URL: {pdf_result['url']}")
                            self.stdout.write(f"   🆔 Contract ID: {pdf_result['contract_id']}")
                            generated_count += 1
                        else:
                            self.stdout.write(self.style.ERROR(f"❌ Failed to create contract record for loan {loan_id}"))
                            error_count += 1
                    else:
                        self.stdout.write(self.style.ERROR(f"❌ PDF generation failed for loan {loan_id}: {pdf_result.get('error')}"))
                        error_count += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Error processing loan {loan.get('id', 'unknown')}: {str(e)}"))
                    error_count += 1

            # Summary
            self.stdout.write(f"\n" + "="*50)
            self.stdout.write(self.style.SUCCESS(f"📊 CONTRACT GENERATION SUMMARY"))
            self.stdout.write(f"✅ Generated: {generated_count}")
            self.stdout.write(f"⏭️ Skipped: {skipped_count}")
            self.stdout.write(f"❌ Errors: {error_count}")
            self.stdout.write(f"📋 Total processed: {len(loans)}")

            if generated_count > 0:
                self.stdout.write(self.style.SUCCESS(f"\n🎉 Successfully generated {generated_count} contracts!"))
                self.stdout.write("📱 Contracts are now available for download by borrowers, lenders, and admin.")
                self.stdout.write("🔍 Use QR codes on contracts for verification.")
            
            if error_count > 0:
                self.stdout.write(self.style.WARNING(f"\n⚠️ {error_count} contracts failed to generate. Check logs for details."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Command failed: {str(e)}"))
            logger.error(f"Contract generation command failed: {str(e)}")