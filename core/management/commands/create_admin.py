from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from core.services import supabase_service
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Create admin user sammyseth260@gmail.com - SERVER ONLY'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm admin user creation',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.ERROR('This command creates an admin user. Use --confirm to proceed.')
            )
            return
        
        admin_email = 'sammyseth260@gmail.com'
        admin_username = 'sammyseth260'
        
        try:
            # Check if admin user already exists in Supabase
            existing_user = supabase_service.get_user_by_email(admin_email)
            if existing_user:
                self.stdout.write(
                    self.style.WARNING(f'Admin user with email {admin_email} already exists in Supabase')
                )
                
                # Update to ensure admin privileges
                update_data = {
                    'role': 'admin',
                    'is_staff': True,
                    'is_superuser': True,
                    'is_promoted_admin': True
                }
                
                result = supabase_service.update_user(existing_user['id'], update_data)
                if result:
                    self.stdout.write(
                        self.style.SUCCESS(f'Admin privileges confirmed for {admin_email}')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR('Failed to update admin privileges')
                    )
                return
            
            # Create new admin user in Supabase
            supabase_result = supabase_service.create_user(
                username=admin_username,
                email=admin_email,
                password='admin123',  # Default password - should be changed
                role='admin',
                phone_number='254700000001',
                national_id='ADMIN001',
                first_name='Sammy',
                last_name='Seth'
            )
            
            if supabase_result:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created admin user: {admin_username}')
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Email: {admin_email}')
                )
                self.stdout.write(
                    self.style.SUCCESS('Default password: admin123')
                )
                self.stdout.write(
                    self.style.WARNING('SECURITY: Change the password after first login!')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('Failed to create admin user in Supabase')
                )
            
        except Exception as e:
            logger.error(f'Error creating admin user: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'Error creating admin user: {str(e)}')
            )