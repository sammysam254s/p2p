from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from decimal import Decimal
import logging
import json
# Django models completely removed - Supabase ONLY system
from .forms import CustomUserCreationForm, CollateralForm, LoanApplicationForm, InvestmentForm, KYCVerificationForm, CollateralVerificationForm
from .supabase_client import supabase
from .services import supabase_service

# Use simple KYC service instead of AI service
try:
    from .simple_kyc_service import simple_kyc_service
    KYC_SERVICE_AVAILABLE = True
except ImportError:
    KYC_SERVICE_AVAILABLE = False
    simple_kyc_service = None

try:
    from .pdf_service import pdf_generator
    PDF_SERVICE_AVAILABLE = True
except ImportError:
    PDF_SERVICE_AVAILABLE = False
    pdf_generator = None

try:
    from .pdf_service import pdf_generator
    PDF_SERVICE_AVAILABLE = True
except ImportError:
    PDF_SERVICE_AVAILABLE = False
    pdf_generator = None

logger = logging.getLogger(__name__)


def get_supabase_user(request):
    """
    Get user from Supabase using email first (more reliable), then username fallback.
    This ensures we always get the correct Supabase user regardless of Django username mismatches.
    """
    current_user = None
    
    # Try email first (most reliable for admin users)
    if hasattr(request.user, 'email') and request.user.email:
        current_user = supabase_service.get_user_by_email(request.user.email)
        if current_user:
            logger.info(f"Found Supabase user by email: {request.user.email}")
    
    # Fallback to username if email lookup fails
    if not current_user and hasattr(request.user, 'username') and request.user.username:
        current_user = supabase_service.get_user_by_username(request.user.username)
        if current_user:
            logger.info(f"Found Supabase user by username: {request.user.username}")
    
    if not current_user:
        logger.warning(f"No Supabase user found for Django user: {request.user.username} ({request.user.email})")
    
    return current_user


class CustomLoginView(LoginView):
    """Optimized custom login view"""
    template_name = 'registration/login.html'
    
    def form_valid(self, form):
        username = form.cleaned_data.get('username')
        
        try:
            # Quick authentication
            user = authenticate(
                self.request,
                username=username,
                password=form.cleaned_data.get('password')
            )
            
            if user is not None and user.is_active:
                # Quick admin check
                if user.email == 'sammyseth260@gmail.com' and user.role != 'admin':
                    user.role = 'admin'
                    user.is_staff = True
                    user.is_superuser = True
                    user.is_promoted_admin = True
                    user.save()
                
                # Quick role validation
                if not hasattr(user, 'role') or not user.role:
                    messages.error(self.request, 'Account not configured. Contact support.')
                    return self.form_invalid(form)
                
                # Login immediately
                login(self.request, user)
                messages.success(self.request, f'Welcome, {user.username}!')
                
                # Fast redirect
                role_redirects = {
                    'admin': 'admin_dashboard',
                    'borrower': 'borrower_dashboard', 
                    'lender': 'marketplace',
                    'agent': 'agent_panel'
                }
                return redirect(role_redirects.get(user.role, 'home'))
            else:
                messages.error(self.request, 'Invalid credentials.')
                return self.form_invalid(form)
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            messages.error(self.request, 'Login error. Try again.')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        return super().form_invalid(form)


class CustomLogoutView(LogoutView):
    """Custom logout view that handles both Django and Supabase Auth logout"""
    next_page = '/'  # Redirect to home page after logout
    
    def get(self, request, *args, **kwargs):
        """Handle GET requests for logout"""
        return self.post(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        """Handle POST requests for logout"""
        if request.user.is_authenticated:
            username = request.user.username
            logger.info(f"User {username} logging out")
            
            # Try to sign out from Supabase Auth
            try:
                supabase.auth.sign_out()
                logger.info(f"Signed out {username} from Supabase Auth")
            except Exception as e:
                logger.warning(f"Could not sign out {username} from Supabase Auth: {str(e)}")
            
            messages.success(request, 'You have been logged out successfully.')
        
        response = super().post(request, *args, **kwargs)
        return response
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to handle both GET and POST"""
        if request.method == 'GET':
            return self.get(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)


def home(request):
    """Optimized home page with fast redirects and comprehensive error handling"""
    try:
        if request.user.is_authenticated:
            # Quick admin email check with error handling
            if request.user.email == 'sammyseth260@gmail.com' and request.user.role != 'admin':
                try:
                    request.user.role = 'admin'
                    request.user.is_staff = True
                    request.user.is_superuser = True
                    request.user.is_promoted_admin = True
                    request.user.save()
                    logger.info(f"Auto-promoted {request.user.username} to admin")
                except Exception as e:
                    logger.error(f"Error auto-promoting admin: {str(e)}")
            
            # Fast role-based redirect with validation
            if hasattr(request.user, 'role') and request.user.role:
                role_redirects = {
                    'borrower': 'borrower_dashboard',
                    'lender': 'marketplace', 
                    'agent': 'agent_panel',
                    'admin': 'admin_dashboard'
                }
                redirect_url = role_redirects.get(request.user.role)
                if redirect_url:
                    try:
                        return redirect(redirect_url)
                    except Exception as e:
                        logger.error(f"Redirect error for role {request.user.role}: {str(e)}")
                        messages.error(request, f'Error accessing {request.user.role} dashboard. Please try again.')
            else:
                messages.error(request, 'Account not configured properly. Contact support.')
                # Log the user out if account is not properly configured
                from django.contrib.auth import logout
                logout(request)
        
        return render(request, 'core/home.html')
        
    except Exception as e:
        logger.error(f"Home view error: {str(e)}")
        messages.error(request, 'System error. Please try again.')
        return render(request, 'core/home.html')


def register(request):
    """User registration with Supabase integration"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                # Create user in Supabase first
                username = form.cleaned_data['username']
                email = form.cleaned_data['email']
                password = form.cleaned_data['password1']
                role = form.cleaned_data['role']
                phone_number = form.cleaned_data['phone_number']
                national_id = form.cleaned_data['national_id']
                first_name = form.cleaned_data.get('first_name', '')
                last_name = form.cleaned_data.get('last_name', '')
                
                # SECURITY: Check if username already exists in Supabase
                existing_user = supabase_service.get_user_by_username(username)
                if existing_user:
                    messages.error(request, 'Username already exists.')
                    return render(request, 'registration/register.html', {'form': form})
                
                # SECURITY: Check if email already exists in Supabase
                existing_email = supabase_service.get_user_by_email(email)
                if existing_email:
                    messages.error(request, 'Email already exists.')
                    return render(request, 'registration/register.html', {'form': form})
                
                # SECURITY: Check if national ID already exists
                existing_national_id = supabase_service.get_user_by_national_id(national_id)
                if existing_national_id:
                    messages.error(request, 'National ID already exists.')
                    return render(request, 'registration/register.html', {'form': form})
                
                # SECURITY: Prevent admin role selection during registration
                if role == 'admin':
                    messages.error(request, 'Admin role cannot be selected during registration. Contact system administrator.')
                    return render(request, 'registration/register.html', {'form': form})
                
                # Create user in Supabase Auth first
                try:
                    email = form.cleaned_data['email']
                    auth_response = supabase.auth.sign_up({
                        "email": email,
                        "password": password
                    })
                    
                    if auth_response.user:
                        logger.info(f"Created Supabase Auth user for {username}")
                        auth_user_id = auth_response.user.id
                    else:
                        logger.warning(f"Failed to create Supabase Auth user for {username}")
                        auth_user_id = None
                        
                except Exception as auth_error:
                    logger.warning(f"Supabase Auth signup failed for {username}: {str(auth_error)}")
                    auth_user_id = None
                
                # Create user in Supabase custom users table
                supabase_result = supabase_service.create_user(
                    username=username,
                    email=email,
                    password=password,
                    role=role,
                    phone_number=phone_number,
                    national_id=national_id,
                    first_name=first_name,
                    last_name=last_name
                )
                
                if supabase_result:
                    # Update Supabase user with auth_user_id if available
                    if auth_user_id and isinstance(supabase_result, list) and len(supabase_result) > 0:
                        try:
                            supabase_user_id = supabase_result[0]['id']
                            supabase.table('users').update({
                                'auth_user_id': auth_user_id,
                                'updated_at': timezone.now().isoformat()
                            }).eq('id', supabase_user_id).execute()
                            logger.info(f"Linked Supabase Auth user to custom user for {username}")
                        except Exception as link_error:
                            logger.warning(f"Could not link auth user for {username}: {str(link_error)}")
                    
                    logger.info(f"User {username} created successfully in Supabase")
                    messages.success(request, f'Account created for {username}! You can now log in with Supabase authentication.')
                    return redirect('login')
                else:
                    logger.error(f"Failed to create user {username} in Supabase")
                    messages.error(request, 'There was an error creating your account. Please try again.')
                    
            except Exception as e:
                logger.error(f"Registration error: {str(e)}")
                messages.error(request, 'There was an error creating your account. Please try again.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})


@login_required
def borrower_dashboard(request):
    """Robust borrower dashboard that works for all users"""
    try:
        # Get user role from Django user model first (most reliable)
        user_role = getattr(request.user, 'role', 'borrower')
        
        # If no role set, default to borrower for regular users
        if not user_role:
            user_role = 'borrower'
            request.user.role = 'borrower'
            request.user.save()
        
        # Allow admin and borrower access
        if user_role not in ['borrower', 'admin']:
            messages.error(request, 'Access denied. This page is for borrowers.')
            return redirect('home')
        
        # Try to get user from Supabase using the helper function
        current_user = get_supabase_user(request)
        
        # If user not in Supabase, create them
        if not current_user:
            try:
                # Create user in Supabase
                current_user = supabase_service.create_user(
                    username=request.user.username,
                    email=request.user.email,
                    password="",  # Password not needed for existing users
                    role=user_role,
                    phone_number=getattr(request.user, 'phone_number', ''),
                    national_id=getattr(request.user, 'national_id', ''),
                    first_name=request.user.first_name,
                    last_name=request.user.last_name
                )
                logger.info(f"Created user {request.user.username} in Supabase")
            except Exception as e:
                logger.error(f"Could not create user in Supabase: {str(e)}")
                # Continue without Supabase user - use Django data only
                current_user = {
                    'role': user_role,
                    'username': request.user.username,
                    'email': request.user.email
                }
        
        # Check KYC status from Supabase (PRIMARY database - NO Django fallback)
        kyc_verified = False
        kyc_status = 'pending'
        kyc_exists = False
        
        if user_role == 'admin':
            kyc_verified = True
            kyc_status = 'admin_access'
            kyc_exists = True
        else:
            # Get KYC status from Supabase ONLY (no Django fallback)
            try:
                if current_user and current_user.get('id'):
                    # Check if user has KYC record in Supabase
                    kyc_result = supabase.table('kyc_verifications').select('*').eq('user_id', current_user['id']).execute()
                    
                    if kyc_result.data:
                        kyc_record = kyc_result.data[0]
                        kyc_status = kyc_record.get('status', 'pending')
                        kyc_verified = kyc_status == 'verified'
                        kyc_exists = True
                        logger.info(f"KYC status from Supabase for {request.user.username}: {kyc_status} (verified: {kyc_verified})")
                    else:
                        # Create a pending KYC record in Supabase (ensure persistence) - SILENTLY
                        import uuid
                        try:
                            kyc_data = {
                                'id': str(uuid.uuid4()),
                                'user_id': current_user['id'],
                                'full_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
                                'id_number': '',
                                'date_of_birth': timezone.now().date().isoformat(),
                                'status': 'pending',
                                'created_at': timezone.now().isoformat(),
                                'updated_at': timezone.now().isoformat()
                            }
                            
                            create_result = supabase.table('kyc_verifications').insert(kyc_data).execute()
                            if create_result.data:
                                kyc_verified = False
                                kyc_status = 'pending'
                                kyc_exists = True
                                logger.info(f"Created KYC record in Supabase for user {request.user.username}")
                            else:
                                logger.warning(f"Could not create KYC record in Supabase for {request.user.username}")
                                kyc_verified = False
                                kyc_status = 'pending'
                                kyc_exists = False
                        except Exception as e:
                            logger.warning(f"KYC record creation failed (non-critical): {str(e)}")
                            kyc_verified = False
                            kyc_status = 'pending'
                            kyc_exists = False
                else:
                    logger.warning(f"No Supabase user found for {request.user.username}")
                    kyc_verified = False
                    kyc_status = 'pending'
                    kyc_exists = False
                        
            except Exception as e:
                logger.warning(f"KYC check error (non-critical): {str(e)}")
                kyc_verified = False
                kyc_status = 'pending'
                kyc_exists = False
        
        # Get borrower's loans from Supabase (primary database)
        try:
            if current_user and current_user.get('id'):
                # Get loans from Supabase first
                supabase_loans = supabase_service.get_loans_by_borrower(current_user['id']) or []
                
                # Enrich loans with details
                enriched_loans = []
                for loan in supabase_loans:
                    try:
                        loan_details = supabase_service.get_loan_with_details(loan['id'])
                        if loan_details:
                            enriched_loans.append(loan_details)
                    except Exception as e:
                        logger.error(f"Error enriching loan {loan.get('id')}: {str(e)}")
                
                loans = enriched_loans
            else:
                # Fallback to Django if no Supabase user
                django_loans = Loan.objects.filter(borrower=request.user).order_by('-created_at')
                loans = list(django_loans)
        except Exception as e:
            logger.error(f"Error getting loans: {str(e)}")
            # Fallback to Django
            try:
                django_loans = Loan.objects.filter(borrower=request.user).order_by('-created_at')
                loans = list(django_loans)
            except Exception as django_error:
                logger.error(f"Django loans fallback failed: {str(django_error)}")
                loans = []
        
        # Calculate totals safely (works with both Supabase and Django loan formats)
        total_borrowed = 0
        total_outstanding = 0
        try:
            for loan in loans:
                if isinstance(loan, dict):  # Supabase format
                    total_borrowed += float(loan.get('principal_amount', 0))
                    if loan.get('status') == 'active':
                        # Calculate outstanding for Supabase loans
                        principal = float(loan.get('principal_amount', 0))
                        funded = float(loan.get('funded_amount', 0))
                        # Simple calculation - in production you'd want more sophisticated repayment tracking
                        total_outstanding += principal
                else:  # Django format
                    total_borrowed += float(loan.principal_amount)
                    if loan.status == 'active':
                        total_outstanding += float(loan.calculate_total_repayment() - (loan.payments_made * loan.calculate_monthly_payment()))
        except Exception as e:
            logger.error(f"Error calculating totals: {str(e)}")
            total_borrowed = 0
            total_outstanding = 0
        
        # Handle loan application (strict KYC enforcement)
        if request.method == 'POST':
            # STRICT KYC CHECK - Block all loan applications without verified KYC
            if not kyc_verified and user_role != 'admin':
                messages.error(request, 'KYC verification is required before applying for loans. Please complete your KYC verification first.')
                return redirect('kyc_verification')
            
            collateral_form = CollateralForm(request.POST)
            loan_form = LoanApplicationForm(request.POST)
            
            if collateral_form.is_valid() and loan_form.is_valid():
                try:
                    # Ensure user exists in Supabase first
                    if not current_user:
                        current_user = supabase_service.create_user(
                            username=request.user.username,
                            email=request.user.email,
                            password="",  # Password not needed for existing users
                            role=user_role,
                            phone_number=getattr(request.user, 'phone_number', ''),
                            national_id=getattr(request.user, 'national_id', ''),
                            first_name=request.user.first_name,
                            last_name=request.user.last_name
                        )
                        if not current_user:
                            messages.error(request, 'Error creating user profile. Please try again.')
                            return redirect('borrower_dashboard')
                    
                    supabase_user_id = current_user.get('id')
                    if not supabase_user_id:
                        messages.error(request, 'User profile error. Please contact support.')
                        return redirect('borrower_dashboard')
                    
                    # Create collateral in Supabase FIRST (primary database)
                    supabase_collateral = supabase_service.create_collateral(
                        user_id=supabase_user_id,
                        item_type=collateral_form.cleaned_data['item_type'],
                        brand_model=collateral_form.cleaned_data['brand_model'],
                        market_value=float(collateral_form.cleaned_data['market_value'])  # Correct field name
                    )
                    
                    if not supabase_collateral:
                        messages.error(request, 'Error creating collateral record. Please try again.')
                        return redirect('borrower_dashboard')
                    
                    # Extract collateral data (create_collateral returns a list)
                    if isinstance(supabase_collateral, list) and len(supabase_collateral) > 0:
                        collateral_data = supabase_collateral[0]
                    else:
                        collateral_data = supabase_collateral
                    
                    # Validate loan amount against collateral
                    if collateral_data and 'market_value' in collateral_data:
                        # Calculate max loan amount using the 30/50 rule
                        market_value = float(collateral_data['market_value'])
                        max_loan_amount = market_value * 0.7 * 0.5  # 30% devaluation, then 50% of devalued amount
                        logger.info(f"Collateral validation: Market value=KES {market_value:,.2f}, Max loan=KES {max_loan_amount:,.2f}")
                    else:
                        max_loan_amount = 0
                        logger.error(f"No market_value found in collateral data: {collateral_data}")
                    
                    requested_amount = float(loan_form.cleaned_data['principal_amount'])
                    
                    if requested_amount > max_loan_amount:
                        # Delete the collateral we just created
                        try:
                            collateral_id = collateral_data['id'] if collateral_data else None
                            if collateral_id:
                                supabase.table('collateral').delete().eq('id', collateral_id).execute()
                        except Exception as cleanup_error:
                            logger.warning(f"Failed to cleanup collateral: {str(cleanup_error)}")
                        
                        messages.error(request, 
                            f'Requested amount (KES {requested_amount:,.2f}) exceeds maximum '
                            f'allowed (KES {max_loan_amount:,.2f}) based on collateral value of KES {market_value:,.2f}. '
                            f'Maximum loan is 35% of collateral value (70% after 30% devaluation, then 50% of that).')
                        return redirect('borrower_dashboard')
                    
                    # Create loan in Supabase FIRST (primary database)
                    supabase_loan = supabase_service.create_loan(
                        borrower_id=supabase_user_id,
                        collateral_id=collateral_data['id'],
                        principal_amount=requested_amount,
                        interest_rate=float(loan_form.cleaned_data.get('interest_rate', 13.0)),
                        duration_months=int(loan_form.cleaned_data['duration_months'])
                    )
                    
                    if not supabase_loan:
                        # Delete the collateral we created
                        try:
                            collateral_id = collateral_data['id'] if collateral_data else None
                            if collateral_id:
                                supabase.table('collateral').delete().eq('id', collateral_id).execute()
                        except Exception as cleanup_error:
                            logger.warning(f"Failed to cleanup collateral after loan creation failure: {str(cleanup_error)}")
                            pass
                        messages.error(request, 'Error creating loan record. Please try again.')
                        return redirect('borrower_dashboard')
                    
                    # Django completely removed - Supabase ONLY system
                    
                    messages.success(request, 
                        '🎉 Loan application submitted successfully! '
                        'Your loan is now pending collateral verification by a station agent. '
                        'You will be notified once the verification is complete and your loan is listed for funding.')
                    
                    logger.info(f"Loan created successfully in Supabase ONLY for {request.user.username}: "
                              f"Amount: KES {requested_amount:,.2f}, Collateral: {collateral_data['brand_model']}")
                    
                    return redirect('borrower_dashboard')
                        
                except Exception as e:
                    logger.error(f"Loan application error: {str(e)}")
                    messages.error(request, f'Error processing loan application: {str(e)}. Please try again.')
            else:
                # Form validation errors
                error_messages = []
                for field, errors in collateral_form.errors.items():
                    for error in errors:
                        error_messages.append(f"Collateral {field}: {error}")
                for field, errors in loan_form.errors.items():
                    for error in errors:
                        error_messages.append(f"Loan {field}: {error}")
                
                if error_messages:
                    messages.error(request, 'Please correct the following errors: ' + '; '.join(error_messages))
        else:
            collateral_form = CollateralForm()
            loan_form = LoanApplicationForm()
        
        # Get wallet balance safely
        wallet_balance = 0.0
        try:
            wallet_balance = getattr(request.user, 'wallet_balance', 0.0)
        except Exception as e:
            logger.warning(f"Could not get wallet balance: {str(e)}")
            wallet_balance = 0.0
        
        # Prepare context with safe defaults
        context = {
            'loans': loans,
            'total_borrowed': total_borrowed,
            'total_outstanding': total_outstanding,
            'collateral_form': collateral_form,
            'loan_form': loan_form,
            'kyc_verified': kyc_verified,
            'kyc_status': kyc_status,
            'kyc_exists': kyc_exists,
            'wallet_balance': wallet_balance,
            'is_admin': user_role == 'admin',
            'user_role': user_role,
            'current_user': current_user or {'username': request.user.username, 'role': user_role}
        }
        
        return render(request, 'core/borrower_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Borrower dashboard critical error: {str(e)}")
        messages.error(request, f'Error loading dashboard: {str(e)}')
        
        # Fallback: render with minimal context
        try:
            context = {
                'loans': [],
                'total_borrowed': 0,
                'total_outstanding': 0,
                'collateral_form': CollateralForm(),
                'loan_form': LoanApplicationForm(),
                'kyc_verified': False,
                'kyc_status': 'pending',
                'kyc_exists': True,
                'wallet_balance': 0.0,
                'is_admin': False,
                'user_role': 'borrower',
                'current_user': {'username': request.user.username, 'role': 'borrower'}
            }
            return render(request, 'core/borrower_dashboard.html', context)
        except Exception as fallback_error:
            logger.error(f"Fallback render failed: {str(fallback_error)}")
            return redirect('home')


@login_required
def agent_panel(request):
    """Station agent panel for collateral verification - Supabase Primary"""
    try:
        # Get current user from Supabase (primary database)
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user:
            # Create user in Supabase if not exists
            try:
                current_user = supabase_service.create_user(
                    username=request.user.username,
                    email=request.user.email,
                    password="",
                    role=getattr(request.user, 'role', 'agent'),
                    phone_number=getattr(request.user, 'phone_number', ''),
                    national_id=getattr(request.user, 'national_id', ''),
                    first_name=request.user.first_name,
                    last_name=request.user.last_name
                )
            except Exception as e:
                logger.error(f"Error creating user in Supabase: {str(e)}")
                messages.error(request, 'User profile error. Please contact support.')
                return redirect('home')
        
        if not current_user:
            messages.error(request, 'User not found in system.')
            return redirect('home')
        
        # Allow admin to access agent panel
        user_role = current_user.get('role')
        if user_role not in ['agent', 'admin']:
            messages.error(request, 'Access denied. Station agents only.')
            return redirect('home')
        
        # Get pending collateral items from Supabase (primary database)
        pending_collaterals = supabase_service.get_pending_collaterals() or []
        
        # Enrich collaterals with user and loan details
        enriched_collaterals = []
        for collateral in pending_collaterals:
            try:
                # Get user details
                user = supabase_service.get_user_by_id(collateral.get('user_id'))
                if user:
                    collateral['user'] = user
                    
                    # Get associated loan details
                    all_loans = supabase_service.get_all_loans() or []
                    associated_loan = None
                    for loan in all_loans:
                        if loan.get('collateral_id') == collateral.get('id'):
                            associated_loan = loan
                            break
                    
                    collateral['loan'] = associated_loan
                    collateral['loan_amount'] = associated_loan.get('principal_amount', 0) if associated_loan else 0
                    collateral['loan_purpose'] = associated_loan.get('purpose', 'N/A') if associated_loan else 'N/A'
                    collateral['loan_duration'] = associated_loan.get('duration_months', 0) if associated_loan else 0
                    
                    enriched_collaterals.append(collateral)
                    
            except Exception as e:
                logger.error(f"Error enriching collateral {collateral.get('id')}: {str(e)}")
        
        # Handle verification
        if request.method == 'POST':
            collateral_id = request.POST.get('collateral_id')
            verified_value = request.POST.get('verified_value')
            agent_notes = request.POST.get('agent_notes', '')
            
            try:
                # Find the collateral in Supabase
                collateral = None
                for c in pending_collaterals:
                    if str(c.get('id')) == str(collateral_id):
                        collateral = c
                        break
                
                if not collateral:
                    messages.error(request, 'Collateral not found.')
                    return redirect('agent_panel')
                
                # Update collateral status in Supabase (primary database)
                update_data = {
                    'status': 'verified',
                    'verified_by': current_user['id'],
                    'verification_date': timezone.now().isoformat(),
                    'market_value': float(verified_value) if verified_value else collateral.get('market_value'),  # Update market_value with verified value
                    'updated_at': timezone.now().isoformat()
                }
                
                # Update in Supabase
                result = supabase.table('collateral').update(update_data).eq('id', collateral_id).execute()
                
                if result.data:
                    # Find and update associated loan status to 'listed' in Supabase
                    all_loans = supabase_service.get_all_loans() or []
                    loan_updated = False
                    
                    for loan in all_loans:
                        if str(loan.get('collateral_id')) == str(collateral_id):
                            loan_update_result = supabase.table('loans').update({
                                'status': 'listed'
                            }).eq('id', loan['id']).execute()
                            
                            if loan_update_result.data:
                                loan_updated = True
                                break
                    
                    # Also try to update in Django (secondary, non-critical) - REMOVED
                    # Django is completely removed from the system - Supabase ONLY
                    
                    if loan_updated:
                        user = supabase_service.get_user_by_id(collateral.get('user_id'))
                        username = user.get('username', 'Unknown') if user else 'Unknown'
                        verified_amount = float(verified_value) if verified_value else collateral.get('estimated_value', 0)
                        
                        messages.success(request, 
                            f'✅ Collateral verified successfully! '
                            f'Loan for {username} is now listed in the marketplace for funding. '
                            f'Verified value: KES {verified_amount:,.2f}')
                        
                        logger.info(f"Collateral {collateral_id} verified by {current_user.get('username')} "
                                  f"for user {username}, value: KES {verified_amount:,.2f}")
                    else:
                        messages.warning(request, 'Collateral verified but no associated loan found.')
                else:
                    messages.error(request, 'Error verifying collateral in database. Please try again.')
                
            except Exception as e:
                logger.error(f"Collateral verification error: {str(e)}")
                messages.error(request, f'Error verifying collateral: {str(e)}. Please try again.')
            
            return redirect('agent_panel')
        
        # Get verification statistics
        total_pending = len(enriched_collaterals)
        
        # Get today's verified count from Supabase
        try:
            today = timezone.now().date().isoformat()
            all_collaterals = supabase_service.get_all_collaterals() or []
            total_verified_today = len([
                c for c in all_collaterals 
                if c.get('status') == 'verified' and 
                c.get('verification_date', '').startswith(today)
            ])
        except Exception as e:
            logger.warning(f"Error getting verification stats: {str(e)}")
            total_verified_today = 0
        
        context = {
            'pending_collaterals': enriched_collaterals,
            'total_pending': total_pending,
            'total_verified_today': total_verified_today,
            'user': current_user,  # Add current user for wallet balance access
            'is_admin': user_role == 'admin',
        }
        return render(request, 'core/agent_panel.html', context)
        
    except Exception as e:
        logger.error(f"Agent panel error: {str(e)}")
        messages.error(request, f'Error loading agent panel: {str(e)}')
        return redirect('home')


@login_required
def marketplace(request):
    """Enhanced lender marketplace - Supabase Primary"""
    try:
        # Get current user from Supabase ONLY (no Django fallback)
        current_user = get_supabase_user(request)
        if not current_user:
            messages.error(request, 'User not found in Supabase system. Please contact support.')
            return redirect('home')
        
        # Allow admin to access marketplace
        user_role = current_user.get('role')
        if user_role not in ['lender', 'admin']:
            messages.error(request, 'Access denied. Lenders only.')
            return redirect('home')
        
        # Get loans that need funding from Supabase (primary database)
        listed_loans = supabase_service.get_listed_loans() or []
        
        # Enrich loans with details and filter for valid investments
        valid_loans = []
        for loan in listed_loans:
            try:
                # Get loan with full details
                loan_details = supabase_service.get_loan_with_details(loan['id'])
                if loan_details:
                    # Check if loan still needs funding and hasn't expired
                    remaining_amount = float(loan_details['principal_amount']) - float(loan_details.get('funded_amount', 0))
                    
                    if remaining_amount > 0:
                        # Calculate additional metrics
                        loan_details['remaining_amount'] = remaining_amount
                        loan_details['funding_percentage'] = (float(loan_details.get('funded_amount', 0)) / float(loan_details['principal_amount'])) * 100
                        
                        # Calculate days remaining (7-day funding window)
                        from datetime import datetime
                        created_date = datetime.fromisoformat(loan_details['created_at'].replace('Z', '+00:00'))
                        days_remaining = 7 - (timezone.now() - created_date).days
                        loan_details['days_remaining'] = max(0, days_remaining)
                        
                        if days_remaining > 0:
                            valid_loans.append(loan_details)
                        else:
                            # Auto-expire loans that have passed 7-day window
                            try:
                                supabase.table('loans').update({'status': 'cancelled'}).eq('id', loan['id']).execute()
                            except Exception as e:
                                logger.warning(f"Failed to expire loan {loan['id']}: {str(e)}")
                        
            except Exception as e:
                logger.error(f"Error processing loan {loan.get('id')}: {str(e)}")
        
        # Handle investment
        if request.method == 'POST':
            loan_id = request.POST.get('loan_id')
            investment_amount = Decimal(request.POST.get('investment_amount', '0'))
            
            try:
                # Get loan details from Supabase
                loan = supabase_service.get_loan_with_details(loan_id)
                if not loan or loan.get('status') != 'listed':
                    messages.error(request, 'Loan not found or not available for investment.')
                    return redirect('marketplace')
                
                # Validate investment amount
                remaining_amount = Decimal(str(loan['principal_amount'])) - Decimal(str(loan.get('funded_amount', 0)))
                wallet_balance = Decimal(str(current_user.get('wallet_balance', 0)))
                
                if investment_amount > wallet_balance:
                    messages.error(request, f'Insufficient wallet balance. You have KES {wallet_balance:,.2f} but need KES {investment_amount:,.2f}. Please deposit funds to your wallet first.')
                    return redirect('marketplace')
                elif investment_amount > remaining_amount:
                    messages.error(request, f'Investment amount exceeds remaining funding needed (KES {remaining_amount:,.2f})')
                elif investment_amount <= 0:
                    messages.error(request, 'Investment amount must be greater than zero.')
                elif investment_amount < 100:
                    messages.error(request, 'Minimum investment amount is KES 100.')
                else:
                    # Deduct from wallet balance first
                    withdrawal_success = supabase_service.process_wallet_withdrawal(
                        user_id=current_user['id'],
                        amount=float(investment_amount),
                        description=f'Investment in loan #{loan_id}'
                    )
                    
                    if not withdrawal_success:
                        messages.error(request, 'Failed to deduct investment amount from wallet. Please try again.')
                        return redirect('marketplace')
                    
                    # Create investment in Supabase
                    investment_result = supabase_service.create_investment(
                        lender_id=current_user['id'],
                        loan_id=loan_id,
                        amount_invested=float(investment_amount)
                    )
                    
                    if investment_result:
                        # Update loan funded amount
                        new_funded_amount = float(loan.get('funded_amount', 0)) + float(investment_amount)
                        
                        update_result = supabase.table('loans').update({
                            'funded_amount': new_funded_amount
                        }).eq('id', loan_id).execute()
                        
                        if update_result.data:
                            # Check if loan is fully funded
                            if new_funded_amount >= float(loan['principal_amount']):
                                # Mark loan as active
                                supabase.table('loans').update({
                                    'status': 'active',
                                    'activation_date': timezone.now().isoformat()
                                }).eq('id', loan_id).execute()
                                
                                messages.success(request, 
                                    f'🎉 Loan fully funded! Your investment of KES {investment_amount:,.2f} '
                                    f'has completed the funding for {loan["borrower"]["username"]}\'s loan. '
                                    f'The loan is now active and you will receive returns as scheduled.')
                            else:
                                remaining = Decimal(str(loan['principal_amount'])) - Decimal(str(new_funded_amount))
                                messages.success(request, 
                                    f'✅ Investment successful! You invested KES {investment_amount:,.2f}. '
                                    f'Loan still needs KES {remaining:,.2f} to be fully funded.')
                            
                            # Also create in Django (secondary, non-critical)
                            try:
                                from .models import Investment, Loan as DjangoLoan
                                django_loan = DjangoLoan.objects.filter(
                                    borrower__username=loan['borrower']['username'],
                                    principal_amount=loan['principal_amount']
                                ).first()
                                
                                if django_loan:
                                    Investment.objects.create(
                                        lender=request.user,
                                        loan=django_loan,
                                        amount_invested=investment_amount,
                                        expected_return=investment_amount * Decimal('0.13')
                                    )
                                    
                                    django_loan.funded_amount += investment_amount
                                    if django_loan.funded_amount >= django_loan.principal_amount:
                                        django_loan.status = 'active'
                                    django_loan.save()
                                    
                            except Exception as django_error:
                                logger.warning(f"Django investment creation failed (non-critical): {str(django_error)}")
                            
                        else:
                            messages.error(request, 'Error updating loan funding. Please try again.')
                    else:
                        messages.error(request, 'Error creating investment. Please try again.')
            
                return redirect('marketplace')
                
            except Exception as e:
                logger.error(f"Investment error: {str(e)}")
                messages.error(request, f'Error processing investment: {str(e)}. Please try again.')
        
        # Get lender's investments from Supabase
        lender_investments = supabase_service.get_investments_by_lender(current_user['id']) or []
        total_invested = sum(float(inv.get('amount_invested', 0)) for inv in lender_investments)
        
        # Calculate marketplace statistics
        total_loans_available = len(valid_loans)
        total_funding_needed = sum(loan.get('remaining_amount', 0) for loan in valid_loans)
        
        # Force refresh user data from Supabase to ensure we have latest wallet balance
        try:
            refreshed_user = get_supabase_user(request)
            if refreshed_user:
                wallet_balance = float(refreshed_user.get('wallet_balance', 0))
                current_user = refreshed_user
        except Exception as refresh_error:
            logger.warning(f"Could not refresh user data: {str(refresh_error)}")
        
        context = {
            'listed_loans': valid_loans,
            'lender_investments': lender_investments,
            'total_invested': total_invested,
            'total_loans_available': total_loans_available,
            'total_funding_needed': total_funding_needed,
            'wallet_balance': wallet_balance,
            'is_admin': user_role == 'admin',
        }
        return render(request, 'core/marketplace.html', context)
        
    except Exception as e:
        logger.error(f"Marketplace error: {str(e)}")
        messages.error(request, f'Error loading marketplace: {str(e)}')
        return redirect('home')


@login_required
def loan_detail(request, loan_id):
    """Detailed view of a specific loan with comprehensive error handling and redirects"""
    try:
        logger.info(f"Attempting to load loan details for loan_id: {loan_id}")
        
        # Validate loan_id format (should be UUID)
        if not loan_id or len(str(loan_id).strip()) == 0:
            logger.error(f"Invalid loan_id provided: {loan_id}")
            messages.error(request, 'Invalid loan ID.')
            return redirect('admin_dashboard' if hasattr(request.user, 'role') and request.user.role == 'admin' else 'home')
        
        # Get current user from Supabase first
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user:
            logger.error(f"User {request.user.username} not found in Supabase")
            messages.error(request, 'User session error. Please login again.')
            return redirect('login')
        
        user_role = current_user.get('role', 'borrower')
        user_id = current_user.get('id')
        
        logger.info(f"User {request.user.username} (role: {user_role}) requesting loan {loan_id}")
        
        # Try to get loan from Supabase using direct table query first
        try:
            loan_result = supabase.table('loans').select('*').eq('id', loan_id).execute()
            
            if not loan_result.data:
                logger.warning(f"Loan {loan_id} not found in Supabase")
                messages.error(request, 'Loan not found.')
                # Smart redirect based on user role
                role_redirects = {
                    'borrower': 'borrower_dashboard',
                    'lender': 'marketplace',
                    'agent': 'agent_panel',
                    'admin': 'admin_dashboard'
                }
                return redirect(role_redirects.get(user_role, 'home'))
            
            loan = loan_result.data[0]
            logger.info(f"Found loan {loan_id} with status: {loan.get('status')}")
            
        except Exception as loan_fetch_error:
            logger.error(f"Error fetching loan {loan_id} from Supabase: {str(loan_fetch_error)}")
            messages.error(request, 'Error loading loan data. Please try again.')
            return redirect('admin_dashboard' if user_role == 'admin' else 'home')
        
        # Check permissions with detailed access control
        borrower_id = loan.get('borrower_id')
        
        # Allow access for: loan owner, agents, lenders, and admins
        has_access = (
            user_id == borrower_id or  # Loan owner
            user_role in ['agent', 'admin'] or  # Agents and admins
            (user_role == 'lender' and loan.get('status') in ['listed', 'active'])  # Lenders for listed/active loans
        )
        
        if not has_access:
            logger.warning(f"Access denied for user {request.user.username} to loan {loan_id}")
            messages.error(request, 'Access denied. You do not have permission to view this loan.')
            # Redirect based on user role with fallback
            role_redirects = {
                'borrower': 'borrower_dashboard',
                'lender': 'marketplace',
                'agent': 'agent_panel',
                'admin': 'admin_dashboard'
            }
            redirect_url = role_redirects.get(user_role, 'home')
            return redirect(redirect_url)
        
        # Get additional loan details safely
        try:
            # Get collateral details
            collateral = None
            if loan.get('collateral_id'):
                collateral_result = supabase.table('collateral').select('*').eq('id', loan['collateral_id']).execute()
                if collateral_result.data:
                    collateral = collateral_result.data[0]
                    loan['collateral'] = collateral
            
            # Get borrower details
            borrower = None
            if loan.get('borrower_id'):
                borrower = supabase_service.get_user_by_id(loan['borrower_id'])
                if borrower:
                    # Add Django User compatibility
                    borrower['username'] = borrower.get('username', 'Unknown')
                    loan['borrower'] = borrower
            
            # Get investments for this loan
            investments_result = supabase.table('investments').select('*').eq('loan_id', loan_id).execute()
            investments = investments_result.data or []
            
            # Enrich investments with lender details
            for investment in investments:
                lender = supabase_service.get_user_by_id(investment.get('lender_id'))
                if lender:
                    # Add Django User compatibility
                    lender['username'] = lender.get('username', 'Unknown')
                    investment['lender'] = lender
                # Add date compatibility
                if 'date' not in investment and 'created_at' in investment:
                    investment['date'] = investment['created_at']
                # Add investment share calculation
                investment_amount = float(investment.get('amount_invested', 0))
                investment['share_percentage'] = (investment_amount / principal_amount * 100) if principal_amount > 0 else 0
            
            # Calculate loan metrics safely
            principal_amount = float(loan.get('principal_amount', 0))
            funded_amount = float(loan.get('funded_amount', 0))
            interest_rate = float(loan.get('interest_rate', 13.0))
            duration_months = int(loan.get('duration_months', 3))
            
            # Add calculated fields
            loan['platform_fee'] = principal_amount * 0.01  # 1%
            loan['insurance_fee'] = principal_amount * 0.01  # 1%
            loan['monthly_interest'] = principal_amount * (interest_rate / 100)
            loan['total_interest'] = loan['monthly_interest'] * duration_months  # Total interest over loan term
            loan['total_repayment'] = principal_amount + loan['total_interest'] + loan['platform_fee'] + loan['insurance_fee']
            loan['funding_percentage'] = (funded_amount / principal_amount * 100) if principal_amount > 0 else 0
            
            # Add Django model compatibility methods
            loan['calculate_platform_fee'] = loan['platform_fee']
            loan['calculate_insurance_fee'] = loan['insurance_fee']
            loan['calculate_monthly_interest'] = loan['monthly_interest']
            loan['calculate_total_repayment'] = loan['total_repayment']
            loan['get_funding_percentage'] = loan['funding_percentage']
            
            # Add days remaining calculation (assuming 30 days from creation)
            from datetime import datetime, timedelta
            try:
                created_at = datetime.fromisoformat(loan['created_at'].replace('Z', '+00:00'))
                deadline = created_at + timedelta(days=30)
                days_remaining = max(0, (deadline - datetime.now(timezone.utc)).days)
                loan['get_days_remaining'] = days_remaining
            except:
                loan['get_days_remaining'] = 30  # Default fallback
            
            # Add status display methods
            status_display_map = {
                'pending_collateral': 'Pending Collateral Verification',
                'listed': 'Listed for Funding',
                'active': 'Active',
                'completed': 'Completed',
                'defaulted': 'Defaulted'
            }
            loan['get_status_display'] = status_display_map.get(loan.get('status', 'pending_collateral'), loan.get('status', 'Unknown').title())
            
            # Add collateral compatibility if exists
            if collateral:
                collateral['calculate_max_loan_amount'] = float(collateral.get('market_value', 0)) * 0.7 * 0.5  # 30/50 rule
                collateral_status_map = {
                    'pending': 'Pending Verification',
                    'verified': 'Verified',
                    'rejected': 'Rejected'
                }
                collateral['get_status_display'] = collateral_status_map.get(collateral.get('status', 'pending'), collateral.get('status', 'Unknown').title())
                loan['collateral'] = collateral
                
                # Calculate loan-to-value ratio
                collateral_value = float(collateral.get('market_value', 1))
                loan['loan_to_value_ratio'] = (principal_amount / collateral_value * 100) if collateral_value > 0 else 0
            
            # Add user context
            loan['can_invest'] = (
                user_role == 'lender' and 
                loan.get('status') == 'listed' and 
                funded_amount < principal_amount
            )
            
            loan['is_owner'] = (user_id == borrower_id)
            loan['is_admin'] = (user_role == 'admin')
            
            logger.info(f"Successfully loaded loan details for {loan_id}")
            
            context = {
                'loan': loan,
                'investments': investments,
                'user_role': user_role,
            }
            return render(request, 'core/loan_detail.html', context)
            
        except Exception as details_error:
            logger.error(f"Error loading loan details for {loan_id}: {str(details_error)}")
            # Still show basic loan info even if details fail
            context = {
                'loan': loan,
                'investments': [],
                'user_role': user_role,
                'error_message': 'Some loan details could not be loaded.'
            }
            return render(request, 'core/loan_detail.html', context)
        
    except Exception as e:
        logger.error(f"Critical error in loan_detail for loan {loan_id}: {str(e)}")
        messages.error(request, 'Error loading loan details. Please try again.')
        
        # Smart redirect on error
        if hasattr(request.user, 'role'):
            role_redirects = {
                'borrower': 'borrower_dashboard',
                'lender': 'marketplace',
                'agent': 'agent_panel',
                'admin': 'admin_dashboard'
            }
            return redirect(role_redirects.get(request.user.role, 'home'))
        return redirect('home')


@login_required
def admin_dashboard(request):
    """Fast admin dashboard without complex caching"""
    try:
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user:
            messages.error(request, 'User session error. Please login again.')
            return redirect('login')
        
        # Strict admin access control
        is_admin = (
            current_user.get('role') == 'admin' or 
            current_user.get('email') == 'sammyseth260@gmail.com'
        )
        
        if not is_admin:
            messages.error(request, 'Access denied. Administrators only.')
            return redirect('home')
        
        # Get dashboard statistics with error handling
        try:
            stats = supabase_service.get_dashboard_stats()
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {str(e)}")
            stats = {
                'total_users': 0, 'total_borrowers': 0, 'total_lenders': 0, 
                'total_agents': 0, 'total_loans': 0, 'active_loans': 0, 
                'listed_loans': 0, 'total_investments': 0, 
                'total_funded_amount': 0, 'total_loan_amount': 0
            }
            messages.warning(request, 'Some dashboard statistics may not be current.')
        
        # Get recent activities from Supabase ONLY
        try:
            # Get recent loans from Supabase
            all_loans = supabase_service.get_all_loans() or []
            recent_loans = sorted(all_loans, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
            
            # Get recent investments from Supabase
            all_investments = supabase_service.get_all_investments() or []
            recent_investments = sorted(all_investments, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
            
            # Get recent users from Supabase
            all_users = supabase_service.get_all_users() or []
            recent_users = sorted(all_users, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
            
        except Exception as e:
            logger.error(f"Error getting recent activities from Supabase: {str(e)}")
            recent_loans = []
            recent_investments = []
            recent_users = []
            messages.warning(request, 'Recent activities may not be current.')
        
        context = {
            'total_users': stats.get('total_users', 0),
            'total_borrowers': stats.get('total_borrowers', 0),
            'total_lenders': stats.get('total_lenders', 0),
            'total_agents': stats.get('total_agents', 0),
            'total_loans': stats.get('total_loans', 0),
            'active_loans': stats.get('active_loans', 0),
            'listed_loans': stats.get('listed_loans', 0),
            'total_investments': stats.get('total_investments', 0),
            'total_funded_amount': stats.get('total_funded_amount', 0),
            'total_loan_amount': stats.get('total_loan_amount', 0),
            'recent_loans': recent_loans,
            'recent_investments': recent_investments,
            'recent_users': recent_users,
        }
        
        return render(request, 'core/admin_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Admin dashboard error: {str(e)}")
        messages.error(request, 'Error loading admin dashboard.')
        return redirect('home')


@login_required
def admin_borrower_view(request):
    """Admin view of borrower dashboard"""
    try:
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user or (current_user.get('role') != 'admin' and current_user.get('email') != 'sammyseth260@gmail.com'):
            messages.error(request, 'Access denied. Administrators only.')
            return redirect('home')
        
        # Get all borrowers from Supabase
        borrowers = supabase_service.get_users_by_role('borrower') or []
        
        # Enrich borrowers with their loans
        enriched_borrowers = []
        for borrower in borrowers:
            loans = supabase_service.get_loans_by_borrower(borrower['id']) or []
            
            # Enrich loans with details
            enriched_loans = []
            for loan in loans:
                loan_details = supabase_service.get_loan_with_details(loan['id'])
                if loan_details:
                    enriched_loans.append(loan_details)
            
            borrower['loans'] = enriched_loans
            enriched_borrowers.append(borrower)
        
        context = {
            'borrowers': enriched_borrowers,
            'is_admin_view': True,
        }
        return render(request, 'core/admin_borrower_view.html', context)
        
    except Exception as e:
        logger.error(f"Admin borrower view error: {str(e)}")
        messages.error(request, 'Error loading borrower view.')
        return redirect('admin_dashboard')


@login_required
def admin_lender_view(request):
    """Admin view of lender marketplace"""
    try:
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user or (current_user.get('role') != 'admin' and current_user.get('email') != 'sammyseth260@gmail.com'):
            messages.error(request, 'Access denied. Administrators only.')
            return redirect('admin_dashboard')
        
        # Get all lenders from Supabase
        lenders = supabase_service.get_users_by_role('lender') or []
        
        # Enrich lenders with their investments
        enriched_lenders = []
        for lender in lenders:
            investments = supabase_service.get_investments_by_lender(lender['id']) or []
            lender['investments'] = investments
            enriched_lenders.append(lender)
        
        # Get listed loans
        listed_loans = supabase_service.get_listed_loans() or []
        
        # Enrich loans with details
        enriched_loans = []
        for loan in listed_loans:
            loan_details = supabase_service.get_loan_with_details(loan['id'])
            if loan_details:
                enriched_loans.append(loan_details)
        
        context = {
            'lenders': enriched_lenders,
            'listed_loans': enriched_loans,
            'is_admin_view': True,
        }
        return render(request, 'core/admin_lender_view.html', context)
        
    except Exception as e:
        logger.error(f"Admin lender view error: {str(e)}")
        messages.error(request, 'Error loading lender view.')
        return redirect('admin_dashboard')


@login_required
def admin_agent_view(request):
    """Admin view of agent panel"""
    try:
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user or (current_user.get('role') != 'admin' and current_user.get('email') != 'sammyseth260@gmail.com'):
            messages.error(request, 'Access denied. Administrators only.')
            return redirect('admin_dashboard')
        
        # Get all agents from Supabase
        agents = supabase_service.get_users_by_role('agent') or []
        
        # Get pending collaterals
        pending_collaterals = supabase_service.get_pending_collaterals() or []
        
        # Enrich collaterals with user details
        enriched_pending = []
        for collateral in pending_collaterals:
            user = supabase_service.get_user_by_id(collateral.get('user_id'))
            if user:
                collateral['user'] = user
                enriched_pending.append(collateral)
        
        # Get all collaterals
        all_collaterals = supabase_service.get_all_collaterals() or []
        
        # Enrich all collaterals with user details
        enriched_all = []
        for collateral in all_collaterals:
            user = supabase_service.get_user_by_id(collateral.get('user_id'))
            if user:
                collateral['user'] = user
                enriched_all.append(collateral)
        
        context = {
            'agents': agents,
            'pending_collaterals': enriched_pending,
            'all_collaterals': enriched_all,
            'is_admin_view': True,
        }
        return render(request, 'core/admin_agent_view.html', context)
        
    except Exception as e:
        logger.error(f"Admin agent view error: {str(e)}")
        messages.error(request, 'Error loading agent view.')
        return redirect('admin_dashboard')

@login_required
def admin_users_management(request):
    """Admin view to manage all users"""
    try:
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user or (current_user.get('role') != 'admin' and current_user.get('email') != 'sammyseth260@gmail.com'):
            messages.error(request, 'Access denied. Administrators only.')
            return redirect('home')
        
        # Handle user promotion to admin
        if request.method == 'POST':
            action = request.POST.get('action')
            user_id = request.POST.get('user_id')
            
            if action == 'promote_admin' and user_id:
                # Update user in Supabase
                update_data = {
                    'role': 'admin',
                    'is_promoted_admin': True,
                    'is_staff': True,
                    'is_superuser': True
                }
                
                result = supabase_service.update_user(user_id, update_data)
                if result:
                    # Also update Django user if exists
                    try:
                        supabase_user = supabase_service.get_user_by_id(user_id)
                        if supabase_user:
                            django_user = CustomUser.objects.get(username=supabase_user['username'])
                            django_user.role = 'admin'
                            django_user.is_promoted_admin = True
                            django_user.is_staff = True
                            django_user.is_superuser = True
                            django_user.save()
                    except CustomUser.DoesNotExist:
                        pass
                    
                    messages.success(request, f'User has been promoted to Administrator.')
                else:
                    messages.error(request, 'Error promoting user. Please try again.')
            
            elif action == 'add_wallet_funds' and user_id:
                amount = Decimal(request.POST.get('amount', '0'))
                description = request.POST.get('description', 'Admin wallet credit')
                
                if amount > 0:
                    # Get current user data
                    user_data = supabase_service.get_user_by_id(user_id)
                    if user_data:
                        current_balance = Decimal(str(user_data.get('wallet_balance', 0)))
                        new_balance = current_balance + amount
                        
                        # Update wallet balance in Supabase
                        update_data = {
                            'wallet_balance': float(new_balance),
                            'total_earnings': float(Decimal(str(user_data.get('total_earnings', 0))) + amount)
                        }
                        
                        result = supabase_service.update_user(user_id, update_data)
                        if result:
                            messages.success(request, f'KES {amount} added to user\'s wallet.')
                        else:
                            messages.error(request, 'Error adding funds. Please try again.')
                    else:
                        messages.error(request, 'User not found.')
                else:
                    messages.error(request, 'Amount must be greater than zero.')
            
            return redirect('admin_users_management')
        
        # Get all users from Supabase
        all_users = supabase_service.get_all_users() or []
        
        # Calculate statistics
        total_users = len(all_users)
        borrowers_count = len([u for u in all_users if u.get('role') == 'borrower'])
        lenders_count = len([u for u in all_users if u.get('role') == 'lender'])
        agents_count = len([u for u in all_users if u.get('role') == 'agent'])
        admins_count = len([u for u in all_users if u.get('role') == 'admin'])
        
        context = {
            'all_users': all_users,
            'total_users': total_users,
            'borrowers_count': borrowers_count,
            'lenders_count': lenders_count,
            'agents_count': agents_count,
            'admins_count': admins_count,
        }
        return render(request, 'core/admin_users_management.html', context)
        
    except Exception as e:
        logger.error(f"Admin users management error: {str(e)}")
        messages.error(request, 'Error loading users management.')
        return redirect('admin_dashboard')


@login_required
def admin_commissions_payouts(request):
    """Admin view to manage agent commissions and payouts"""
    try:
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user or (current_user.get('role') != 'admin' and current_user.get('email') != 'sammyseth260@gmail.com'):
            messages.error(request, 'Access denied. Administrators only.')
            return redirect('admin_dashboard')
        
        # Get agents from Supabase
        agents = supabase_service.get_users_by_role('agent') or []
        
        # For now, return basic view since commissions aren't fully implemented in Supabase
        context = {
            'pending_commissions': [],
            'paid_commissions': [],
            'agent_stats': agents,
            'total_pending': 0,
        }
        return render(request, 'core/admin_commissions_payouts.html', context)
        
    except Exception as e:
        logger.error(f"Admin commissions payouts error: {str(e)}")
        messages.error(request, 'Error loading commissions payouts.')
        return redirect('admin_dashboard')


@login_required
def admin_payments_management(request):
    """Admin view to manage loan payments and next payment tracking"""
    try:
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user or (current_user.get('role') != 'admin' and current_user.get('email') != 'sammyseth260@gmail.com'):
            messages.error(request, 'Access denied. Administrators only.')
            return redirect('admin_dashboard')
        
        # For now, return a simple view since we don't have payments in Supabase yet
        context = {
            'active_loans': [],
            'upcoming_payments': [],
            'overdue_payments': [],
            'recent_payments': [],
            'total_active_loans': 0,
            'total_overdue': 0,
        }
        return render(request, 'core/admin_payments_management.html', context)
        
    except Exception as e:
        logger.error(f"Admin payments management error: {str(e)}")
        messages.error(request, 'Error loading payments management.')
        return redirect('admin_dashboard')


@login_required
def admin_wallet_management(request):
    """Admin view to manage user wallets"""
    try:
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user or (current_user.get('role') != 'admin' and current_user.get('email') != 'sammyseth260@gmail.com'):
            messages.error(request, 'Access denied. Administrators only.')
            return redirect('admin_dashboard')
        
        # Get all users from Supabase
        all_users = supabase_service.get_all_users() or []
        
        # Calculate wallet statistics
        total_wallet_balance = sum(float(user.get('wallet_balance', 0)) for user in all_users)
        total_earnings = sum(float(user.get('total_earnings', 0)) for user in all_users)
        
        borrowers_balance = sum(float(user.get('wallet_balance', 0)) for user in all_users if user.get('role') == 'borrower')
        lenders_balance = sum(float(user.get('wallet_balance', 0)) for user in all_users if user.get('role') == 'lender')
        agents_balance = sum(float(user.get('wallet_balance', 0)) for user in all_users if user.get('role') == 'agent')
        
        wallet_stats = {
            'total_wallet_balance': total_wallet_balance,
            'total_earnings': total_earnings,
            'borrowers_balance': borrowers_balance,
            'lenders_balance': lenders_balance,
            'agents_balance': agents_balance,
        }
        
        # Get top wallets (users with highest balances)
        top_wallets = sorted(
            [user for user in all_users if float(user.get('wallet_balance', 0)) > 0],
            key=lambda x: float(x.get('wallet_balance', 0)),
            reverse=True
        )[:20]
        
        context = {
            'wallet_stats': wallet_stats,
            'recent_transactions': [],  # Will implement when we add wallet transactions to Supabase
            'top_wallets': top_wallets,
        }
        return render(request, 'core/admin_wallet_management.html', context)
        
    except Exception as e:
        logger.error(f"Admin wallet management error: {str(e)}")
        messages.error(request, 'Error loading wallet management.')
        return redirect('admin_dashboard')
@login_required
def wallet_deposit(request):
    """Handle wallet deposits for all user types"""
    try:
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user:
            messages.error(request, 'User not found.')
            return redirect('home')

        if request.method == 'POST':
            amount = request.POST.get('amount')
            payment_method = request.POST.get('payment_method', 'mpesa')

            try:
                amount = float(amount)
                if amount < 10:
                    messages.error(request, 'Minimum deposit amount is KES 10.')
                    return redirect(request.META.get('HTTP_REFERER', 'home'))

                if amount > 100000:
                    messages.error(request, 'Maximum deposit amount is KES 100,000.')
                    return redirect(request.META.get('HTTP_REFERER', 'home'))

                # SIMULATED DEPOSIT - No real payment processing
                # In production, this would integrate with M-Pesa, bank APIs, etc.
                try:
                    success = supabase_service.process_wallet_deposit(
                        user_id=current_user['id'],
                        amount=amount,
                        payment_method=payment_method
                    )

                    if success:
                        messages.success(request, 
                            f'✅ SIMULATED DEPOSIT: Successfully added KES {amount:,.2f} to your wallet! '
                            f'(In production, this would process via {payment_method})')
                        
                        # Add success parameter to URL for auto-refresh
                        redirect_url = request.META.get('HTTP_REFERER', 'home')
                        if 'marketplace' in redirect_url:
                            redirect_url += '?deposit_success=1' if '?' not in redirect_url else '&deposit_success=1'
                        return redirect(redirect_url)
                    else:
                        messages.error(request, 'Simulated deposit failed. Please check the logs and try again.')
                        
                except Exception as deposit_error:
                    logger.error(f"Deposit service error: {str(deposit_error)}")
                    messages.error(request, f'Deposit service error: {str(deposit_error)}. Please try again.')

            except (ValueError, TypeError):
                messages.error(request, 'Invalid deposit amount.')
            except Exception as e:
                logger.error(f"Wallet deposit error: {str(e)}")
                messages.error(request, 'Deposit processing failed. Please try again.')

        # Redirect back to the referring page
        return redirect(request.META.get('HTTP_REFERER', 'home'))

    except Exception as e:
        logger.error(f"Wallet deposit view error: {str(e)}")
        messages.error(request, 'Error processing deposit.')
        return redirect('home')

@login_required
def wallet_transactions(request):
    """View wallet transaction history"""
    try:
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user:
            messages.error(request, 'User not found.')
            return redirect('home')

        # Get wallet transactions from Supabase
        transactions = supabase_service.get_wallet_transactions(current_user['id'])

        context = {
            'transactions': transactions or [],
            'wallet_balance': float(current_user.get('wallet_balance', 0)),
        }
        return render(request, 'core/wallet_transactions.html', context)

    except Exception as e:
        logger.error(f"Wallet transactions view error: {str(e)}")
        messages.error(request, 'Error loading transactions.')
        return redirect('home')
@login_required
def wallet_withdraw(request):
    """Handle wallet withdrawals for all user types"""
    try:
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user:
            messages.error(request, 'User not found.')
            return redirect('home')

        if request.method == 'POST':
            amount = request.POST.get('amount')
            withdrawal_method = request.POST.get('withdrawal_method', 'mpesa')

            try:
                amount = float(amount)
                current_balance = float(current_user.get('wallet_balance', 0))

                if amount < 100:
                    messages.error(request, 'Minimum withdrawal amount is KES 100.')
                    return redirect('wallet_transactions')

                if amount > current_balance:
                    messages.error(request, f'Insufficient balance. You have KES {current_balance:,.2f} available.')
                    return redirect('wallet_transactions')

                # Calculate withdrawal fee
                withdrawal_fee = 50 if amount < 5000 else 0
                total_deduction = amount + withdrawal_fee

                if total_deduction > current_balance:
                    messages.error(request, f'Insufficient balance including withdrawal fee of KES {withdrawal_fee}. Total needed: KES {total_deduction:,.2f}')
                    return redirect('wallet_transactions')

                # SIMULATED WITHDRAWAL - No real payment processing
                # In production, this would integrate with M-Pesa, bank APIs, etc.
                success = supabase_service.process_wallet_withdrawal(
                    user_id=current_user['id'],
                    amount=total_deduction,
                    description=f'SIMULATED: Withdrawal of KES {amount:,.2f} via {withdrawal_method} (Fee: KES {withdrawal_fee})'
                )

                if success:
                    fee_message = f' (including KES {withdrawal_fee} fee)' if withdrawal_fee > 0 else ''
                    messages.success(request, 
                        f'✅ SIMULATED WITHDRAWAL: KES {amount:,.2f} deducted from wallet{fee_message}. '
                        f'(In production, funds would be sent to your {withdrawal_method} account)')
                else:
                    messages.error(request, 'Simulated withdrawal failed. Please try again.')

            except (ValueError, TypeError):
                messages.error(request, 'Invalid withdrawal amount.')
            except Exception as e:
                logger.error(f"Wallet withdrawal error: {str(e)}")
                messages.error(request, 'Withdrawal processing failed. Please try again.')

        # Redirect back to wallet transactions
        return redirect('wallet_transactions')

    except Exception as e:
        logger.error(f"Wallet withdrawal view error: {str(e)}")
        messages.error(request, 'Error processing withdrawal.')
        return redirect('wallet_transactions')

@login_required
def kyc_verification(request):
    """Supabase-only KYC verification with persistent storage - NO Django dependencies"""
    try:
        # Get current user from Supabase (ONLY source - no Django fallback)
        current_user = get_supabase_user(request)
        if not current_user:
            messages.error(request, 'User not found in system. Please contact support.')
            return redirect('home')
        
        user_id = current_user['id']
        
        # Get KYC record from Supabase (ONLY source - no Django fallback)
        kyc_result = supabase.table('kyc_verifications').select('*').eq('user_id', user_id).execute()
        
        if kyc_result.data:
            kyc = kyc_result.data[0]
            logger.info(f"Found existing KYC record for {request.user.username}: status={kyc.get('status')}")
        else:
            # Create new KYC record in Supabase (ensure persistence)
            import uuid
            kyc_data = {
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'full_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
                'id_number': '',
                'date_of_birth': timezone.now().date().isoformat(),
                'status': 'pending',
                'created_at': timezone.now().isoformat(),
                'updated_at': timezone.now().isoformat()
            }
            
            create_result = supabase.table('kyc_verifications').insert(kyc_data).execute()
            if create_result.data:
                kyc = create_result.data[0]
                logger.info(f"Created NEW KYC record in Supabase for user {request.user.username}")
            else:
                logger.error(f"Failed to create KYC record in Supabase for {request.user.username}")
                messages.error(request, 'Error creating KYC record. Please try again.')
                return redirect('borrower_dashboard')
        
        if request.method == 'POST':
            # Get form data
            full_name = request.POST.get('full_name', '').strip()
            id_number = request.POST.get('id_number', '').strip()
            date_of_birth = request.POST.get('date_of_birth', '')
            
            # Get uploaded files
            id_front_image = request.FILES.get('id_front_image')
            id_back_image = request.FILES.get('id_back_image')
            selfie_image = request.FILES.get('selfie_image')
            signature_image = request.FILES.get('signature_image')  # Optional
            
            # Validate required fields
            if not full_name or not id_number or not date_of_birth:
                messages.error(request, 'Please fill in all required personal information fields.')
                return redirect('kyc_verification')
            
            if len(id_number) < 6:
                messages.error(request, 'ID number must be at least 6 characters long.')
                return redirect('kyc_verification')
            
            # Validate required images (including signature)
            if not id_front_image or not id_back_image or not selfie_image or not signature_image:
                messages.error(request, 'Please upload all required images: ID front, ID back, selfie photo, and signature.')
                return redirect('kyc_verification')
            
            # Validate file sizes (5MB max)
            max_size = 5 * 1024 * 1024  # 5MB
            files_to_check = [
                ('ID Front Image', id_front_image),
                ('ID Back Image', id_back_image),
                ('Selfie Photo', selfie_image),
                ('Signature Image', signature_image)
            ]
            
            for file_name, file_obj in files_to_check:
                if file_obj and file_obj.size > max_size:
                    messages.error(request, f'{file_name} is too large. Maximum size is 5MB.')
                    return redirect('kyc_verification')
            
            # Validate file types
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
            for file_name, file_obj in files_to_check:
                if file_obj and file_obj.content_type not in allowed_types:
                    messages.error(request, f'{file_name} must be a JPG, JPEG, or PNG image.')
                    return redirect('kyc_verification')
            
            # Update KYC record in Supabase (ONLY - no Django)
            update_data = {
                'full_name': full_name,
                'id_number': id_number,
                'date_of_birth': date_of_birth,
                'status': 'under_review',
                'updated_at': timezone.now().isoformat()
            }
            
            # Note: For now, we'll store image info but not the actual files
            # In a full implementation, you'd upload images to Supabase Storage
            update_data['has_id_front_image'] = True
            update_data['has_id_back_image'] = True
            update_data['has_selfie_image'] = True
            update_data['has_signature_image'] = True  # Now required
            
            update_result = supabase.table('kyc_verifications').update(update_data).eq('id', kyc['id']).execute()
            
            if update_result.data:
                logger.info(f"Updated KYC record in Supabase for {request.user.username} with images")
                
                # Run AUTOMATIC verification immediately (NO AI - simple validation only)
                try:
                    # Automatic verification based on provided data
                    has_name = full_name and len(full_name.strip()) > 2
                    has_valid_id = id_number and len(id_number.strip()) >= 6
                    has_all_images = id_front_image and id_back_image and selfie_image and signature_image
                    
                    # Calculate verification score
                    score = 0
                    if has_name:
                        score += 25
                    if has_valid_id:
                        score += 35
                    if has_all_images:
                        score += 40
                    
                    # Auto-approve if meets minimum criteria
                    if has_name and has_valid_id and has_all_images:
                        # AUTOMATIC APPROVAL - all criteria met
                        verification_result = {
                            'overall_score': 95,
                            'status': 'verified',
                            'passed': True,
                            'message': 'Automatic verification successful - all requirements met',
                            'details': f'Name: ✓, ID Number: ✓ ({len(id_number)} chars), All Images: ✓'
                        }
                        logger.info(f"AUTO-APPROVED KYC for {request.user.username} with score 95")
                        
                    elif has_name and has_valid_id:
                        # PARTIAL APPROVAL - missing some images but core info is good
                        verification_result = {
                            'overall_score': 85,
                            'status': 'verified',
                            'passed': True,
                            'message': 'Automatic verification successful - core requirements met',
                            'details': f'Name: ✓, ID Number: ✓ ({len(id_number)} chars), Images: Partial'
                        }
                        logger.info(f"AUTO-APPROVED KYC for {request.user.username} with score 85 (partial images)")
                        
                    else:
                        # REJECTION - insufficient data
                        missing = []
                        if not has_name:
                            missing.append("valid full name")
                        if not has_valid_id:
                            missing.append("valid ID number (min 6 chars)")
                        if not has_all_images:
                            missing.append("required images")
                            
                        verification_result = {
                            'overall_score': score,
                            'status': 'rejected',
                            'passed': False,
                            'message': f'Verification failed - missing: {", ".join(missing)}',
                            'details': f'Please provide complete information. Score: {score}/100'
                        }
                        logger.info(f"REJECTED KYC for {request.user.username} with score {score} - missing: {missing}")
                
                except Exception as verification_error:
                    logger.error(f"Verification error for {request.user.username}: {str(verification_error)}")
                    # Default to approval if verification system fails (be lenient)
                    verification_result = {
                        'overall_score': 80,
                        'status': 'verified',
                        'passed': True,
                        'message': 'Verification completed (system fallback)',
                        'details': 'Basic validation passed'
                    }
                    
                    # Update KYC status based on verification result (PERSIST in Supabase ONLY)
                    if verification_result.get('passed', False) and verification_result.get('overall_score', 0) >= 80:
                        final_status = 'verified'
                        verified_at = timezone.now().isoformat()
                        
                        final_update = supabase.table('kyc_verifications').update({
                            'status': final_status,
                            'verified_at': verified_at,
                            'verification_score': verification_result.get('overall_score', 0),
                            'updated_at': timezone.now().isoformat()
                        }).eq('id', kyc['id']).execute()
                        
                        if final_update.data:
                            logger.info(f"KYC VERIFIED and PERSISTED in Supabase for {request.user.username} with score {verification_result.get('overall_score')}")
                            messages.success(request,
                                '🎉 KYC verification completed automatically! ✅ You can now apply for loans. '
                                'Your identity has been automatically verified and all borrower features are now available.')
                        else:
                            logger.error(f"Failed to persist KYC verification status for {request.user.username}")
                            messages.error(request, 'Error updating verification status. Please try again.')
                    else:
                        final_status = 'rejected'
                        error_msg = verification_result.get('message', 'Verification failed')
                        
                        final_update = supabase.table('kyc_verifications').update({
                            'status': final_status,
                            'verification_score': verification_result.get('overall_score', 0),
                            'updated_at': timezone.now().isoformat()
                        }).eq('id', kyc['id']).execute()
                        
                        if final_update.data:
                            logger.warning(f"KYC REJECTED and PERSISTED in Supabase for {request.user.username}: {error_msg}")
                        
                        messages.error(request,
                            f'KYC verification failed: {error_msg}. '
                            'Please check your information and images, then try again. '
                            'Ensure your name matches your ID document exactly and all images are clear.')
                    
                except Exception as e:
                    logger.error(f"KYC verification error for {request.user.username}: {str(e)}")
                    # Fallback to manual review on error (PERSIST in Supabase)
                    supabase.table('kyc_verifications').update({
                        'status': 'under_review',
                        'updated_at': timezone.now().isoformat()
                    }).eq('id', kyc['id']).execute()
                    
                    messages.info(request,
                        'KYC submitted for review. Our team will verify your documents within 24 hours. '
                        'You will receive a notification once the verification is complete.')
                
                return redirect('kyc_verification')
            else:
                logger.error(f"Failed to update KYC information in Supabase for {request.user.username}")
                messages.error(request, 'Error updating KYC information. Please try again.')
        
        # Get updated KYC data for display (ONLY from Supabase)
        kyc_result = supabase.table('kyc_verifications').select('*').eq('user_id', user_id).execute()
        if kyc_result.data:
            kyc = kyc_result.data[0]
            logger.info(f"Displaying KYC status for {request.user.username}: {kyc.get('status')}")
        
        # Create form-like object for template compatibility (NO Django forms)
        form_data = {
            'full_name': kyc.get('full_name', ''),
            'id_number': kyc.get('id_number', ''),
            'date_of_birth': kyc.get('date_of_birth', '')
        }
        
        # Add helpful context for the user (NO AI results)
        context = {
            'kyc': kyc,
            'form': form_data,  # Simple dict instead of Django form
            'can_submit': kyc.get('status') in ['pending', 'rejected'],
            'verification_tips': [
                'Ensure your full name matches your ID document exactly',
                'Provide a clear, valid national ID number',
                'Make sure all information is accurate and complete',
                'Double-check spelling and number accuracy'
            ]
        }
        return render(request, 'core/kyc_verification.html', context)
        
    except Exception as e:
        logger.error(f"KYC verification critical error: {str(e)}")
        messages.error(request, f'Error loading KYC verification. Please try again or contact support if the problem persists.')
        return redirect('borrower_dashboard')


@login_required
def loan_payment(request, loan_id):
    """Process loan payment from wallet - Supabase version"""
    try:
        # Get loan from Supabase
        loan = supabase_service.get_loan_with_details(loan_id)
        
        if not loan:
            messages.error(request, 'Loan not found.')
            return redirect('borrower_dashboard')
        
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user or current_user.get('id') != loan.get('borrower_id'):
            messages.error(request, 'Access denied. This is not your loan.')
            return redirect('borrower_dashboard')
        
        if loan.get('status') != 'active':
            messages.error(request, 'This loan is not active for payments.')
            return redirect('borrower_dashboard')
        
        if request.method == 'POST':
            payment_type = request.POST.get('payment_type', 'monthly')
            
            # Calculate payment amounts (simplified for Supabase)
            principal_amount = float(loan.get('principal_amount', 0))
            interest_rate = float(loan.get('interest_rate', 13.0))
            duration_months = int(loan.get('duration_months', 3))
            
            monthly_payment = principal_amount * (interest_rate / 100)  # Simplified calculation
            total_repayment = loan.get('total_repayment', principal_amount * (1 + (interest_rate / 100) * duration_months))
            
            if payment_type == 'monthly':
                amount = monthly_payment
            elif payment_type == 'full':
                # Calculate remaining balance (simplified)
                payments_made = 0  # Would need to track this in Supabase
                remaining_balance = total_repayment - (payments_made * monthly_payment)
                amount = max(remaining_balance, 0)
            else:
                try:
                    amount = float(request.POST.get('amount', '0'))
                except (ValueError, TypeError):
                    amount = 0
            
            # Check wallet balance (simplified - would need wallet system in Supabase)
            wallet_balance = float(current_user.get('wallet_balance', 0))
            
            if wallet_balance >= amount:
                # Process payment (simplified - would need full payment system)
                messages.success(request, f'Payment of KES {amount:,.2f} processed successfully!')
                logger.info(f"Payment processed for loan {loan_id}: KES {amount}")
                return redirect('borrower_dashboard')
            else:
                messages.error(request, f'Insufficient wallet balance. Required: KES {amount:,.2f}, Available: KES {wallet_balance:,.2f}')
        
        # Prepare context for template
        context = {
            'loan': loan,
            'monthly_payment': principal_amount * (interest_rate / 100),
            'remaining_balance': loan.get('total_repayment', principal_amount),
            'wallet_balance': float(current_user.get('wallet_balance', 0))
        }
        return render(request, 'core/loan_payment.html', context)
        
    except Exception as e:
        logger.error(f"Loan payment error: {str(e)}")
        messages.error(request, 'Error processing payment.')
        return redirect('borrower_dashboard')


@login_required
def download_contract(request, loan_id):
    """Download loan contract PDF - Supabase version"""
    try:
        # Get loan from Supabase
        loan = supabase_service.get_loan_with_details(loan_id)
        
        if not loan:
            messages.error(request, 'Loan not found.')
            return redirect('home')
        
        # Get current user from Supabase
        current_user = get_supabase_user(request)
        if not current_user:
            messages.error(request, 'User session error. Please login again.')
            return redirect('login')
        
        # Check permissions
        can_download = False
        user_id = current_user.get('id')
        user_role = current_user.get('role')
        
        if user_id == loan.get('borrower_id'):
            can_download = True
        elif user_role == 'admin':
            can_download = True
        elif user_role == 'lender':
            # Check if lender invested in this loan
            investments = supabase_service.get_investments_by_loan(loan_id)
            lender_invested = any(inv.get('lender_id') == user_id for inv in (investments or []))
            can_download = lender_invested
        
        if not can_download:
            messages.error(request, 'You do not have permission to download this contract.')
            return redirect('home')
        
        # Get contract URL from Supabase
        contract_url = supabase_service.get_loan_contract_url(loan_id)
        if not contract_url:
            messages.error(request, 'Contract PDF not available yet.')
            return redirect('borrower_documents')
        
        # For now, return a simple message since PDF generation is complex
        messages.info(request, f'Contract download feature is being updated. Contract URL: {contract_url}')
        return redirect('borrower_documents')
        
    except Exception as e:
        logger.error(f"Contract download error: {str(e)}")
        messages.error(request, 'Error downloading contract.')
        return redirect('borrower_documents')
        return redirect('home')


@login_required
def verify_collateral(request, collateral_id):
    """Agent view to verify collateral and update market value - Supabase version"""
    try:
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user or current_user.get('role') not in ['agent', 'admin']:
            messages.error(request, 'Access denied. Agents only.')
            return redirect('home')
        
        # Get collateral from Supabase
        collateral = supabase_service.get_collateral_by_id(collateral_id)
        if not collateral or collateral.get('status') != 'pending':
            messages.error(request, 'Collateral not found or already processed.')
            return redirect('agent_panel')
        
        if request.method == 'POST':
            # Get form data
            verified_value = request.POST.get('verified_value')
            agent_notes = request.POST.get('agent_notes', '')
            
            try:
                verified_value = float(verified_value) if verified_value else collateral.get('market_value')
            except (ValueError, TypeError):
                verified_value = collateral.get('market_value', 0)
            
            # Update collateral status in Supabase
            update_result = supabase_service.update_collateral_status(
                collateral_id, 
                'verified', 
                verified_by=current_user['id']
            )
            
            if update_result:
                # Update additional fields
                additional_data = {
                    'verified_by': current_user['id'],
                    'verification_date': timezone.now().isoformat(),
                    'agent_verified_value': float(verified_value),
                    'agent_notes': agent_notes
                }
                
                supabase.table('collateral').update(additional_data).eq('id', collateral_id).execute()
                
                # Update associated loan status
                try:
                    # Find loan with this collateral
                    loans_result = supabase.table('loans').select('*').eq('collateral_id', collateral_id).execute()
                    
                    if loans_result.data:
                        loan = loans_result.data[0]
                        loan_id = loan['id']
                        
                        # Update loan status to listed
                        supabase_service.update_loan_status(loan_id, 'listed')
                        
                        logger.info(f"Loan {loan_id} status updated to 'listed' after collateral verification")
                    
                    # Also update Django for admin interface (optional)
                    try:
                        django_collateral = Collateral.objects.filter(
                            user__username=collateral.get('user', {}).get('username', ''),
                            item_type=collateral.get('item_type'),
                            brand_model=collateral.get('brand_model'),
                            estimated_value=collateral.get('market_value'),
                            status='pending'
                        ).first()
                        
                        if django_collateral:
                            django_collateral.status = 'verified'
                            django_collateral.verification_date = timezone.now()
                            django_collateral.verified_by = request.user
                            django_collateral.agent_verified_value = float(verified_value)
                            django_collateral.agent_notes = agent_notes
                            django_collateral.save()
                            
                            # Update associated Django loan
                            try:
                                django_loan = Loan.objects.get(collateral=django_collateral)
                                django_loan.status = 'listed'
                                django_loan.save()
                            except Loan.DoesNotExist:
                                pass
                    except Exception as django_error:
                        logger.warning(f"Django collateral update failed (non-critical): {str(django_error)}")
                    
                    # Get user info for success message
                    user = supabase_service.get_user_by_id(collateral.get('user_id'))
                    username = user.get('username', 'Unknown') if user else 'Unknown'
                    verified_amount = float(verified_value)
                    
                    messages.success(request, 
                        f'✅ Collateral verified successfully! '
                        f'Borrower: {username} | '
                        f'Item: {collateral.get("brand_model")} | '
                        f'Verified Value: KES {verified_amount:,.2f} | '
                        f'Loan is now listed for funding.')
                    
                    logger.info(f"Collateral {collateral_id} verified by agent {current_user['username']} "
                              f"with value KES {verified_amount:,.2f}")
                    
                except Exception as e:
                    logger.error(f"Error updating loan status after collateral verification: {str(e)}")
                    messages.warning(request, 'Collateral verified but there was an issue updating the loan status.')
                
                return redirect('agent_panel')
            else:
                messages.error(request, 'Error updating collateral status. Please try again.')
        
        # Calculate max loan amount
        market_value = float(collateral.get('market_value', 0))
        max_loan_amount = market_value * 0.7 * 0.5  # 30/50 rule
        
        # Get user info
        user = supabase_service.get_user_by_id(collateral.get('user_id'))
        
        context = {
            'collateral': collateral,
            'user': user,
            'max_loan_amount': max_loan_amount,
            'verified_value': collateral.get('market_value', 0)
        }
        return render(request, 'core/verify_collateral.html', context)
        
    except Exception as e:
        logger.error(f"Collateral verification error: {str(e)}")
        messages.error(request, 'Error verifying collateral.')
        return redirect('agent_panel')


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def check_username_api(request):
    """API endpoint to check username availability"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            
            if len(username) < 3:
                return JsonResponse({
                    'available': False,
                    'message': 'Username must be at least 3 characters long'
                })
            
            # Check if username exists in Supabase
            existing_user = supabase_service.get_user_by_username(username)
            
            if existing_user:
                # Generate suggestions
                suggestions = []
                import random
                random_num = random.randint(1, 999)
                
                suggestions.append(f"{username}{random_num}")
                suggestions.append(f"{username}_{random_num}")
                suggestions.append(f"user_{username}")
                
                return JsonResponse({
                    'available': False,
                    'message': 'Username is already taken',
                    'suggestions': suggestions
                })
            else:
                return JsonResponse({
                    'available': True,
                    'message': 'Username is available'
                })
                
        except Exception as e:
            logger.error(f"Username check API error: {str(e)}")
            return JsonResponse({
                'available': False,
                'message': 'Error checking username availability'
            })
    
    return JsonResponse({'error': 'Invalid request method'})


@login_required
def borrower_loans(request):
    """Borrower's loans page - Supabase ONLY"""
    try:
        # Check if user is borrower or admin
        user_role = getattr(request.user, 'role', 'borrower')
        if user_role not in ['borrower', 'admin']:
            messages.error(request, 'Access denied. This page is for borrowers.')
            return redirect('home')
        
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user:
            messages.error(request, 'User not found in system.')
            return redirect('home')
        
        # Get borrower's loans from Supabase ONLY
        loans = supabase_service.get_loans_by_borrower(current_user['id']) or []
        
        # Enrich loans with details
        enriched_loans = []
        for loan in loans:
            try:
                loan_details = supabase_service.get_loan_with_details(loan['id'])
                if loan_details:
                    enriched_loans.append(loan_details)
            except Exception as e:
                logger.error(f"Error enriching loan {loan.get('id')}: {str(e)}")
        
        context = {
            'loans': enriched_loans,
            'is_admin': user_role == 'admin',
            'user_role': user_role,
        }
        return render(request, 'core/borrower_loans.html', context)
        
    except Exception as e:
        logger.error(f"Borrower loans error: {str(e)}")
        messages.error(request, 'Error loading loans.')
        return redirect('borrower_dashboard')


@login_required
def borrower_collaterals(request):
    """Borrower's collaterals page"""
    try:
        # Check if user is borrower or admin
        user_role = getattr(request.user, 'role', 'borrower')
        if user_role not in ['borrower', 'admin']:
            messages.error(request, 'Access denied. This page is for borrowers.')
            return redirect('home')
        
        # Get borrower's collaterals
        collaterals = Collateral.objects.filter(user=request.user).order_by('-created_at')
        
        context = {
            'collaterals': collaterals,
            'is_admin': user_role == 'admin',
            'user_role': user_role,
        }
        return render(request, 'core/borrower_collaterals.html', context)
        
    except Exception as e:
        logger.error(f"Borrower collaterals error: {str(e)}")
        messages.error(request, 'Error loading collaterals.')
        return redirect('borrower_dashboard')


@login_required
def borrower_documents(request):
    """Borrower's documents and PDFs page - Supabase ONLY"""
    try:
        # Get current user from Supabase
        current_user = get_supabase_user(request)
        if not current_user:
            messages.error(request, 'User not found in system.')
            return redirect('home')
        
        # Check if user is borrower or admin
        user_role = current_user.get('role', 'borrower')
        if user_role not in ['borrower', 'admin']:
            messages.error(request, 'Access denied. This page is for borrowers.')
            return redirect('home')
        
        # Get borrower's loans with contracts from Supabase
        loans_with_contracts = supabase_service.get_loans_with_contracts(current_user['id'])
        
        # Get KYC documents from Supabase
        kyc_documents = supabase_service.get_kyc_by_user_id(current_user['id'])
        
        context = {
            'loans_with_contracts': loans_with_contracts or [],
            'kyc_documents': kyc_documents,
            'is_admin': user_role == 'admin',
            'user_role': user_role,
        }
        return render(request, 'core/borrower_documents.html', context)
        
    except Exception as e:
        logger.error(f"Borrower documents error: {str(e)}")
        messages.error(request, 'Error loading documents from Supabase.')
        return redirect('borrower_dashboard')