from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Create admin user sammyseth260@gmail.com'

    def handle(self, *args, **options):
        admin_email = 'sammyseth260@gmail.com'
        admin_username = 'sammyseth260'
        
        try:
            # Try to get existing user by email
            try:
                user = User.objects.get(email=admin_email)
                # Update existing user to admin
                user.role = 'admin'
                user.is_staff = True
                user.is_superuser = True
                user.is_promoted_admin = True
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully updated existing user {admin_email} to admin')
                )
                return
            except User.DoesNotExist:
                pass
            
            # Try to get existing user by username
            try:
                user = User.objects.get(username=admin_username)
                # Update existing user to admin
                user.email = admin_email
                user.role = 'admin'
                user.is_staff = True
                user.is_superuser = True
                user.is_promoted_admin = True
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully updated existing username {admin_username} to admin')
                )
                return
            except User.DoesNotExist:
                pass
            
            # Create new admin user
            admin_user = User.objects.create_user(
                username=admin_username,
                email=admin_email,
                password='admin123',  # Default password
                first_name='Sammy',
                last_name='Seth',
                role='admin',
                phone_number='254700000001',
                national_id='ADMIN001',
                is_staff=True,
                is_superuser=True,
                wallet_balance=0.00,
                total_earnings=0.00,
                commission_rate=0.00,
                is_promoted_admin=True
            )
            
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
            
        except IntegrityError as e:
            self.stdout.write(
                self.style.ERROR(f'Database integrity error: {str(e)}')
            )
            self.stdout.write(
                self.style.ERROR('This usually means the username or email already exists')
            )
        except Exception as e:
            logger.error(f'Error creating admin user: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'Error creating admin user: {str(e)}')
            )