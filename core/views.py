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
    """Custom login view with enhanced logging and error handling"""
    template_name = 'registration/login.html'
    
    def form_valid(self, form):
        username = form.cleaned_data.get('username')
        logger.info(f"Login form valid for user: {username}")
        
        # Authenticate user
        user = authenticate(
            self.request,
            username=username,
            password=form.cleaned_data.get('password')
        )
        
        if user is not None:
            logger.info(f"User {username} authenticated successfully")
            
            # Special check for admin email - auto-promote to admin if needed
            if user.email == 'sammyseth260@gmail.com' and user.role != 'admin':
                logger.info(f"Auto-promoting user {username} to admin based on email")
                user.role = 'admin'
                user.is_staff = True
                user.is_superuser = True
                user.is_promoted_admin = True
                user.save()
            
            # Check if user has a role
            if not hasattr(user, 'role') or not user.role:
                logger.error(f"User {username} has no role assigned")
                messages.error(self.request, 'Your account is not properly configured. Please contact support.')
                return self.form_invalid(form)
            
            # Log the user in
            login(self.request, user)
            logger.info(f"User {username} logged in with role: {user.role}")
            
            # Add success message
            messages.success(self.request, f'Welcome back, {user.username}!')
            
            # Redirect based on role
            if user.role == 'admin':
                return redirect('admin_dashboard')
            elif user.role == 'borrower':
                return redirect('borrower_dashboard')
            elif user.role == 'lender':
                return redirect('marketplace')
            elif user.role == 'agent':
                return redirect('agent_panel')
            else:
                logger.warning(f"Unknown role for user {username}: {user.role}")
                return redirect('home')
        else:
            logger.warning(f"Authentication failed for user: {username}")
            messages.error(self.request, 'Invalid username or password.')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        logger.warning(f"Login form invalid: {form.errors}")
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
    """Home page - redirect based on user role or show landing page"""
    if request.user.is_authenticated:
        logger.info(f"Authenticated user {request.user.username} accessing home page")
        
        # Special check for admin email - auto-promote to admin if needed
        if request.user.email == 'sammyseth260@gmail.com' and request.user.role != 'admin':
            logger.info(f"Auto-promoting user {request.user.username} to admin based on email")
            
            # Update in Supabase
            supabase_user = supabase_service.get_user_by_username(request.user.username)
            if supabase_user:
                supabase_service.update_user(supabase_user['id'], {
                    'role': 'admin',
                    'is_staff': True,
                    'is_superuser': True,
                    'is_promoted_admin': True
                })
            
            # Update Django user
            request.user.role = 'admin'
            request.user.is_staff = True
            request.user.is_superuser = True
            request.user.is_promoted_admin = True
            request.user.save()
        
        # Check if user has a role
        if not hasattr(request.user, 'role') or not request.user.role:
            logger.error(f"User {request.user.username} has no role assigned")
            messages.error(request, 'Your account is not properly configured. Please contact support.')
            return render(request, 'core/home.html')
        
        logger.info(f"User {request.user.username} has role: {request.user.role}")
        
        # Redirect based on role
        if request.user.role == 'borrower':
            return redirect('borrower_dashboard')
        elif request.user.role == 'lender':
            return redirect('marketplace')
        elif request.user.role == 'agent':
            return redirect('agent_panel')
        elif request.user.role == 'admin':
            return redirect('admin_dashboard')
        else:
            logger.warning(f"Unknown role for user {request.user.username}: {request.user.role}")
            messages.warning(request, f'Unknown user role: {request.user.role}. Please contact support.')
    
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
                
                # Special handling for admin email
                if email == 'sammyseth260@gmail.com':
                    # Check if admin user already exists
                    existing_user = supabase_service.get_user_by_email(email)
                    if existing_user:
                        # Update existing admin user with new details
                        update_data = {
                            'username': username,
                            'first_name': first_name,
                            'last_name': last_name,
                            'role': 'admin',  # Force admin role
                            'phone_number': phone_number,
                            'national_id': national_id,
                            'is_staff': True,
                            'is_superuser': True,
                            'is_promoted_admin': True
                        }
                        
                        supabase_result = supabase_service.update_user(existing_user['id'], update_data)
                        
                        if supabase_result:
                            logger.info(f"Admin user {email} updated successfully")
                            messages.success(request, f'Admin account updated for {username}! You can now log in.')
                            return redirect('login')
                        else:
                            messages.error(request, 'Error updating admin account. Please try again.')
                            return render(request, 'registration/register.html', {'form': form})
                
                # Check if user already exists in Supabase (for non-admin emails)
                existing_user = supabase_service.get_user_by_username(username)
                if existing_user:
                    messages.error(request, 'Username already exists.')
                    return render(request, 'registration/register.html', {'form': form})
                
                existing_email = supabase_service.get_user_by_email(email)
                if existing_email:
                    messages.error(request, 'Email already exists.')
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
        if not current_user or current_user.get('role') != 'borrower':
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
        if not current_user or current_user.get('role') != 'agent':
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
        if not current_user or current_user.get('role') != 'lender':
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
    """Detailed view of a specific loan"""
    try:
        # Get loan with all details from Supabase
        loan = supabase_service.get_loan_with_details(loan_id)
        
        if not loan:
            messages.error(request, 'Loan not found.')
            return redirect('marketplace')
        
        # Get current user from Supabase
        current_user = supabase_service.get_user_by_username(request.user.username)
        if not current_user:
            messages.error(request, 'User not found.')
            return redirect('home')
        
        # Check permissions
        borrower_id = loan.get('borrower_id')
        user_role = current_user.get('role')
        user_id = current_user.get('id')
        
        if (user_id != borrower_id and user_role not in ['agent', 'lender', 'admin']):
            messages.error(request, 'Access denied.')
            return redirect('home')
        
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
def admin_lender_view(request):
    """Admin view of lender marketplace"""
    if request.user.role != 'admin' and request.user.email != 'sammyseth260@gmail.com':
        messages.error(request, 'Access denied. Administrators only.')
        return redirect('home')
    
    # Get all lenders and their investments
    lenders = CustomUser.objects.filter(role='lender').prefetch_related('investment_set__loan')
    listed_loans = Loan.objects.filter(status='listed').select_related('borrower', 'collateral')
    
    context = {
        'lenders': lenders,
        'listed_loans': listed_loans,
        'is_admin_view': True,
    }
    return render(request, 'core/admin_lender_view.html', context)


@login_required
def admin_agent_view(request):
    """Admin view of agent panel"""
    if request.user.role != 'admin' and request.user.email != 'sammyseth260@gmail.com':
        messages.error(request, 'Access denied. Administrators only.')
        return redirect('home')
    
    # Get all agents and pending collateral
    agents = CustomUser.objects.filter(role='agent')
    pending_collaterals = Collateral.objects.filter(status='pending').select_related('user')
    all_collaterals = Collateral.objects.all().select_related('user').order_by('-created_at')
    
    context = {
        'agents': agents,
        'pending_collaterals': pending_collaterals,
        'all_collaterals': all_collaterals,
        'is_admin_view': True,
    }
    return render(request, 'core/admin_agent_view.html', context)

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
def admin_commissions_payouts(request):
    """Admin view to manage agent commissions and payouts"""
    if request.user.role != 'admin' and request.user.email != 'sammyseth260@gmail.com':
        messages.error(request, 'Access denied. Administrators only.')
        return redirect('home')
    
    # Handle commission payouts
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'pay_commission':
            commission_id = request.POST.get('commission_id')
            commission = get_object_or_404(Commission, id=commission_id)
            
            if not commission.is_paid:
                # Add commission to agent's wallet
                commission.agent.add_to_wallet(
                    commission.amount, 
                    f'Commission for Loan #{commission.loan.id}'
                )
                
                # Mark commission as paid
                commission.is_paid = True
                commission.paid_at = timezone.now()
                commission.save()
                
                messages.success(request, f'Commission of KES {commission.amount} paid to {commission.agent.username}.')
        
        elif action == 'pay_all_pending':
            pending_commissions = Commission.objects.filter(is_paid=False)
            total_paid = 0
            
            for commission in pending_commissions:
                commission.agent.add_to_wallet(
                    commission.amount,
                    f'Commission for Loan #{commission.loan.id}'
                )
                commission.is_paid = True
                commission.paid_at = timezone.now()
                commission.save()
                total_paid += commission.amount
            
            messages.success(request, f'Paid KES {total_paid} in total commissions to {pending_commissions.count()} agents.')
        
        return redirect('admin_commissions_payouts')
    
    # Get commission data
    pending_commissions = Commission.objects.filter(is_paid=False).select_related('agent', 'loan')
    paid_commissions = Commission.objects.filter(is_paid=True).select_related('agent', 'loan').order_by('-paid_at')[:20]
    
    # Agent statistics
    agents = CustomUser.objects.filter(role='agent')
    agent_stats = []
    
    for agent in agents:
        total_commissions = Commission.objects.filter(agent=agent).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        paid_commissions_sum = Commission.objects.filter(agent=agent, is_paid=True).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        pending_commissions_sum = Commission.objects.filter(agent=agent, is_paid=False).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        agent_stats.append({
            'agent': agent,
            'total_commissions': total_commissions,
            'paid_commissions': paid_commissions_sum,
            'pending_commissions': pending_commissions_sum,
            'wallet_balance': agent.wallet_balance,
        })
    
    context = {
        'pending_commissions': pending_commissions,
        'paid_commissions': paid_commissions,
        'agent_stats': agent_stats,
        'total_pending': pending_commissions.aggregate(total=Sum('amount'))['total'] or 0,
    }
    return render(request, 'core/admin_commissions_payouts.html', context)


@login_required
def admin_payments_management(request):
    """Admin view to manage loan payments and next payment tracking"""
    if request.user.role != 'admin' and request.user.email != 'sammyseth260@gmail.com':
        messages.error(request, 'Access denied. Administrators only.')
        return redirect('home')
    
    # Handle payment processing
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'process_payment':
            loan_id = request.POST.get('loan_id')
            amount = Decimal(request.POST.get('amount', '0'))
            payment_type = request.POST.get('payment_type', 'monthly')
            
            loan = get_object_or_404(Loan, id=loan_id)
            
            if amount > 0:
                # Create payment record
                payment = Payment.objects.create(
                    loan=loan,
                    amount=amount,
                    payment_type=payment_type,
                    processed_by=request.user
                )
                
                # Update loan payment tracking
                loan.payments_made += 1
                
                # Set next payment date
                if payment_type == 'monthly':
                    loan.next_payment_date = timezone.now() + timedelta(days=30)
                elif payment_type == 'full':
                    loan.status = 'paid'
                    loan.next_payment_date = None
                
                loan.save()
                
                # Distribute returns to lenders
                investments = Investment.objects.filter(loan=loan)
                for investment in investments:
                    monthly_return = investment.calculate_monthly_return()
                    investment.lender.add_to_wallet(
                        monthly_return,
                        f'Monthly return from Loan #{loan.id}'
                    )
                    investment.total_returns_paid += monthly_return
                    investment.save()
                
                messages.success(request, f'Payment of KES {amount} processed for Loan #{loan.id}.')
        
        return redirect('admin_payments_management')
    
    # Get active loans with payment info
    active_loans = Loan.objects.filter(status='active').select_related('borrower', 'collateral')
    
    # Get upcoming payments (next 30 days)
    upcoming_payments = []
    overdue_payments = []
    
    for loan in active_loans:
        if loan.next_payment_date:
            days_until_payment = loan.get_days_until_payment()
            payment_info = {
                'loan': loan,
                'days_until_payment': days_until_payment,
                'payment_amount': loan.get_next_payment_amount(),
                'is_overdue': loan.next_payment_date < timezone.now(),
            }
            
            if payment_info['is_overdue']:
                overdue_payments.append(payment_info)
            else:
                upcoming_payments.append(payment_info)
    
    # Recent payments
    recent_payments = Payment.objects.all().select_related('loan', 'processed_by').order_by('-payment_date')[:20]
    
    context = {
        'active_loans': active_loans,
        'upcoming_payments': upcoming_payments[:10],  # Next 10 payments
        'overdue_payments': overdue_payments,
        'recent_payments': recent_payments,
        'total_active_loans': active_loans.count(),
        'total_overdue': len(overdue_payments),
    }
    return render(request, 'core/admin_payments_management.html', context)


@login_required
def admin_wallet_management(request):
    """Admin view to manage user wallets"""
    if request.user.role != 'admin' and request.user.email != 'sammyseth260@gmail.com':
        messages.error(request, 'Access denied. Administrators only.')
        return redirect('home')
    
    # Get wallet statistics
    all_users = CustomUser.objects.all()
    
    wallet_stats = {
        'total_wallet_balance': all_users.aggregate(total=Sum('wallet_balance'))['total'] or 0,
        'total_earnings': all_users.aggregate(total=Sum('total_earnings'))['total'] or 0,
        'borrowers_balance': all_users.filter(role='borrower').aggregate(total=Sum('wallet_balance'))['total'] or 0,
        'lenders_balance': all_users.filter(role='lender').aggregate(total=Sum('wallet_balance'))['total'] or 0,
        'agents_balance': all_users.filter(role='agent').aggregate(total=Sum('wallet_balance'))['total'] or 0,
    }
    
    # Recent wallet transactions
    recent_transactions = WalletTransaction.objects.all().select_related('user').order_by('-created_at')[:50]
    
    # Users with highest wallet balances
    top_wallets = all_users.filter(wallet_balance__gt=0).order_by('-wallet_balance')[:20]
    
    context = {
        'wallet_stats': wallet_stats,
        'recent_transactions': recent_transactions,
        'top_wallets': top_wallets,
    }
    return render(request, 'core/admin_wallet_management.html', context)

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