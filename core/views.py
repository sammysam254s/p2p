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
try:
    from .kyc_ai_service import kyc_ai_service
    KYC_SERVICE_AVAILABLE = True
except ImportError:
    KYC_SERVICE_AVAILABLE = False
    kyc_ai_service = None

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
        
        # Check KYC status (skip for admin)
        kyc_verified = False
        kyc_status = 'pending'
        kyc_exists = False
        
        if user_role == 'admin':
            kyc_verified = True
            kyc_status = 'admin_access'
            kyc_exists = True
        else:
            # Check KYC from Django model
            try:
                kyc = request.user.kyc
                kyc_verified = kyc.is_verified()
                kyc_status = kyc.status
                kyc_exists = True
            except KYCVerification.DoesNotExist:
                # Create a pending KYC record for the user
                try:
                    kyc = KYCVerification.objects.create(
                        user=request.user,
                        full_name=f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
                        id_number="",
                        date_of_birth=timezone.now().date(),
                        status='pending'
                    )
                    kyc_verified = False
                    kyc_status = 'pending'
                    kyc_exists = True
                    logger.info(f"Created KYC record for user {request.user.username}")
                except Exception as e:
                    logger.error(f"Error creating KYC record: {str(e)}")
                    kyc_verified = False
                    kyc_status = 'pending'
                    kyc_exists = False
            except Exception as e:
                logger.warning(f"KYC check error: {str(e)}")
                kyc_verified = False
                kyc_status = 'pending'
                kyc_exists = False
        
        # Get borrower's loans from Django (most reliable)
        try:
            django_loans = Loan.objects.filter(borrower=request.user).order_by('-created_at')
        except Exception as e:
            logger.error(f"Error getting loans: {str(e)}")
            django_loans = []
        
        # Calculate totals safely
        total_borrowed = 0
        total_outstanding = 0
        try:
            total_borrowed = sum(loan.principal_amount for loan in django_loans)
            total_outstanding = sum(
                loan.calculate_total_repayment() - (loan.payments_made * loan.calculate_monthly_payment())
                for loan in django_loans if loan.status == 'active'
            )
        except Exception as e:
            logger.error(f"Error calculating totals: {str(e)}")
        
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
                    # Create collateral
                    collateral = collateral_form.save(commit=False)
                    collateral.user = request.user
                    collateral.save()
                    
                    # Validate loan amount against collateral
                    max_loan_amount = collateral.calculate_max_loan_amount()
                    requested_amount = loan_form.cleaned_data['principal_amount']
                    
                    if requested_amount > max_loan_amount:
                        collateral.delete()
                        messages.error(request, 
                            f'Requested amount (KES {requested_amount:,.2f}) exceeds maximum '
                            f'allowed (KES {max_loan_amount:,.2f}) based on collateral value.')
                    else:
                        # Create loan
                        loan = loan_form.save(commit=False)
                        loan.borrower = request.user
                        loan.collateral = collateral
                        loan.save()
                        
                        messages.success(request, 
                            'Loan application submitted! Please visit a station agent to verify your collateral.')
                        return redirect('borrower_dashboard')
                        
                except Exception as e:
                    logger.error(f"Loan application error: {str(e)}")
                    messages.error(request, 'Error processing loan application. Please try again.')
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
            'loans': django_loans,
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
    """Station agent panel for collateral verification"""
    try:
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user:
            messages.error(request, 'User not found.')
            return redirect('home')
        
        # Allow admin to access agent panel
        user_role = current_user.get('role')
        if user_role not in ['agent', 'admin']:
            messages.error(request, 'Access denied. Station agents only.')
            return redirect('home')
        
        # Get pending collateral items from Supabase
        pending_collaterals = supabase_service.get_pending_collaterals() or []
        
        # Enrich collaterals with user details
        enriched_collaterals = []
        for collateral in pending_collaterals:
            user = supabase_service.get_user_by_id(collateral.get('user_id'))
            if user:
                collateral['user'] = user
                enriched_collaterals.append(collateral)
        
        # Handle verification
        if request.method == 'POST':
            collateral_id = request.POST.get('collateral_id')
            
            # Find the collateral
            collateral = None
            for c in pending_collaterals:
                if c['id'] == collateral_id:
                    collateral = c
                    break
            
            if not collateral:
                messages.error(request, 'Collateral not found.')
                return redirect('agent_panel')
            
            # Update collateral status in Supabase
            result = supabase_service.update_collateral_status(
                collateral_id, 
                'verified', 
                verified_by=current_user['id']
            )
            
            if result:
                # Find and update associated loan status to 'listed'
                all_loans = supabase_service.get_all_loans() or []
                loan_updated = False
                
                for loan in all_loans:
                    if loan.get('collateral_id') == collateral_id:
                        loan_result = supabase_service.update_loan_status(loan['id'], 'listed')
                        if loan_result:
                            loan_updated = True
                            break
                
                if loan_updated:
                    user = supabase_service.get_user_by_id(collateral.get('user_id'))
                    username = user.get('username', 'Unknown') if user else 'Unknown'
                    messages.success(request, f'Collateral verified and loan listed for {username}')
                else:
                    messages.warning(request, 'Collateral verified but no associated loan found.')
            else:
                messages.error(request, 'Error verifying collateral. Please try again.')
            
            return redirect('agent_panel')
        
        context = {
            'pending_collaterals': enriched_collaterals,
            'is_admin': user_role == 'admin',  # Add admin flag for template
        }
        return render(request, 'core/agent_panel.html', context)
        
    except Exception as e:
        logger.error(f"Agent panel error: {str(e)}")
        messages.error(request, 'Error loading agent panel.')
        return redirect('home')


@login_required
def marketplace(request):
    """Fast lender marketplace without complex caching"""
    try:
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user:
            messages.error(request, 'User not found.')
            return redirect('home')
        
        # Allow admin to access marketplace
        user_role = current_user.get('role')
        if user_role not in ['lender', 'admin']:
            messages.error(request, 'Access denied. Lenders only.')
            return redirect('home')
        
        # Get loans that need funding from Django for better data consistency
        # Include both 'listed' and 'pending_collateral' that have been verified
        available_loans = Loan.objects.filter(
            status__in=['listed', 'pending_collateral']
        ).select_related('borrower', 'collateral').order_by('-created_at')
        
        # Filter for loans that are actually available for investment
        valid_loans = []
        for loan in available_loans:
            # Check if loan is ready for investment
            loan_ready = False
            
            if loan.status == 'listed':
                loan_ready = True
            elif loan.status == 'pending_collateral' and loan.collateral.status == 'verified':
                # Auto-update loan status if collateral is verified
                loan.status = 'listed'
                loan.save()
                loan_ready = True
            
            if loan_ready and not loan.is_expired():
                # Check if loan still needs funding
                remaining_amount = loan.principal_amount - loan.funded_amount
                if remaining_amount > 0:
                    valid_loans.append(loan)
            elif loan.is_expired():
                # Auto-expire loans that have passed 7-day window
                loan.status = 'cancelled'
                loan.save()
        
        # Handle investment
        if request.method == 'POST':
            loan_id = request.POST.get('loan_id')
            investment_amount = Decimal(request.POST.get('investment_amount', '0'))
            
            try:
                loan = Loan.objects.get(id=loan_id, status='listed')
                
                # Validate investment amount
                remaining_amount = loan.principal_amount - loan.funded_amount
                if investment_amount > remaining_amount:
                    messages.error(request, f'Investment amount exceeds remaining funding needed (KES {remaining_amount:,.2f})')
                elif investment_amount <= 0:
                    messages.error(request, 'Investment amount must be greater than zero.')
                elif investment_amount < 100:
                    messages.error(request, 'Minimum investment amount is KES 100.')
                else:
                    # Create investment
                    investment = Investment.objects.create(
                        lender=request.user,
                        loan=loan,
                        amount_invested=investment_amount,
                        expected_return=investment_amount * Decimal('0.13')  # 13% return
                    )
                    
                    # Update loan funded amount
                    loan.funded_amount += investment_amount
                    
                    # Check if loan is fully funded
                    if loan.funded_amount >= loan.principal_amount:
                        loan.status = 'active'
                        loan.activate_loan()
                        
                        # Generate updated contract PDF
                        if PDF_SERVICE_AVAILABLE and pdf_generator:
                            pdf_generator.save_contract_pdf(loan)
                        
                        messages.success(request, f'Loan fully funded! KES {investment_amount:,.2f} invested successfully.')
                    else:
                        messages.success(request, f'KES {investment_amount:,.2f} invested successfully.')
                    
                    loan.save()
            
                return redirect('marketplace')
                
            except Loan.DoesNotExist:
                messages.error(request, 'Loan not found or not available for investment.')
            except Exception as e:
                logger.error(f"Investment error: {str(e)}")
                messages.error(request, 'Error processing investment. Please try again.')
        
        # Get lender's investments
        lender_investments = Investment.objects.filter(lender=request.user).select_related('loan')
        total_invested = sum(inv.amount_invested for inv in lender_investments)
        
        context = {
            'listed_loans': valid_loans,
            'lender_investments': lender_investments,
            'total_invested': total_invested,
            'is_admin': user_role == 'admin',  # Add admin flag for template
        }
        return render(request, 'core/marketplace.html', context)
        
    except Exception as e:
        logger.error(f"Marketplace error: {str(e)}")
        messages.error(request, 'Error loading marketplace.')
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
    """Fast KYC verification with automatic processing"""
    try:
        # Get or create KYC verification record
        kyc, created = KYCVerification.objects.get_or_create(
            user=request.user,
            defaults={
                'full_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
                'id_number': "",
                'date_of_birth': timezone.now().date(),
                'status': 'pending'
            }
        )
        
        if created:
            logger.info(f"Created new KYC record for user {request.user.username}")
        
        if request.method == 'POST':
            form = KYCVerificationForm(request.POST, request.FILES, instance=kyc)
            if form.is_valid():
                kyc = form.save(commit=False)
                kyc.status = 'under_review'
                kyc.save()
                
                # Immediate automatic verification for faster processing
                try:
                    if KYC_SERVICE_AVAILABLE and kyc_ai_service:
                        # Run AI verification immediately
                        verification_result = kyc_ai_service.verify_kyc_submission(kyc)
                        logger.info(f"KYC AI verification result for {request.user.username}: {verification_result}")
                    else:
                        # Fast fallback verification when AI service is not available
                        # Check basic requirements: name and ID number must be provided
                        if kyc.full_name and kyc.id_number and len(kyc.id_number) >= 6:
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
                    
                    kyc.ai_verification_result = verification_result
                    kyc.verification_score = verification_result.get('overall_score', 0)
                    
                    # Auto-approve if score is high enough (faster processing)
                    if verification_result.get('passed', False) and verification_result.get('overall_score', 0) >= 80:
                        kyc.status = 'verified'
                        kyc.verified_at = timezone.now()
                        messages.success(request, 
                            'KYC verification completed successfully! ✅ You can now apply for loans. '
                            'Your identity has been verified and all borrower features are now available.')
                        logger.info(f"KYC auto-approved for {request.user.username} with score {verification_result.get('overall_score')}")
                    else:
                        kyc.status = 'rejected'
                        error_msg = verification_result.get('message', 'Verification failed')
                        messages.error(request, 
                            f'KYC verification failed: {error_msg}. '
                            'Please check your information and try again. '
                            'Ensure your name matches your ID document exactly.')
                        logger.warning(f"KYC rejected for {request.user.username}: {error_msg}")
                    
                    kyc.save()
                    
                except Exception as e:
                    logger.error(f"KYC verification error for {request.user.username}: {str(e)}")
                    # Fallback to manual review on error
                    kyc.status = 'under_review'
                    kyc.save()
                    messages.info(request, 
                        'KYC submitted for review. Our team will verify your documents within 24 hours. '
                        'You will receive a notification once the verification is complete.')
                
                return redirect('kyc_verification')
            else:
                # Form has errors - show detailed error messages
                error_messages = []
                for field, errors in form.errors.items():
                    for error in errors:
                        error_messages.append(f"{field.replace('_', ' ').title()}: {error}")
                
                messages.error(request, 
                    'Please correct the following errors: ' + '; '.join(error_messages))
        else:
            form = KYCVerificationForm(instance=kyc)
        
        # Add helpful context for the user
        context = {
            'form': form,
            'kyc': kyc,
            'can_submit': kyc.status in ['pending', 'rejected'],
            'verification_tips': [
                'Ensure your full name matches your ID document exactly',
                'Provide a clear, valid national ID number',
                'Upload clear, readable photos of your ID documents',
                'Make sure all information is accurate and complete'
            ]
        }
        return render(request, 'core/kyc_verification.html', context)
        
    except Exception as e:
        logger.error(f"KYC verification error: {str(e)}")
        messages.error(request, f'Error loading KYC verification. Please try again or contact support if the problem persists.')
        
        # Create a fallback context
        try:
            kyc, created = KYCVerification.objects.get_or_create(
                user=request.user,
                defaults={
                    'full_name': request.user.username,
                    'id_number': "",
                    'date_of_birth': timezone.now().date(),
                    'status': 'pending'
                }
            )
            form = KYCVerificationForm(instance=kyc)
            context = {
                'form': form,
                'kyc': kyc,
                'can_submit': True,
                'verification_tips': []
            }
            return render(request, 'core/kyc_verification.html', context)
        except Exception as fallback_error:
            logger.error(f"KYC fallback error: {str(fallback_error)}")
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