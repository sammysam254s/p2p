from django.contrib.auth.backends import ModelBackend, BaseBackend
from django.contrib.auth import get_user_model
from .supabase_client import supabase, user_service
from .services import supabase_service
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class SupabaseAuthBackend(BaseBackend):
    """
    Supabase authentication backend that uses Supabase Auth for login
    and syncs with Django User model for session management
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """Authenticate user using Supabase Auth"""
        if not username or not password:
            return None
        
        try:
            logger.info(f"Attempting Supabase Auth authentication for: {username}")
            
            # Try to authenticate with Supabase Auth first
            try:
                # Use email for Supabase Auth (create temp email if username provided)
                email = username if '@' in username else f"{username}@securelend.temp"
                
                auth_response = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })
                
                if auth_response.user:
                    logger.info(f"Supabase Auth successful for {username}")
                    
                    # Get user from our custom users table
                    supabase_user = supabase_service.get_user_by_username(username)
                    
                    if supabase_user:
                        return self._create_or_update_django_user(username, supabase_user, auth_response.user.id)
                    else:
                        logger.warning(f"User {username} authenticated with Supabase Auth but not found in users table")
                        return None
                        
            except Exception as auth_error:
                logger.info(f"Supabase Auth failed for {username}: {str(auth_error)}")
                
                # Fallback to custom users table authentication
                logger.info(f"Trying fallback authentication for {username}")
                supabase_user = supabase_service.authenticate_user(username, password)
                
                if supabase_user:
                    logger.info(f"Fallback authentication successful for {username}")
                    
                    # Try to create Supabase Auth user for future logins
                    try:
                        email = supabase_user.get('email', f"{username}@securelend.temp")
                        signup_response = supabase.auth.sign_up({
                            "email": email,
                            "password": password
                        })
                        
                        auth_user_id = signup_response.user.id if signup_response.user else None
                        logger.info(f"Created Supabase Auth user for {username}")
                        
                    except Exception as signup_error:
                        logger.warning(f"Could not create Supabase Auth user for {username}: {str(signup_error)}")
                        auth_user_id = None
                    
                    return self._create_or_update_django_user(username, supabase_user, auth_user_id)
                else:
                    logger.warning(f"Both Supabase Auth and fallback authentication failed for {username}")
                    return None
                    
        except Exception as e:
            logger.error(f"Authentication error for {username}: {str(e)}")
            return None
    
    def _create_or_update_django_user(self, username, supabase_user, auth_user_id=None):
        """Create or update Django user with Supabase data"""
        try:
            # Get or create Django user for session management
            django_user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': supabase_user.get('email', ''),
                    'first_name': supabase_user.get('first_name', ''),
                    'last_name': supabase_user.get('last_name', ''),
                    'is_active': supabase_user.get('is_active', True),
                    'is_staff': supabase_user.get('is_staff', False),
                    'is_superuser': supabase_user.get('is_superuser', False),
                }
            )
            
            # Update Django user with latest Supabase data
            if not created:
                django_user.email = supabase_user.get('email', django_user.email)
                django_user.first_name = supabase_user.get('first_name', django_user.first_name)
                django_user.last_name = supabase_user.get('last_name', django_user.last_name)
                django_user.is_active = supabase_user.get('is_active', True)
                django_user.is_staff = supabase_user.get('is_staff', False)
                django_user.is_superuser = supabase_user.get('is_superuser', False)
            
            # Add custom attributes from Supabase
            django_user.role = supabase_user.get('role', 'borrower')
            django_user.phone_number = supabase_user.get('phone_number', '')
            django_user.national_id = supabase_user.get('national_id', '')
            django_user.wallet_balance = supabase_user.get('wallet_balance', 0.0)
            django_user.total_earnings = supabase_user.get('total_earnings', 0.0)
            django_user.commission_rate = supabase_user.get('commission_rate', 0.0)
            django_user.is_promoted_admin = supabase_user.get('is_promoted_admin', False)
            django_user.supabase_id = supabase_user.get('id')
            django_user.supabase_auth_id = auth_user_id
            
            django_user.save()
            
            action = "Created" if created else "Updated"
            logger.info(f"{action} Django user for {username} with Supabase data")
            return django_user
            
        except Exception as e:
            logger.error(f"Error creating/updating Django user for {username}: {str(e)}")
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
        logger.info(f"Django fallback authentication attempt for username: {username}")
        
        try:
            # Try to get the user
            user = User.objects.get(username=username)
            logger.info(f"User found: {user.username}, role: {user.role}, is_active: {user.is_active}")
            
            # Check password
            if user.check_password(password):
                logger.info(f"Password check passed for user: {username}")
                
                # Check if user is active
                if user.is_active:
                    logger.info(f"User {username} authenticated successfully via Django fallback")
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