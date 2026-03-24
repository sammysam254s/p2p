from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Collateral, Loan, Investment, KYCVerification


class KYCVerificationForm(forms.ModelForm):
    """Form for KYC verification submission"""
    
    class Meta:
        model = KYCVerification
        fields = ['full_name', 'id_number', 'date_of_birth', 'id_front_image', 
                 'id_back_image', 'selfie_image', 'signature_image']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your full name as on ID'
            }),
            'id_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your national ID number'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'full_name': 'Full Name (as on ID)',
            'id_number': 'National ID Number',
            'date_of_birth': 'Date of Birth',
            'id_front_image': 'ID Front Image',
            'id_back_image': 'ID Back Image',
            'selfie_image': 'Selfie Photo',
            'signature_image': 'Signature Image',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Check if Pillow is available for file fields
        try:
            from PIL import Image
            pillow_available = True
        except ImportError:
            pillow_available = False
        
        if pillow_available:
            # Use FileInput for image fields when Pillow is available
            self.fields['id_front_image'].widget = forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
            self.fields['id_back_image'].widget = forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
            self.fields['selfie_image'].widget = forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
            self.fields['signature_image'].widget = forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        else:
            # Use TextInput for image paths when Pillow is not available
            self.fields['id_front_image'].widget = forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Image path or URL'
            })
            self.fields['id_back_image'].widget = forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Image path or URL'
            })
            self.fields['selfie_image'].widget = forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Image path or URL'
            })
            self.fields['signature_image'].widget = forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Image path or URL'
            })
    
    def clean_id_number(self):
        id_number = self.cleaned_data.get('id_number')
        if len(id_number) < 7 or len(id_number) > 8:
            raise forms.ValidationError('ID number must be 7-8 digits long')
        return id_number


class CollateralVerificationForm(forms.ModelForm):
    """Form for agents to verify and update collateral market value"""
    
    class Meta:
        model = Collateral
        fields = ['agent_verified_value']
        widgets = {
            'agent_verified_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1000',
                'step': '0.01',
                'placeholder': 'Enter verified market value'
            }),
        }
        labels = {
            'agent_verified_value': 'Verified Market Value (KES)',
        }
    
    def clean_agent_verified_value(self):
        value = self.cleaned_data.get('agent_verified_value')
        if value < 1000:
            raise forms.ValidationError('Verified value must be at least KES 1,000')
        return value


class CustomUserCreationForm(UserCreationForm):
    # Define role choices without admin option for security
    ROLE_CHOICES = [
        ('borrower', 'Borrower'),
        ('lender', 'Lender'),
        ('agent', 'Station Agent'),
    ]
    
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=ROLE_CHOICES, required=True)
    phone_number = forms.CharField(max_length=15, help_text="M-Pesa phone number (e.g., 254712345678)")
    national_id = forms.CharField(max_length=20, help_text="National ID number")
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2', 'role', 'phone_number', 'national_id')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes for styling
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # Add placeholder text
        self.fields['username'].widget.attrs['placeholder'] = 'Enter username'
        self.fields['email'].widget.attrs['placeholder'] = 'Enter email address'
        self.fields['phone_number'].widget.attrs['placeholder'] = '254712345678'
        self.fields['national_id'].widget.attrs['placeholder'] = 'Enter National ID'
        
    def clean_email(self):
        """Custom validation for email"""
        email = self.cleaned_data.get('email')
        
        # Security: Prevent registration with admin email
        if email == 'sammyseth260@gmail.com':
            raise forms.ValidationError('This email is reserved for system administration.')
        
        return email
    
    def clean_national_id(self):
        """Custom validation for national ID"""
        from .services import supabase_service
        
        national_id = self.cleaned_data.get('national_id')
        
        # Check if national ID already exists in Supabase
        existing_user = supabase_service.get_user_by_national_id(national_id)
        if existing_user:
            raise forms.ValidationError('This National ID is already registered.')
        
        return national_id
    
    def clean_role(self):
        """Custom validation for role"""
        role = self.cleaned_data.get('role')
        
        # Security: Prevent admin role selection
        if role == 'admin':
            raise forms.ValidationError('Admin role cannot be selected during registration.')
        
        return role


class CollateralForm(forms.ModelForm):
    class Meta:
        model = Collateral
        fields = ['item_type', 'brand_model', 'market_value']
        widgets = {
            'item_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Smartphone, Laptop, Jewelry'
            }),
            'brand_model': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., iPhone 14 Pro, MacBook Air M2'
            }),
            'market_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter market value in KES',
                'step': '0.01',
                'min': '1000'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['market_value'].help_text = "Current market value of the item in KES"


class LoanApplicationForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ['principal_amount', 'duration_months']
        widgets = {
            'principal_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter loan amount in KES',
                'step': '0.01',
                'min': '500'
            }),
            'duration_months': forms.Select(
                choices=[(i, f'{i} months') for i in range(1, 13)],
                attrs={'class': 'form-control'}
            ),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['principal_amount'].help_text = "Amount you want to borrow (subject to collateral limits)"
        self.fields['duration_months'].help_text = "Loan repayment period"


class InvestmentForm(forms.ModelForm):
    class Meta:
        model = Investment
        fields = ['amount_invested']
        widgets = {
            'amount_invested': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter investment amount',
                'step': '0.01',
                'min': '100'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['amount_invested'].help_text = "Minimum investment: KES 100"