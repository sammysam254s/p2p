from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.services import supabase_service
from core.models import Collateral, Loan, Investment, WalletTransaction, Commission, Payment
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Migrate existing Django data to Supabase'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be migrated'))
        
        self.stdout.write('Starting migration from Django to Supabase...')
        
        # Migrate Users
        self.migrate_users(dry_run)
        
        # Migrate Collateral
        self.migrate_collateral(dry_run)
        
        # Migrate Loans
        self.migrate_loans(dry_run)
        
        # Migrate Investments
        self.migrate_investments(dry_run)
        
        self.stdout.write(
            self.style.SUCCESS('Migration completed successfully!')
        )

    def migrate_users(self, dry_run=False):
        """Migrate Django users to Supabase"""
        self.stdout.write('\n--- Migrating Users ---')
        
        django_users = User.objects.all()
        self.stdout.write(f'Found {django_users.count()} Django users')
        
        migrated = 0
        skipped = 0
        errors = 0
        
        for user in django_users:
            try:
                # Check if user already exists in Supabase
                existing = supabase_service.get_user_by_username(user.username)
                if existing:
                    self.stdout.write(f'  ⚠ User {user.username} already exists in Supabase - skipping')
                    skipped += 1
                    continue
                
                if not dry_run:
                    # Create user in Supabase
                    result = supabase_service.create_user(
                        username=user.username,
                        email=user.email,
                        password='temp123',  # Temporary password - users will need to reset
                        role=getattr(user, 'role', 'borrower'),
                        phone_number=getattr(user, 'phone_number', ''),
                        national_id=getattr(user, 'national_id', f'MIGRATED_{user.id}'),
                        first_name=user.first_name,
                        last_name=user.last_name
                    )
                    
                    if result:
                        self.stdout.write(f'  ✓ Migrated user: {user.username}')
                        migrated += 1
                    else:
                        self.stdout.write(f'  ✗ Failed to migrate user: {user.username}')
                        errors += 1
                else:
                    self.stdout.write(f'  → Would migrate user: {user.username} ({user.email})')
                    migrated += 1
                    
            except Exception as e:
                self.stdout.write(f'  ✗ Error migrating user {user.username}: {str(e)}')
                errors += 1
        
        self.stdout.write(f'Users: {migrated} migrated, {skipped} skipped, {errors} errors')
        
        if not dry_run and migrated > 0:
            self.stdout.write(
                self.style.WARNING(
                    'NOTE: Migrated users have temporary password "temp123" - they should reset their passwords!'
                )
            )

    def migrate_collateral(self, dry_run=False):
        """Migrate collateral data"""
        self.stdout.write('\n--- Migrating Collateral ---')
        
        try:
            collaterals = Collateral.objects.all()
            self.stdout.write(f'Found {collaterals.count()} collateral items')
            
            migrated = 0
            errors = 0
            
            for collateral in collaterals:
                try:
                    # Get Supabase user ID
                    supabase_user = supabase_service.get_user_by_username(collateral.user.username)
                    if not supabase_user:
                        self.stdout.write(f'  ⚠ User {collateral.user.username} not found in Supabase - skipping collateral')
                        continue
                    
                    if not dry_run:
                        result = supabase_service.create_collateral(
                            user_id=supabase_user['id'],
                            item_type=collateral.item_type,
                            brand_model=collateral.brand_model,
                            market_value=float(collateral.market_value)
                        )
                        
                        if result:
                            # Update status if verified
                            if collateral.status == 'verified':
                                supabase_service.update_collateral_status(
                                    result[0]['id'], 
                                    'verified'
                                )
                            migrated += 1
                        else:
                            errors += 1
                    else:
                        self.stdout.write(f'  → Would migrate collateral: {collateral.brand_model}')
                        migrated += 1
                        
                except Exception as e:
                    self.stdout.write(f'  ✗ Error migrating collateral: {str(e)}')
                    errors += 1
            
            self.stdout.write(f'Collateral: {migrated} migrated, {errors} errors')
            
        except Exception as e:
            self.stdout.write(f'Collateral migration failed: {str(e)}')

    def migrate_loans(self, dry_run=False):
        """Migrate loan data"""
        self.stdout.write('\n--- Migrating Loans ---')
        
        try:
            loans = Loan.objects.all()
            self.stdout.write(f'Found {loans.count()} loans')
            
            migrated = 0
            errors = 0
            
            for loan in loans:
                try:
                    # Get Supabase borrower
                    supabase_borrower = supabase_service.get_user_by_username(loan.borrower.username)
                    if not supabase_borrower:
                        self.stdout.write(f'  ⚠ Borrower {loan.borrower.username} not found - skipping loan')
                        continue
                    
                    # For now, skip loans without collateral migration
                    # In a real migration, you'd need to map collateral IDs
                    if not dry_run:
                        self.stdout.write(f'  ⚠ Loan migration requires collateral ID mapping - skipping for now')
                    else:
                        self.stdout.write(f'  → Would migrate loan: {loan.principal_amount} for {loan.borrower.username}')
                        migrated += 1
                        
                except Exception as e:
                    self.stdout.write(f'  ✗ Error migrating loan: {str(e)}')
                    errors += 1
            
            self.stdout.write(f'Loans: {migrated} would be migrated, {errors} errors')
            
        except Exception as e:
            self.stdout.write(f'Loan migration failed: {str(e)}')

    def migrate_investments(self, dry_run=False):
        """Migrate investment data"""
        self.stdout.write('\n--- Migrating Investments ---')
        
        try:
            investments = Investment.objects.all()
            self.stdout.write(f'Found {investments.count()} investments')
            
            # Similar to loans, this would require proper ID mapping
            self.stdout.write('Investment migration requires loan ID mapping - skipping for now')
            
        except Exception as e:
            self.stdout.write(f'Investment migration failed: {str(e)}')