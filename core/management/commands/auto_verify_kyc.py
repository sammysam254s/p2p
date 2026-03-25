from django.core.management.base import BaseCommand
from django.utils import timezone
from core.supabase_client import supabase
from core.services import supabase_service
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Automatically verify pending KYC records that meet criteria'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be verified without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('Starting automatic KYC verification...'))
        
        try:
            # Get all pending KYC records
            kyc_result = supabase.table('kyc_verifications').select('*').execute()
            kyc_records = kyc_result.data or []
            
            pending_records = [kyc for kyc in kyc_records if kyc.get('status') in ['pending', 'under_review']]
            
            self.stdout.write(f'Found {len(pending_records)} pending KYC records')
            
            verified_count = 0
            
            for kyc in pending_records:
                try:
                    # Get user info
                    user = supabase_service.get_user_by_id(kyc['user_id'])
                    username = user.get('username', 'Unknown') if user else 'Unknown'
                    
                    # Check verification criteria
                    has_name = kyc.get('full_name') and len(kyc.get('full_name', '').strip()) > 2
                    has_id_number = kyc.get('id_number') and len(kyc.get('id_number', '').strip()) >= 6
                    has_images = (
                        kyc.get('has_id_front_image', False) and 
                        kyc.get('has_id_back_image', False) and 
                        kyc.get('has_selfie_image', False) and 
                        kyc.get('has_signature_image', False)
                    )
                    
                    # Calculate score
                    score = 0
                    if has_name:
                        score += 25
                    if has_id_number:
                        score += 35
                    if has_images:
                        score += 40
                    
                    # Auto-verify if meets criteria
                    if (has_name and has_id_number and has_images) or (has_name and has_id_number and score >= 60):
                        if dry_run:
                            self.stdout.write(f'  [DRY RUN] Would verify: {username} (score: {score})')
                        else:
                            # Verify the record
                            update_data = {
                                'status': 'verified',
                                'verified_at': timezone.now().isoformat(),
                                'verification_score': score,
                                'updated_at': timezone.now().isoformat()
                            }
                            
                            update_result = supabase.table('kyc_verifications').update(update_data).eq('id', kyc['id']).execute()
                            
                            if update_result.data:
                                self.stdout.write(self.style.SUCCESS(f'  ✓ Verified: {username} (score: {score})'))
                                verified_count += 1
                            else:
                                self.stdout.write(self.style.ERROR(f'  ✗ Failed to verify: {username}'))
                    else:
                        missing = []
                        if not has_name:
                            missing.append('name')
                        if not has_id_number:
                            missing.append('ID number')
                        if not has_images:
                            missing.append('images')
                        
                        self.stdout.write(f'  - Skipping {username}: missing {", ".join(missing)} (score: {score})')
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Error processing {username}: {str(e)}'))
            
            if dry_run:
                self.stdout.write(self.style.WARNING(f'DRY RUN: Would have verified {verified_count} records'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Successfully verified {verified_count} KYC records'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error in auto KYC verification: {str(e)}'))
            raise e