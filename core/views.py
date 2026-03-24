from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal
import logging
import json
from .models import CustomUser, Collateral, Loan, Investment, WalletTransaction, Commission, Payment
from .forms import CustomUserCreationForm, CollateralForm, LoanApplicationForm, InvestmentForm
from .supabase_client import supabase
from .services import supabase_service

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
    """Optimized home page with fast redirects"""
    if request.user.is_authenticated:
        # Quick admin email check
        if request.user.email == 'sammyseth260@gmail.com' and request.user.role != 'admin':
            request.user.role = 'admin'
            request.user.is_staff = True
            request.user.is_superuser = True
            request.user.is_promoted_admin = True
            request.user.save()
        
        # Fast role-based redirect
        if hasattr(request.user, 'role') and request.user.role:
            role_redirects = {
                'borrower': 'borrower_dashboard',
                'lender': 'marketplace', 
                'agent': 'agent_panel',
                'admin': 'admin_dashboard'
            }
            redirect_url = role_redirects.get(request.user.role)
            if redirect_url:
                return redirect(redirect_url)
        else:
            messages.error(request, 'Account not configured. Contact support.')
    
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
@login_required
def borrower_dashboard(request):
    """Borrower dashboard with loan overview and application form"""
    try:
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user:
            messages.error(request, 'User not found.')
            return redirect('home')
        
        # Allow admin to access borrower dashboard
        user_role = current_user.get('role')
        if user_role not in ['borrower', 'admin']:
            messages.error(request, 'Access denied. Borrowers only.')
            return redirect('home')
        
        # Get borrower's loans from Supabase
        loans = supabase_service.get_loans_by_borrower(current_user['id']) or []
        
        # Enrich loans with details
        enriched_loans = []
        total_outstanding = Decimal('0')
        
        for loan in loans:
            loan_details = supabase_service.get_loan_with_details(loan['id'])
            if loan_details:
                enriched_loans.append(loan_details)
                
                # Calculate outstanding amount for active loans
                if loan_details.get('status') == 'active':
                    total_repayment = Decimal(str(loan_details.get('total_repayment', 0)))
                    funded_amount = Decimal(str(loan_details.get('funded_amount', 0)))
                    total_outstanding += (total_repayment - funded_amount)
        
        # Handle loan application
        if request.method == 'POST':
            collateral_form = CollateralForm(request.POST)
            loan_form = LoanApplicationForm(request.POST)
            
            if collateral_form.is_valid() and loan_form.is_valid():
                try:
                    # Create collateral in Supabase
                    collateral_result = supabase_service.create_collateral(
                        user_id=current_user['id'],
                        item_type=collateral_form.cleaned_data['item_type'],
                        brand_model=collateral_form.cleaned_data['brand_model'],
                        market_value=float(collateral_form.cleaned_data['market_value'])
                    )
                    
                    if not collateral_result:
                        messages.error(request, 'Error creating collateral. Please try again.')
                        return redirect('borrower_dashboard')
                    
                    collateral_id = collateral_result[0]['id']
                    market_value = float(collateral_form.cleaned_data['market_value'])
                    
                    # Validate loan amount against 30/50 rule
                    from .services import LoanCalculatorService
                    max_loan_amount = LoanCalculatorService.calculate_max_loan_amount(market_value)
                    requested_amount = loan_form.cleaned_data['principal_amount']
                    
                    if requested_amount > max_loan_amount:
                        messages.error(request, 
                            f'Requested amount (KES {requested_amount:,.2f}) exceeds maximum '
                            f'allowed (KES {max_loan_amount:,.2f}) based on collateral value.')
                        # Note: In a real implementation, you'd want to delete the collateral here
                    else:
                        # Create loan in Supabase
                        loan_result = supabase_service.create_loan(
                            borrower_id=current_user['id'],
                            collateral_id=collateral_id,
                            principal_amount=float(requested_amount),
                            interest_rate=float(loan_form.cleaned_data.get('interest_rate', 13.00)),
                            duration_months=int(loan_form.cleaned_data['duration_months'])
                        )
                        
                        if loan_result:
                            messages.success(request, 
                                'Loan application submitted! Please visit a station agent to verify your collateral.')
                        else:
                            messages.error(request, 'Error creating loan. Please try again.')
                        
                        return redirect('borrower_dashboard')
                        
                except Exception as e:
                    logger.error(f"Loan application error: {str(e)}")
                    messages.error(request, 'Error processing loan application. Please try again.')
        else:
            collateral_form = CollateralForm()
            loan_form = LoanApplicationForm()
        
        context = {
            'loans': enriched_loans,
            'total_outstanding': total_outstanding,
            'collateral_form': collateral_form,
            'loan_form': loan_form,
        }
        return render(request, 'core/borrower_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Borrower dashboard error: {str(e)}")
        messages.error(request, 'Error loading dashboard.')
        return redirect('home')


@login_required
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
        }
        return render(request, 'core/agent_panel.html', context)
        
    except Exception as e:
        logger.error(f"Agent panel error: {str(e)}")
        messages.error(request, 'Error loading agent panel.')
        return redirect('home')


@login_required
@login_required
def marketplace(request):
    """Lender marketplace showing available loans"""
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
        
        # Get listed loans from Supabase
        listed_loans = supabase_service.get_listed_loans() or []
        
        # Enrich loans with details and filter expired ones
        valid_loans = []
        for loan in listed_loans:
            # Get loan with full details
            loan_details = supabase_service.get_loan_with_details(loan['id'])
            if loan_details:
                # Check if loan is expired (7 days)
                from datetime import datetime, timezone as dt_timezone
                created_at = datetime.fromisoformat(loan_details['created_at'].replace('Z', '+00:00'))
                days_passed = (datetime.now(dt_timezone.utc) - created_at).days
                
                if days_passed <= 7:
                    valid_loans.append(loan_details)
                else:
                    # Auto-expire loans that have passed 7-day window
                    supabase_service.update_loan_status(loan['id'], 'cancelled')
        
        # Handle investment
        if request.method == 'POST':
            loan_id = request.POST.get('loan_id')
            investment_amount = Decimal(request.POST.get('investment_amount', '0'))
            
            loan = supabase_service.get_loan_by_id(loan_id)
            if not loan or loan.get('status') != 'listed':
                messages.error(request, 'Loan not found or not available for investment.')
                return redirect('marketplace')
            
            # Validate investment amount
            remaining_amount = Decimal(str(loan['principal_amount'])) - Decimal(str(loan['funded_amount']))
            if investment_amount > remaining_amount:
                messages.error(request, f'Investment amount exceeds remaining funding needed (KES {remaining_amount:,.2f})')
            elif investment_amount <= 0:
                messages.error(request, 'Investment amount must be greater than zero.')
            else:
                try:
                    # Check if lender already invested in this loan
                    existing_investments = supabase_service.get_investments_by_loan(loan_id) or []
                    existing_investment = None
                    for inv in existing_investments:
                        if inv.get('lender_id') == current_user['id']:
                            existing_investment = inv
                            break
                    
                    if existing_investment:
                        # Update existing investment (this would need a custom update method)
                        messages.info(request, 'You have already invested in this loan.')
                    else:
                        # Create new investment
                        investment_result = supabase_service.create_investment(
                            lender_id=current_user['id'],
                            loan_id=loan_id,
                            amount_invested=float(investment_amount)
                        )
                        
                        if investment_result:
                            # Update loan funded amount
                            new_funded_amount = float(loan['funded_amount']) + float(investment_amount)
                            supabase_service.update_loan_funding(loan_id, new_funded_amount)
                            
                            # Check if loan is fully funded
                            if new_funded_amount >= float(loan['principal_amount']):
                                supabase_service.update_loan_status(loan_id, 'active')
                                messages.success(request, f'Loan fully funded! KES {investment_amount:,.2f} invested successfully.')
                            else:
                                messages.success(request, f'KES {investment_amount:,.2f} invested successfully.')
                        else:
                            messages.error(request, 'Error processing investment. Please try again.')
                    
                except Exception as e:
                    logger.error(f"Investment error: {str(e)}")
                    messages.error(request, 'Error processing investment. Please try again.')
                
                return redirect('marketplace')
        
        context = {
            'listed_loans': valid_loans,
        }
        return render(request, 'core/marketplace.html', context)
        
    except Exception as e:
        logger.error(f"Marketplace error: {str(e)}")
        messages.error(request, 'Error loading marketplace.')
        return redirect('home')


@login_required
@login_required
def loan_detail(request, loan_id):
    """Detailed view of a specific loan with proper error handling"""
    try:
        # Get loan with all details from Supabase
        loan = supabase_service.get_loan_with_details(loan_id)
        
        if not loan:
            messages.error(request, 'Loan not found.')
            return redirect('marketplace')
        
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user:
            messages.error(request, 'User session error. Please login again.')
            return redirect('login')
        
        # Check permissions
        borrower_id = loan.get('borrower_id')
        user_role = current_user.get('role')
        user_id = current_user.get('id')
        
        if (user_id != borrower_id and user_role not in ['agent', 'lender', 'admin']):
            messages.error(request, 'Access denied.')
            # Redirect based on user role
            role_redirects = {
                'borrower': 'borrower_dashboard',
                'lender': 'marketplace',
                'agent': 'agent_panel',
                'admin': 'admin_dashboard'
            }
            return redirect(role_redirects.get(user_role, 'home'))
        
        # Get investments for this loan
        investments = supabase_service.get_investments_by_loan(loan_id) or []
        
        # Enrich investments with lender details
        for investment in investments:
            lender = supabase_service.get_user_by_id(investment.get('lender_id'))
            if lender:
                investment['lender'] = lender
        
        context = {
            'loan': loan,
            'investments': investments,
        }
        return render(request, 'core/loan_detail.html', context)
        
    except Exception as e:
        logger.error(f"Loan detail error: {str(e)}")
        messages.error(request, 'Error loading loan details.')
        return redirect('marketplace')


@login_required
@login_required
def admin_dashboard(request):
    """Admin dashboard with access to all system data"""
    try:
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user or (current_user.get('role') != 'admin' and current_user.get('email') != 'sammyseth260@gmail.com'):
            messages.error(request, 'Access denied. Administrators only.')
            return redirect('home')
        
        # Get dashboard statistics from Supabase
        stats = supabase_service.get_dashboard_stats()
        
        # Get recent activities
        all_loans = supabase_service.get_all_loans() or []
        all_investments = supabase_service.get_all_investments() or []
        all_users = supabase_service.get_all_users() or []
        
        # Sort and limit recent activities
        recent_loans = sorted(all_loans, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
        recent_investments = sorted(all_investments, key=lambda x: x.get('date', ''), reverse=True)[:10]
        recent_users = sorted(all_users, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
        
        # Enrich recent loans with details
        enriched_recent_loans = []
        for loan in recent_loans:
            loan_details = supabase_service.get_loan_with_details(loan['id'])
            if loan_details:
                enriched_recent_loans.append(loan_details)
        
        # Enrich recent investments with details
        enriched_recent_investments = []
        for investment in recent_investments:
            # Get lender details
            lender = supabase_service.get_user_by_id(investment.get('lender_id'))
            loan = supabase_service.get_loan_by_id(investment.get('loan_id'))
            if lender and loan:
                investment['lender'] = lender
                investment['loan'] = loan
                enriched_recent_investments.append(investment)
        
        # Get collateral statistics
        pending_collaterals = supabase_service.get_pending_collaterals() or []
        all_collaterals = supabase_service.get_all_collaterals() or []
        
        context = {
            'total_users': stats.get('total_users', 0),
            'total_borrowers': stats.get('total_borrowers', 0),
            'total_lenders': stats.get('total_lenders', 0),
            'total_agents': stats.get('total_agents', 0),
            'total_collateral': len(all_collaterals),
            'pending_collateral': len(pending_collaterals),
            'verified_collateral': len(all_collaterals) - len(pending_collaterals),
            'total_loans': stats.get('total_loans', 0),
            'active_loans': stats.get('active_loans', 0),
            'listed_loans': stats.get('listed_loans', 0),
            'pending_loans': len([l for l in all_loans if l.get('status') == 'pending_collateral']),
            'total_investments': stats.get('total_investments', 0),
            'total_invested_amount': stats.get('total_funded_amount', 0),
            'recent_loans': enriched_recent_loans,
            'recent_investments': enriched_recent_investments,
            'recent_users': recent_users,
            'total_loan_amount': stats.get('total_loan_amount', 0),
            'total_funded_amount': stats.get('total_funded_amount', 0),
        }
        return render(request, 'core/admin_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Admin dashboard error: {str(e)}")
        messages.error(request, 'Error loading admin dashboard.')
        return redirect('home')


@login_required
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