from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Create admin user for P2P Secure-Lend'

    def handle(self, *args, **options):
        admin_email = 'sammyseth260@gmail.com'
        admin_username = 'admin'
        
        try:
            # Check if admin user already exists
            if User.objects.filter(email=admin_email).exists():
                self.stdout.write(
                    self.style.WARNING(f'Admin user with email {admin_email} already exists')
                )
                return
            
            if User.objects.filter(username=admin_username).exists():
                self.stdout.write(
                    self.style.WARNING(f'User with username {admin_username} already exists')
                )
                return
            
            # Create admin user
            admin_user = User.objects.create_user(
                username=admin_username,
                email=admin_email,
                password='admin123',  # Default password
                first_name='System',
                last_name='Administrator'
            )
            
            # Set admin properties
            admin_user.role = 'admin'
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.phone_number = '254700000001'
            admin_user.national_id = 'ADMIN001'
            admin_user.wallet_balance = 0.00
            admin_user.total_earnings = 0.00
            admin_user.commission_rate = 0.00
            admin_user.is_promoted_admin = False
            admin_user.save()
            
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
                self.style.WARNING('Please change the password after first login!')
            )
            
        except Exception as e:
            logger.error(f'Error creating admin user: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'Error creating admin user: {str(e)}')
            )