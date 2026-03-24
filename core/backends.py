from django.contrib.auth.backends import ModelBackend, BaseBackend
from django.contrib.auth import get_user_model
from .supabase_client import user_service
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class SupabaseAuthBackend(BaseBackend):
    """Custom authentication backend that uses Supabase"""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """Authenticate user against Supabase"""
        if username is None or password is None:
            return None
        
        try:
            logger.info(f"Attempting Supabase authentication for: {username}")
            
            # Get user from Supabase
            supabase_user = user_service.authenticate_user(username, password)
            if not supabase_user:
                logger.warning(f"Supabase authentication failed for username: {username}")
                return None
            
            logger.info(f"Supabase user found: {username}, role: {supabase_user.get('role')}")
            
            # Create or get Django user for session management
            try:
                django_user = User.objects.get(username=username)
                # Update Django user with Supabase data
                django_user.email = supabase_user.get('email', '')
                django_user.first_name = supabase_user.get('first_name', '')
                django_user.last_name = supabase_user.get('last_name', '')
                django_user.is_active = supabase_user.get('is_active', True)
                django_user.is_staff = supabase_user.get('is_staff', False)
                django_user.is_superuser = supabase_user.get('is_superuser', False)
                
                # Set custom fields
                if hasattr(django_user, 'role'):
                    django_user.role = supabase_user.get('role', 'borrower')
                if hasattr(django_user, 'phone_number'):
                    django_user.phone_number = supabase_user.get('phone_number', '')
                if hasattr(django_user, 'national_id'):
                    django_user.national_id = supabase_user.get('national_id', '')
                if hasattr(django_user, 'wallet_balance'):
                    django_user.wallet_balance = supabase_user.get('wallet_balance', 0.00)
                if hasattr(django_user, 'total_earnings'):
                    django_user.total_earnings = supabase_user.get('total_earnings', 0.00)
                if hasattr(django_user, 'commission_rate'):
                    django_user.commission_rate = supabase_user.get('commission_rate', 0.00)
                if hasattr(django_user, 'is_promoted_admin'):
                    django_user.is_promoted_admin = supabase_user.get('is_promoted_admin', False)
                
                django_user.save()
                logger.info(f"Updated existing Django user: {username}")
                
            except User.DoesNotExist:
                # Create new Django user
                django_user = User(
                    username=username,
                    email=supabase_user.get('email', ''),
                    first_name=supabase_user.get('first_name', ''),
                    last_name=supabase_user.get('last_name', ''),
                    is_active=supabase_user.get('is_active', True),
                    is_staff=supabase_user.get('is_staff', False),
                    is_superuser=supabase_user.get('is_superuser', False)
                )
                
                # Set custom fields
                if hasattr(django_user, 'role'):
                    django_user.role = supabase_user.get('role', 'borrower')
                if hasattr(django_user, 'phone_number'):
                    django_user.phone_number = supabase_user.get('phone_number', '')
                if hasattr(django_user, 'national_id'):
                    django_user.national_id = supabase_user.get('national_id', '')
                if hasattr(django_user, 'wallet_balance'):
                    django_user.wallet_balance = supabase_user.get('wallet_balance', 0.00)
                if hasattr(django_user, 'total_earnings'):
                    django_user.total_earnings = supabase_user.get('total_earnings', 0.00)
                if hasattr(django_user, 'commission_rate'):
                    django_user.commission_rate = supabase_user.get('commission_rate', 0.00)
                if hasattr(django_user, 'is_promoted_admin'):
                    django_user.is_promoted_admin = supabase_user.get('is_promoted_admin', False)
                
                django_user.save()
                logger.info(f"Created new Django user: {username}")
            
            # Store Supabase user ID for reference
            django_user.supabase_id = supabase_user.get('id')
            
            logger.info(f"Successfully authenticated user: {username}")
            return django_user
            
        except Exception as e:
            logger.error(f"Supabase authentication error for {username}: {str(e)}")
            return None
    
    def get_user(self, user_id):
        """Get user by ID"""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class CustomAuthBackend(ModelBackend):
    """Fallback authentication backend for Django admin and local users"""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        logger.info(f"Django authentication attempt for username: {username}")
        
        try:
            # Try to get the user
            user = User.objects.get(username=username)
            logger.info(f"User found: {user.username}, role: {user.role}, is_active: {user.is_active}")
            
            # Check password
            if user.check_password(password):
                logger.info(f"Password check passed for user: {username}")
                
                # Check if user is active
                if user.is_active:
                    logger.info(f"User {username} authenticated successfully")
                    return user
                else:
                    logger.warning(f"User {username} is inactive")
                    return None
            else:
                logger.warning(f"Password check failed for user: {username}")
                return None
                
        except User.DoesNotExist:
            logger.warning(f"User {username} does not exist in Django")
            return None
        except Exception as e:
            logger.error(f"Django authentication error for {username}: {str(e)}")
            return None
    
    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
            logger.debug(f"Retrieved user: {user.username}, role: {user.role}")
            return user
        except User.DoesNotExist:
            logger.warning(f"User with ID {user_id} does not exist")
            return None
        except Exception as e:
            logger.error(f"Error retrieving user {user_id}: {str(e)}")
            return None