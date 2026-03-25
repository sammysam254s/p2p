#!/usr/bin/env python3
"""Simple Supabase test"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'secure_lend.settings')
django.setup()

from core.supabase_client import supabase

def test_tables():
    """Test Supabase tables"""
    tables = ['users', 'collateral', 'loans', 'investments', 'kyc_verifications']
    
    for table in tables:
        try:
            result = supabase.table(table).select('*').execute()
            count = len(result.data) if result.data else 0
            print(f"✅ {table}: {count} records")
        except Exception as e:
            print(f"❌ {table}: Error - {str(e)}")

if __name__ == "__main__":
    print("🧪 Testing Supabase Tables...")
    test_tables()