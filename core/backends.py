from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class CustomAuthBackend(ModelBackend):
    """Custom authentication backend with logging"""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        logger.info(f"Authentication attempt for username: {username}")
        
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
            logger.warning(f"User {username} does not exist")
            return None
        except Exception as e:
            logger.error(f"Authentication error for {username}: {str(e)}")
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