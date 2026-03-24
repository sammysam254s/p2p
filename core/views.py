from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
import logging
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
    
    def get(self, request, *args, **kwargs):
        """Handle GET requests for logout"""
        return self.post(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        """Handle POST requests for logout"""
        if request.user.is_authenticated:
            username = request.user.username
            logger.info(f"User {username} logging out")
            messages.success(request, 'You have been logged out successfully.')
        
        return super().post(request, *args, **kwargs)


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
                
                # Check if user already exists in Supabase
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
def borrower_dashboard(request):
    """Borrower dashboard with loan overview and application form"""
    if request.user.role != 'borrower':
        messages.error(request, 'Access denied. Borrowers only.')
        return redirect('home')
    
    # Get borrower's loans
    loans = Loan.objects.filter(borrower=request.user).order_by('-created_at')
    
    # Calculate totals
    active_loans = loans.filter(status='active')
    total_outstanding = sum(loan.calculate_total_repayment() - loan.funded_amount 
                          for loan in active_loans)
    
    # Handle loan application
    if request.method == 'POST':
        collateral_form = CollateralForm(request.POST)
        loan_form = LoanApplicationForm(request.POST)
        
        if collateral_form.is_valid() and loan_form.is_valid():
            # Create collateral
            collateral = collateral_form.save(commit=False)
            collateral.user = request.user
            collateral.save()
            
            # Validate loan amount against 30/50 rule
            max_loan_amount = collateral.calculate_max_loan_amount()
            requested_amount = loan_form.cleaned_data['principal_amount']
            
            if requested_amount > max_loan_amount:
                messages.error(request, 
                    f'Requested amount (KES {requested_amount:,.2f}) exceeds maximum '
                    f'allowed (KES {max_loan_amount:,.2f}) based on collateral value.')
                collateral.delete()  # Remove the collateral if loan validation fails
            else:
                # Create loan
                loan = loan_form.save(commit=False)
                loan.borrower = request.user
                loan.collateral = collateral
                loan.save()
                
                messages.success(request, 
                    'Loan application submitted! Please visit a station agent to verify your collateral.')
                return redirect('borrower_dashboard')
    else:
        collateral_form = CollateralForm()
        loan_form = LoanApplicationForm()
    
    context = {
        'loans': loans,
        'total_outstanding': total_outstanding,
        'collateral_form': collateral_form,
        'loan_form': loan_form,
    }
    return render(request, 'core/borrower_dashboard.html', context)


@login_required
def agent_panel(request):
    """Station agent panel for collateral verification"""
    if request.user.role != 'agent':
        messages.error(request, 'Access denied. Station agents only.')
        return redirect('home')
    
    # Get pending collateral items
    pending_collaterals = Collateral.objects.filter(status='pending').select_related('user')
    
    # Handle verification
    if request.method == 'POST':
        collateral_id = request.POST.get('collateral_id')
        collateral = get_object_or_404(Collateral, id=collateral_id, status='pending')
        
        # Update collateral status
        collateral.status = 'verified'
        collateral.verification_date = timezone.now()
        collateral.save()
        
        # Update associated loan status to 'listed'
        try:
            loan = Loan.objects.get(collateral=collateral)
            loan.status = 'listed'
            loan.save()
            messages.success(request, f'Collateral verified and loan listed for {collateral.user.username}')
        except Loan.DoesNotExist:
            messages.error(request, 'No associated loan found for this collateral.')
        
        return redirect('agent_panel')
    
    context = {
        'pending_collaterals': pending_collaterals,
    }
    return render(request, 'core/agent_panel.html', context)


@login_required
def marketplace(request):
    """Lender marketplace showing available loans"""
    if request.user.role != 'lender':
        messages.error(request, 'Access denied. Lenders only.')
        return redirect('home')
    
    # Get listed loans that are not expired
    listed_loans = []
    for loan in Loan.objects.filter(status='listed').select_related('borrower', 'collateral'):
        if not loan.is_expired():
            listed_loans.append(loan)
        else:
            # Auto-expire loans that have passed 7-day window
            loan.status = 'cancelled'
            loan.save()
    
    # Handle investment
    if request.method == 'POST':
        loan_id = request.POST.get('loan_id')
        investment_amount = Decimal(request.POST.get('investment_amount', '0'))
        
        loan = get_object_or_404(Loan, id=loan_id, status='listed')
        
        # Validate investment amount
        remaining_amount = loan.principal_amount - loan.funded_amount
        if investment_amount > remaining_amount:
            messages.error(request, f'Investment amount exceeds remaining funding needed (KES {remaining_amount:,.2f})')
        elif investment_amount <= 0:
            messages.error(request, 'Investment amount must be greater than zero.')
        else:
            # Check if lender already invested in this loan
            existing_investment = Investment.objects.filter(lender=request.user, loan=loan).first()
            if existing_investment:
                # Update existing investment
                existing_investment.amount_invested += investment_amount
                existing_investment.save()
            else:
                # Create new investment
                Investment.objects.create(
                    lender=request.user,
                    loan=loan,
                    amount_invested=investment_amount
                )
            
            # Update loan funded amount
            loan.funded_amount += investment_amount
            
            # Check if loan is fully funded
            if loan.is_fully_funded():
                loan.status = 'active'
                messages.success(request, f'Loan fully funded! KES {investment_amount:,.2f} invested successfully.')
            else:
                messages.success(request, f'KES {investment_amount:,.2f} invested successfully.')
            
            loan.save()
            return redirect('marketplace')
    
    context = {
        'listed_loans': listed_loans,
    }
    return render(request, 'core/marketplace.html', context)


@login_required
def loan_detail(request, loan_id):
    """Detailed view of a specific loan"""
    loan = get_object_or_404(Loan, id=loan_id)
    
    # Check permissions
    if (request.user != loan.borrower and 
        request.user.role not in ['agent', 'lender']):
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Get investments for this loan
    investments = Investment.objects.filter(loan=loan).select_related('lender')
    
    context = {
        'loan': loan,
        'investments': investments,
    }
    return render(request, 'core/loan_detail.html', context)


@login_required
def admin_dashboard(request):
    """Admin dashboard with access to all system data"""
    if request.user.role != 'admin' and request.user.email != 'sammyseth260@gmail.com':
        messages.error(request, 'Access denied. Administrators only.')
        return redirect('home')
    
    # Get all system statistics
    total_users = CustomUser.objects.count()
    total_borrowers = CustomUser.objects.filter(role='borrower').count()
    total_lenders = CustomUser.objects.filter(role='lender').count()
    total_agents = CustomUser.objects.filter(role='agent').count()
    
    total_collateral = Collateral.objects.count()
    pending_collateral = Collateral.objects.filter(status='pending').count()
    verified_collateral = Collateral.objects.filter(status='verified').count()
    
    total_loans = Loan.objects.count()
    active_loans = Loan.objects.filter(status='active').count()
    listed_loans = Loan.objects.filter(status='listed').count()
    pending_loans = Loan.objects.filter(status='pending_collateral').count()
    
    total_investments = Investment.objects.count()
    total_invested_amount = Investment.objects.aggregate(
        total=Sum('amount_invested')
    )['total'] or 0
    
    # Recent activities
    recent_loans = Loan.objects.select_related('borrower', 'collateral').order_by('-created_at')[:10]
    recent_investments = Investment.objects.select_related('lender', 'loan').order_by('-date')[:10]
    recent_users = CustomUser.objects.order_by('-date_joined')[:10]
    
    # Financial summary
    total_loan_amount = Loan.objects.aggregate(
        total=Sum('principal_amount')
    )['total'] or 0
    
    total_funded_amount = Loan.objects.aggregate(
        total=Sum('funded_amount')
    )['total'] or 0
    
    context = {
        'total_users': total_users,
        'total_borrowers': total_borrowers,
        'total_lenders': total_lenders,
        'total_agents': total_agents,
        'total_collateral': total_collateral,
        'pending_collateral': pending_collateral,
        'verified_collateral': verified_collateral,
        'total_loans': total_loans,
        'active_loans': active_loans,
        'listed_loans': listed_loans,
        'pending_loans': pending_loans,
        'total_investments': total_investments,
        'total_invested_amount': total_invested_amount,
        'recent_loans': recent_loans,
        'recent_investments': recent_investments,
        'recent_users': recent_users,
        'total_loan_amount': total_loan_amount,
        'total_funded_amount': total_funded_amount,
    }
    return render(request, 'core/admin_dashboard.html', context)


@login_required
def admin_borrower_view(request):
    """Admin view of borrower dashboard"""
    if request.user.role != 'admin' and request.user.email != 'sammyseth260@gmail.com':
        messages.error(request, 'Access denied. Administrators only.')
        return redirect('home')
    
    # Get all borrowers and their loans
    borrowers = CustomUser.objects.filter(role='borrower').prefetch_related('loan_set__collateral')
    
    context = {
        'borrowers': borrowers,
        'is_admin_view': True,
    }
    return render(request, 'core/admin_borrower_view.html', context)


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
def admin_users_management(request):
    """Admin view to manage all users"""
    if request.user.role != 'admin' and request.user.email != 'sammyseth260@gmail.com':
        messages.error(request, 'Access denied. Administrators only.')
        return redirect('home')
    
    # Handle user promotion to admin
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        
        if action == 'promote_admin' and user_id:
            user = get_object_or_404(CustomUser, id=user_id)
            user.role = 'admin'
            user.is_promoted_admin = True
            user.is_staff = True
            user.save()
            messages.success(request, f'{user.username} has been promoted to Administrator.')
        
        elif action == 'add_wallet_funds' and user_id:
            user = get_object_or_404(CustomUser, id=user_id)
            amount = Decimal(request.POST.get('amount', '0'))
            description = request.POST.get('description', 'Admin wallet credit')
            
            if amount > 0:
                user.add_to_wallet(amount, description)
                messages.success(request, f'KES {amount} added to {user.username}\'s wallet.')
        
        return redirect('admin_users_management')
    
    # Get all users with statistics
    all_users = CustomUser.objects.all().order_by('-date_joined')
    
    context = {
        'all_users': all_users,
        'total_users': all_users.count(),
        'borrowers_count': all_users.filter(role='borrower').count(),
        'lenders_count': all_users.filter(role='lender').count(),
        'agents_count': all_users.filter(role='agent').count(),
        'admins_count': all_users.filter(role='admin').count(),
    }
    return render(request, 'core/admin_users_management.html', context)


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
            
            # Check if username exists
            user_exists = CustomUser.objects.filter(username=username).exists()
            
            if user_exists:
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