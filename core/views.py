from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
from .models import CustomUser, Collateral, Loan, Investment
from .forms import CustomUserCreationForm, CollateralForm, LoanApplicationForm, InvestmentForm


def home(request):
    """Home page - redirect based on user role or show landing page"""
    if request.user.is_authenticated:
        if request.user.role == 'borrower':
            return redirect('borrower_dashboard')
        elif request.user.role == 'lender':
            return redirect('marketplace')
        elif request.user.role == 'agent':
            return redirect('agent_panel')
    return render(request, 'core/home.html')


def register(request):
    """User registration"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            return redirect('login')
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