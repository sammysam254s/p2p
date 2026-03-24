from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.services import supabase_service
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Verify system functionality and data integrity'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-admin',
            action='store_true',
            help='Check admin user configuration',
        )
        parser.add_argument(
            '--check-supabase',
            action='store_true',
            help='Check Supabase connectivity and data',
        )
        parser.add_argument(
            '--check-all',
            action='store_true',
            help='Run all verification checks',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 System Verification Started'))
        
        if options['check_all'] or options['check_admin']:
            self.check_admin_user()
        
        if options['check_all'] or options['check_supabase']:
            self.check_supabase_connectivity()
            self.check_supabase_data()
        
        if options['check_all']:
            self.check_url_patterns()
            self.check_templates()
        
        self.stdout.write(self.style.SUCCESS('✅ System Verification Complete'))

    def check_admin_user(self):
        """Check admin user configuration"""
        self.stdout.write('\n📋 Checking Admin User Configuration...')
        
        try:
            User = get_user_model()
            admin_email = 'sammyseth260@gmail.com'
            
            # Check Django admin user
            try:
                django_admin = User.objects.get(email=admin_email)
                self.stdout.write(f'✅ Django admin user exists: {django_admin.username}')
                self.stdout.write(f'   - Role: {django_admin.role}')
                self.stdout.write(f'   - Is Staff: {django_admin.is_staff}')
                self.stdout.write(f'   - Is Superuser: {django_admin.is_superuser}')
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING('⚠️  Django admin user not found'))
            
            # Check Supabase admin user
            supabase_admin = supabase_service.get_user_by_email(admin_email)
            if supabase_admin:
                self.stdout.write(f'✅ Supabase admin user exists: {supabase_admin["username"]}')
                self.stdout.write(f'   - Role: {supabase_admin["role"]}')
                self.stdout.write(f'   - Is Staff: {supabase_admin.get("is_staff", False)}')
            else:
                self.stdout.write(self.style.WARNING('⚠️  Supabase admin user not found'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error checking admin user: {str(e)}'))

    def check_supabase_connectivity(self):
        """Check Supabase connectivity"""
        self.stdout.write('\n🔗 Checking Supabase Connectivity...')
        
        try:
            # Test basic connectivity
            users = supabase_service.get_all_users()
            if users is not None:
                self.stdout.write(f'✅ Supabase connection successful')
                self.stdout.write(f'   - Total users in database: {len(users)}')
            else:
                self.stdout.write(self.style.ERROR('❌ Supabase connection failed'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Supabase connectivity error: {str(e)}'))

    def check_supabase_data(self):
        """Check Supabase data integrity"""
        self.stdout.write('\n📊 Checking Supabase Data Integrity...')
        
        try:
            # Check users
            users = supabase_service.get_all_users() or []
            borrowers = [u for u in users if u.get('role') == 'borrower']
            lenders = [u for u in users if u.get('role') == 'lender']
            agents = [u for u in users if u.get('role') == 'agent']
            admins = [u for u in users if u.get('role') == 'admin']
            
            self.stdout.write(f'👥 Users: {len(users)} total')
            self.stdout.write(f'   - Borrowers: {len(borrowers)}')
            self.stdout.write(f'   - Lenders: {len(lenders)}')
            self.stdout.write(f'   - Agents: {len(agents)}')
            self.stdout.write(f'   - Admins: {len(admins)}')
            
            # Check loans
            loans = supabase_service.get_all_loans() or []
            pending_loans = [l for l in loans if l.get('status') == 'pending_collateral']
            listed_loans = [l for l in loans if l.get('status') == 'listed']
            active_loans = [l for l in loans if l.get('status') == 'active']
            
            self.stdout.write(f'💰 Loans: {len(loans)} total')
            self.stdout.write(f'   - Pending: {len(pending_loans)}')
            self.stdout.write(f'   - Listed: {len(listed_loans)}')
            self.stdout.write(f'   - Active: {len(active_loans)}')
            
            # Check collateral
            collaterals = supabase_service.get_all_collaterals() or []
            pending_collaterals = supabase_service.get_pending_collaterals() or []
            
            self.stdout.write(f'🛡️  Collateral: {len(collaterals)} total')
            self.stdout.write(f'   - Pending verification: {len(pending_collaterals)}')
            self.stdout.write(f'   - Verified: {len(collaterals) - len(pending_collaterals)}')
            
            # Check investments
            investments = supabase_service.get_all_investments() or []
            total_invested = sum(float(i.get('amount_invested', 0)) for i in investments)
            
            self.stdout.write(f'📈 Investments: {len(investments)} total')
            self.stdout.write(f'   - Total amount: KES {total_invested:,.2f}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Data integrity check error: {str(e)}'))

    def check_url_patterns(self):
        """Check URL patterns"""
        self.stdout.write('\n🔗 Checking URL Patterns...')
        
        try:
            from django.urls import reverse
            
            # Test critical URLs
            critical_urls = [
                'home',
                'login',
                'logout',
                'register',
                'admin_dashboard',
                'borrower_dashboard',
                'marketplace',
                'agent_panel',
            ]
            
            for url_name in critical_urls:
                try:
                    url = reverse(url_name)
                    self.stdout.write(f'✅ {url_name}: {url}')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ {url_name}: {str(e)}'))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ URL pattern check error: {str(e)}'))

    def check_templates(self):
        """Check template files"""
        self.stdout.write('\n📄 Checking Template Files...')
        
        import os
        from django.conf import settings
        
        try:
            template_dirs = []
            for template_setting in settings.TEMPLATES:
                template_dirs.extend(template_setting.get('DIRS', []))
            
            critical_templates = [
                'base.html',
                'core/home.html',
                'core/admin_dashboard.html',
                'core/admin_payments_management.html',
                'core/admin_wallet_management.html',
                'registration/login.html',
                'registration/register.html',
            ]
            
            for template_dir in template_dirs:
                if os.path.exists(template_dir):
                    for template in critical_templates:
                        template_path = os.path.join(template_dir, template)
                        if os.path.exists(template_path):
                            self.stdout.write(f'✅ {template}')
                        else:
                            self.stdout.write(self.style.WARNING(f'⚠️  {template} not found'))
                            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Template check error: {str(e)}'))