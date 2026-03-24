from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Reset admin password for P2P Secure-Lend'

    def add_arguments(self, parser):
        parser.add_argument('--password', type=str, help='New password for admin user')

    def handle(self, *args, **options):
        admin_email = 'sammyseth260@gmail.com'
        new_password = options.get('password', 'admin123')
        
        try:
            # Find admin user
            admin_user = User.objects.get(email=admin_email)
            
            # Reset password
            admin_user.set_password(new_password)
            admin_user.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully reset password for admin user: {admin_user.username}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'Email: {admin_email}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'New password: {new_password}')
            )
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Admin user with email {admin_email} not found')
            )
        except Exception as e:
            logger.error(f'Error resetting admin password: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'Error resetting admin password: {str(e)}')
            )