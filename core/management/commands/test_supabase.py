from django.core.management.base import BaseCommand
from core.services import supabase_service
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test Supabase connection and services'

    def handle(self, *args, **options):
        self.stdout.write('Testing Supabase connection...')
        
        try:
            # Test getting all users
            users = supabase_service.get_all_users()
            if users is not None:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Successfully connected to Supabase')
                )
                self.stdout.write(f'Found {len(users)} users in database')
                
                # Check for admin user
                admin_users = [u for u in users if u.get('role') == 'admin']
                if admin_users:
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Found {len(admin_users)} admin user(s)')
                    )
                    for admin in admin_users:
                        self.stdout.write(f'  - {admin.get("username")} ({admin.get("email")})')
                else:
                    self.stdout.write(
                        self.style.WARNING('⚠ No admin users found')
                    )
                
                # Test user creation (dry run)
                self.stdout.write('\nTesting user lookup...')
                test_user = supabase_service.get_user_by_email('sammyseth260@gmail.com')
                if test_user:
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Found admin user: {test_user.get("username")}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING('⚠ Admin user sammyseth260@gmail.com not found')
                    )
                
            else:
                self.stdout.write(
                    self.style.ERROR('✗ Failed to connect to Supabase')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error testing Supabase: {str(e)}')
            )
            logger.error(f'Supabase test error: {str(e)}')