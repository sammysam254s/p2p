from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from decimal import Decimal
import logging
import json
from .models import CustomUser, Collateral, Loan, Investment, WalletTransaction, Commission, Payment, KYCVerification
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
    """Custom logout view that handles both GET and POST requests"""
    next_page = '/'  # Redirect to home page after logout
    
    def get(self, request, *args, **kwargs):
        """Handle GET requests for logout"""
        return self.post(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        """Handle POST requests for logout"""
        if request.user.is_authenticated:
            username = request.user.username
            logger.info(f"User {username} logging out")
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
                
                # Create user in Supabase
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
                    logger.info(f"User {username} created successfully in Supabase")
                    messages.success(request, f'Account created for {username}! You can now log in.')
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
        
        # Try to get user from Supabase, but don't fail if not found
        current_user = None
        try:
            current_user = supabase_service.get_user_by_username(request.user.username)
        except Exception as e:
            logger.warning(f"Could not get user from Supabase: {str(e)}")
        
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
                        # Create a pending KYC record in Supabase (ensure persistence)
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
                                logger.error(f"Failed to create KYC record in Supabase for {request.user.username}")
                                kyc_verified = False
                                kyc_status = 'pending'
                                kyc_exists = False
                        except Exception as e:
                            logger.error(f"Error creating KYC record in Supabase: {str(e)}")
                            kyc_verified = False
                            kyc_status = 'pending'
                            kyc_exists = False
                else:
                    logger.warning(f"No Supabase user found for {request.user.username}")
                    kyc_verified = False
                    kyc_status = 'pending'
                    kyc_exists = False
                        
            except Exception as e:
                logger.error(f"KYC check error: {str(e)}")
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
                    
                    # Validate loan amount against collateral
                    if supabase_collateral and 'market_value' in supabase_collateral:
                        # Calculate max loan amount using the 30/50 rule
                        market_value = float(supabase_collateral['market_value'])
                        max_loan_amount = market_value * 0.7 * 0.5  # 30% devaluation, then 50% of devalued amount
                    else:
                        max_loan_amount = 0
                    requested_amount = float(loan_form.cleaned_data['principal_amount'])
                    
                    if requested_amount > max_loan_amount:
                        # Delete the collateral we just created
                        try:
                            supabase.table('collateral').delete().eq('id', supabase_collateral['id']).execute()
                        except:
                            pass
                        messages.error(request, 
                            f'Requested amount (KES {requested_amount:,.2f}) exceeds maximum '
                            f'allowed (KES {max_loan_amount:,.2f}) based on collateral value.')
                        return redirect('borrower_dashboard')
                    
                    # Create loan in Supabase FIRST (primary database)
                    supabase_loan = supabase_service.create_loan(
                        borrower_id=supabase_user_id,
                        collateral_id=supabase_collateral['id'],
                        principal_amount=requested_amount,
                        interest_rate=float(loan_form.cleaned_data.get('interest_rate', 13.0)),
                        duration_months=int(loan_form.cleaned_data['duration_months'])
                    )
                    
                    if not supabase_loan:
                        # Delete the collateral we created
                        try:
                            supabase.table('collateral').delete().eq('id', supabase_collateral['id']).execute()
                        except:
                            pass
                        messages.error(request, 'Error creating loan record. Please try again.')
                        return redirect('borrower_dashboard')
                    
                    # Also create in Django for admin interface (secondary) - OPTIONAL
                    try:
                        django_collateral = collateral_form.save(commit=False)
                        django_collateral.user = request.user
                        django_collateral.estimated_value = django_collateral.market_value  # Copy market_value to estimated_value for Django compatibility
                        django_collateral.save()
                        
                        django_loan = loan_form.save(commit=False)
                        django_loan.borrower = request.user
                        django_loan.collateral = django_collateral
                        django_loan.status = 'pending_collateral'
                        django_loan.save()
                        
                        logger.info(f"Created loan in both Supabase (primary) and Django (secondary) for {request.user.username}")
                    except Exception as django_error:
                        logger.warning(f"Django loan creation failed (non-critical): {str(django_error)}")
                        # Continue - Supabase is primary, Django is optional
                    
                    messages.success(request, 
                        '🎉 Loan application submitted successfully! '
                        'Your loan is now pending collateral verification by a station agent. '
                        'You will be notified once the verification is complete and your loan is listed for funding.')
                    
                    logger.info(f"Loan created successfully in Supabase for {request.user.username}: "
                              f"Amount: KES {requested_amount:,.2f}, Collateral: {supabase_collateral['brand_model']}")
                    
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
                    'agent_verified_value': float(verified_value) if verified_value else collateral.get('estimated_value'),
                    'agent_notes': agent_notes
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
                    
                    # Also try to update in Django (secondary, non-critical)
                    try:
                        from .models import Collateral, Loan
                        django_collateral = Collateral.objects.filter(
                            item_type=collateral.get('item_type'),
                            brand_model=collateral.get('brand_model'),
                            estimated_value=collateral.get('estimated_value'),
                            status='pending'
                        ).first()
                        
                        if django_collateral:
                            django_collateral.status = 'verified'
                            django_collateral.verification_date = timezone.now()
                            django_collateral.verified_by = request.user
                            django_collateral.agent_verified_value = float(verified_value) if verified_value else django_collateral.estimated_value
                            django_collateral.agent_notes = agent_notes
                            django_collateral.save()
                            
                            # Update associated Django loan
                            django_loan = Loan.objects.filter(collateral=django_collateral).first()
                            if django_loan:
                                django_loan.status = 'listed'
                                django_loan.save()
                                
                    except Exception as django_error:
                        logger.warning(f"Django update failed (non-critical): {str(django_error)}")
                    
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
        # Get current user from Supabase (primary database)
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user:
            # Create user in Supabase if not exists
            try:
                current_user = supabase_service.create_user(
                    username=request.user.username,
                    email=request.user.email,
                    password="",
                    role=getattr(request.user, 'role', 'lender'),
                    phone_number=getattr(request.user, 'phone_number', ''),
                    national_id=getattr(request.user, 'national_id', ''),
                    first_name=request.user.first_name,
                    last_name=request.user.last_name
                )
            except Exception as e:
                logger.error(f"Error creating user in Supabase: {str(e)}")
        
        if not current_user:
            messages.error(request, 'User not found in system.')
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
                if investment_amount > remaining_amount:
                    messages.error(request, f'Investment amount exceeds remaining funding needed (KES {remaining_amount:,.2f})')
                elif investment_amount <= 0:
                    messages.error(request, 'Investment amount must be greater than zero.')
                elif investment_amount < 100:
                    messages.error(request, 'Minimum investment amount is KES 100.')
                else:
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
        
        context = {
            'listed_loans': valid_loans,
            'lender_investments': lender_investments,
            'total_invested': total_invested,
            'total_loans_available': total_loans_available,
            'total_funding_needed': total_funding_needed,
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
        # Get loan with all details from Supabase
        loan = supabase_service.get_loan_with_details(loan_id)
        
        if not loan:
            messages.error(request, 'Loan not found.')
            # Smart redirect based on user role
            if hasattr(request.user, 'role'):
                role_redirects = {
                    'borrower': 'borrower_dashboard',
                    'lender': 'marketplace',
                    'agent': 'agent_panel',
                    'admin': 'admin_dashboard'
                }
                return redirect(role_redirects.get(request.user.role, 'home'))
            return redirect('home')
        
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user:
            messages.error(request, 'User session error. Please login again.')
            return redirect('login')
        
        # Check permissions with detailed access control
        borrower_id = loan.get('borrower_id')
        user_role = current_user.get('role')
        user_id = current_user.get('id')
        
        # Allow access for: loan owner, agents, lenders, and admins
        has_access = (
            user_id == borrower_id or  # Loan owner
            user_role in ['agent', 'admin'] or  # Agents and admins
            (user_role == 'lender' and loan.get('status') in ['listed', 'active'])  # Lenders for listed/active loans
        )
        
        if not has_access:
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
        
        # Get investments for this loan
        investments = supabase_service.get_investments_by_loan(loan_id) or []
        
        # Enrich investments with lender details
        for investment in investments:
            lender = supabase_service.get_user_by_id(investment.get('lender_id'))
            if lender:
                investment['lender'] = lender
        
        # Add additional loan context
        loan['can_invest'] = (
            user_role == 'lender' and 
            loan.get('status') == 'listed' and 
            float(loan.get('funded_amount', 0)) < float(loan.get('principal_amount', 0))
        )
        
        loan['is_owner'] = (user_id == borrower_id)
        loan['is_admin'] = (user_role == 'admin')
        
        context = {
            'loan': loan,
            'investments': investments,
            'user_role': user_role,
        }
        return render(request, 'core/loan_detail.html', context)
        
    except Exception as e:
        logger.error(f"Loan detail error for loan {loan_id}: {str(e)}")
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
        
        # Get recent activities using Django ORM for speed
        try:
            recent_loans = list(Loan.objects.select_related('borrower', 'collateral')
                              .order_by('-created_at')[:10])
            recent_investments = list(Investment.objects.select_related('lender', 'loan')
                                    .order_by('-date')[:10])
            recent_users = list(CustomUser.objects.order_by('-date_joined')[:10])
        except Exception as e:
            logger.error(f"Error getting recent activities: {str(e)}")
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
def kyc_verification(request):
    """Supabase-only KYC verification with persistent storage - NO Django dependencies"""
    try:
        # Get current user from Supabase (ONLY source - no Django fallback)
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user:
            # Create user in Supabase if not exists (ensure persistence)
            try:
                current_user = supabase_service.create_user(
                    username=request.user.username,
                    email=request.user.email,
                    password="",  # Password not needed for existing users
                    role=getattr(request.user, 'role', 'borrower'),
                    phone_number=getattr(request.user, 'phone_number', ''),
                    national_id=getattr(request.user, 'national_id', ''),
                    first_name=request.user.first_name,
                    last_name=request.user.last_name
                )
                if current_user and isinstance(current_user, list) and len(current_user) > 0:
                    current_user = current_user[0]
                logger.info(f"Created user in Supabase for KYC: {request.user.username}")
            except Exception as e:
                logger.error(f"Error creating user in Supabase: {str(e)}")
                messages.error(request, 'User profile error. Please contact support.')
                return redirect('home')
        
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
            
            # Validate required fields
            if not full_name or not id_number or not date_of_birth:
                messages.error(request, 'Please fill in all required fields.')
                return redirect('kyc_verification')
            
            if len(id_number) < 6:
                messages.error(request, 'ID number must be at least 6 characters long.')
                return redirect('kyc_verification')
            
            # Update KYC record in Supabase (ONLY - no Django)
            update_data = {
                'full_name': full_name,
                'id_number': id_number,
                'date_of_birth': date_of_birth,
                'status': 'under_review',
                'updated_at': timezone.now().isoformat()
            }
            
            update_result = supabase.table('kyc_verifications').update(update_data).eq('id', kyc['id']).execute()
            
            if update_result.data:
                logger.info(f"Updated KYC record in Supabase for {request.user.username}")
                
                # Run simple verification immediately (NO AI - simple text matching only)
                try:
                    if KYC_SERVICE_AVAILABLE and simple_kyc_service:
                        # Create a mock KYC object for verification
                        class MockKYC:
                            def __init__(self, data):
                                self.full_name = data['full_name']
                                self.id_number = data['id_number']
                                self.date_of_birth = timezone.datetime.fromisoformat(data['date_of_birth']).date()
                                self.user = type('User', (), {'username': current_user['username']})()
                        
                        mock_kyc = MockKYC(update_result.data[0])
                        verification_result = simple_kyc_service.verify_kyc_submission(mock_kyc)
                        logger.info(f"Simple KYC verification result for {request.user.username}: {verification_result}")
                    else:
                        # Basic verification when service not available (NO AI dependencies)
                        if full_name and id_number and len(id_number) >= 6:
                            verification_result = {
                                'overall_score': 95,
                                'status': 'verified',
                                'passed': True,
                                'message': 'Basic verification completed - all required fields provided',
                                'details': 'Name and ID number validation passed'
                            }
                        else:
                            verification_result = {
                                'overall_score': 30,
                                'status': 'rejected',
                                'passed': False,
                                'message': 'Missing required information',
                                'details': 'Please provide complete name and valid ID number'
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
                                '🎉 KYC verification completed successfully! ✅ You can now apply for loans. '
                                'Your identity has been verified and all borrower features are now available.')
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
                            'Please check your information and try again. '
                            'Ensure your name matches your ID document exactly.')
                    
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
    """Process loan payment from wallet"""
    try:
        loan = get_object_or_404(Loan, id=loan_id, borrower=request.user)
        
        if loan.status != 'active':
            messages.error(request, 'This loan is not active for payments.')
            return redirect('borrower_dashboard')
        
        if request.method == 'POST':
            payment_type = request.POST.get('payment_type', 'monthly')
            
            if payment_type == 'monthly':
                amount = loan.get_next_payment_amount()
            elif payment_type == 'full':
                # Calculate remaining balance
                remaining_balance = loan.calculate_total_repayment() - (loan.payments_made * loan.calculate_monthly_payment())
                amount = max(remaining_balance, 0)
            else:
                amount = Decimal(request.POST.get('amount', '0'))
            
            # Check wallet balance
            if request.user.wallet_balance >= amount:
                # Process payment
                success = request.user.deduct_from_wallet(
                    amount, 
                    f"Loan payment for Loan #{loan.id}"
                )
                
                if success:
                    # Create payment record
                    Payment.objects.create(
                        loan=loan,
                        amount=amount,
                        payment_type=payment_type,
                        processed_by=request.user
                    )
                    
                    # Update loan
                    loan.payments_made += 1
                    if payment_type == 'full' or loan.payments_made >= loan.duration_months:
                        loan.status = 'paid'
                        loan.next_payment_date = None
                        # Release collateral
                        loan.collateral.status = 'released'
                        loan.collateral.save()
                    else:
                        # Set next payment date
                        from datetime import timedelta
                        loan.next_payment_date = timezone.now() + timedelta(days=30)
                    
                    loan.save()
                    
                    messages.success(request, f'Payment of KES {amount:,.2f} processed successfully!')
                    return redirect('borrower_dashboard')
                else:
                    messages.error(request, 'Payment processing failed.')
            else:
                messages.error(request, f'Insufficient wallet balance. Required: KES {amount:,.2f}')
        
        context = {
            'loan': loan,
            'monthly_payment': loan.get_next_payment_amount(),
            'remaining_balance': loan.calculate_total_repayment() - (loan.payments_made * loan.calculate_monthly_payment()),
        }
        return render(request, 'core/loan_payment.html', context)
        
    except Exception as e:
        logger.error(f"Loan payment error: {str(e)}")
        messages.error(request, 'Error processing payment.')
        return redirect('borrower_dashboard')


@login_required
def download_contract(request, loan_id):
    """Download loan contract PDF"""
    try:
        loan = get_object_or_404(Loan, id=loan_id)
        
        # Check permissions
        can_download = False
        
        if request.user == loan.borrower:
            can_download = True
        elif request.user.role == 'admin':
            can_download = True
        elif request.user.role == 'lender':
            # Lender can download only if they invested in the loan
            investments = Investment.objects.filter(loan=loan, lender=request.user)
            can_download = investments.exists()
        
        if not can_download:
            messages.error(request, 'You do not have permission to download this contract.')
            return redirect('home')
        
        # Generate PDF if it doesn't exist
        if not loan.contract_pdf:
            if PDF_SERVICE_AVAILABLE and pdf_generator:
                pdf_generator.save_contract_pdf(loan)
        
        # Serve the PDF
        response = HttpResponse(loan.contract_pdf.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="loan_contract_{loan.id}.pdf"'
        return response
        
    except Exception as e:
        logger.error(f"Contract download error: {str(e)}")
        messages.error(request, 'Error downloading contract.')
        return redirect('home')


@login_required
def verify_collateral(request, collateral_id):
    """Agent view to verify collateral and update market value"""
    try:
        # Check if user is agent or admin
        if request.user.role not in ['agent', 'admin']:
            messages.error(request, 'Access denied. Agents only.')
            return redirect('home')
        
        collateral = get_object_or_404(Collateral, id=collateral_id, status='pending')
        
        if request.method == 'POST':
            form = CollateralVerificationForm(request.POST, instance=collateral)
            if form.is_valid():
                collateral = form.save(commit=False)
                collateral.status = 'verified'
                collateral.verification_date = timezone.now()
                collateral.verified_by = request.user
                collateral.save()
                
                # Update associated loan status and generate PDF
                try:
                    loan = Loan.objects.get(collateral=collateral)
                    loan.status = 'listed'
                    loan.save()
                    
                    # Generate contract PDF
                    if PDF_SERVICE_AVAILABLE and pdf_generator:
                        pdf_generator.save_contract_pdf(loan)
                    
                    # Remove KYC images for security (after PDF generation)
                    try:
                        kyc = loan.borrower.kyc
                        if kyc.status == 'verified':
                            # Images are now in the PDF, remove from KYC for security
                            kyc.id_front_image.delete()
                            kyc.id_back_image.delete()
                            kyc.selfie_image.delete()
                            # Keep signature for future use
                    except:
                        pass
                    
                    messages.success(request, f'Collateral verified and loan listed. Market value updated to KES {collateral.agent_verified_value:,.2f}')
                except Loan.DoesNotExist:
                    messages.success(request, 'Collateral verified successfully.')
                
                return redirect('agent_panel')
        else:
            form = CollateralVerificationForm(instance=collateral)
        
        context = {
            'form': form,
            'collateral': collateral,
            'max_loan_amount': collateral.calculate_max_loan_amount(),
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
    """Borrower's loans page"""
    try:
        # Check if user is borrower or admin
        user_role = getattr(request.user, 'role', 'borrower')
        if user_role not in ['borrower', 'admin']:
            messages.error(request, 'Access denied. This page is for borrowers.')
            return redirect('home')
        
        # Get borrower's loans
        loans = Loan.objects.filter(borrower=request.user).select_related('collateral').order_by('-created_at')
        
        context = {
            'loans': loans,
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
    """Borrower's documents and PDFs page"""
    try:
        # Check if user is borrower or admin
        user_role = getattr(request.user, 'role', 'borrower')
        if user_role not in ['borrower', 'admin']:
            messages.error(request, 'Access denied. This page is for borrowers.')
            return redirect('home')
        
        # Get borrower's loans with contracts
        loans_with_contracts = Loan.objects.filter(
            borrower=request.user,
            contract_pdf__isnull=False
        ).exclude(contract_pdf='').select_related('collateral').order_by('-created_at')
        
        # Get KYC documents
        kyc_documents = None
        try:
            kyc_documents = request.user.kyc
        except KYCVerification.DoesNotExist:
            pass
        
        context = {
            'loans_with_contracts': loans_with_contracts,
            'kyc_documents': kyc_documents,
            'is_admin': user_role == 'admin',
            'user_role': user_role,
        }
        return render(request, 'core/borrower_documents.html', context)
        
    except Exception as e:
        logger.error(f"Borrower documents error: {str(e)}")
        messages.error(request, 'Error loading documents.')
        return redirect('borrower_dashboard')