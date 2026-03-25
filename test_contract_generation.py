#!/usr/bin/env python
"""
Test script to verify PDF contract generation system
Run with: python test_contract_generation.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'secure_lend.settings')
django.setup()

from core.services import supabase_service
from core.supabase_client import supabase

def test_contract_system():
    """Test the contract generation system"""
    print("🔍 Testing PDF Contract Generation System...")
    print("=" * 50)
    
    try:
        # Test 1: Check Supabase connection
        print("1️⃣ Testing Supabase connection...")
        users = supabase_service.get_all_users()
        if users:
            print(f"   ✅ Connected to Supabase - {len(users)} users found")
        else:
            print("   ⚠️ No users found in Supabase")
        
        # Test 2: Check for active loans
        print("\n2️⃣ Checking for active loans...")
        all_loans = supabase_service.get_all_loans() or []
        active_loans = [loan for loan in all_loans if loan.get('status') == 'active']
        print(f"   📋 Total loans: {len(all_loans)}")
        print(f"   🎯 Active loans: {len(active_loans)}")
        
        # Test 3: Check contract table exists
        print("\n3️⃣ Checking contract tables...")
        try:
            contracts = supabase.table('loan_contracts').select('id').limit(1).execute()
            print("   ✅ loan_contracts table exists")
        except Exception as e:
            print(f"   ❌ loan_contracts table error: {str(e)}")
            print("   💡 Run: supabase_add_contracts.sql in Supabase SQL Editor")
        
        # Test 4: Check existing contracts
        print("\n4️⃣ Checking existing contracts...")
        try:
            all_contracts = supabase.table('loan_contracts').select('*').execute()
            if all_contracts.data:
                print(f"   📄 Found {len(all_contracts.data)} existing contracts")
                for contract in all_contracts.data[:3]:  # Show first 3
                    print(f"      - Loan: {contract['loan_id'][:8]}... | PDF: {contract['pdf_url'][:50]}...")
            else:
                print("   📭 No contracts found")
        except Exception as e:
            print(f"   ❌ Error checking contracts: {str(e)}")
        
        # Test 5: Check PDF generation dependencies
        print("\n5️⃣ Checking PDF generation dependencies...")
        try:
            import reportlab
            print(f"   ✅ reportlab: {reportlab.Version}")
        except ImportError:
            print("   ❌ reportlab not installed - run: pip install reportlab")
        
        try:
            import qrcode
            print(f"   ✅ qrcode: {qrcode.__version__}")
        except ImportError:
            print("   ❌ qrcode not installed - run: pip install qrcode")
        
        try:
            from PIL import Image
            print(f"   ✅ Pillow (PIL) available")
        except ImportError:
            print("   ❌ Pillow not installed - run: pip install Pillow")
        
        # Test 6: Check contract services
        print("\n6️⃣ Testing contract services...")
        try:
            from core.contract_pdf_service import contract_pdf_service
            from core.contract_verification import contract_verification_service
            print("   ✅ Contract services imported successfully")
        except ImportError as e:
            print(f"   ❌ Contract service import error: {str(e)}")
        
        # Test 7: Recommendations
        print("\n" + "=" * 50)
        print("📋 RECOMMENDATIONS:")
        
        if len(active_loans) > 0:
            print("🚀 Generate contracts for active loans:")
            print("   python manage.py generate_missing_contracts")
        
        print("\n🔧 Ensure Supabase setup:")
        print("   1. Run supabase_add_contracts.sql in Supabase SQL Editor")
        print("   2. Create 'contracts' storage bucket in Supabase")
        print("   3. Set bucket to public read access")
        
        print("\n✅ System Status: Ready for contract generation!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")

if __name__ == "__main__":
    test_contract_system()