#!/usr/bin/env python3
"""
Test script to verify KYC persistence in Supabase
This script tests that KYC verification status is properly stored and retrieved from Supabase
"""

import os
import sys
import django
from datetime import datetime, timezone
import uuid

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'secure_lend.settings')
django.setup()

from core.supabase_client import supabase
from core.services import supabase_service

def test_kyc_persistence():
    """Test KYC persistence in Supabase"""
    print("🧪 Testing KYC Persistence in Supabase...")
    
    # Test user data
    test_username = "test_kyc_user"
    test_email = "test@example.com"
    
    try:
        # 1. Create test user in Supabase
        print(f"1. Creating test user: {test_username}")
        user_data = supabase_service.create_user(
            username=test_username,
            email=test_email,
            password="test123",
            role="borrower",
            phone_number="1234567890",
            national_id="12345678",
            first_name="Test",
            last_name="User"
        )
        
        if user_data and isinstance(user_data, list) and len(user_data) > 0:
            user = user_data[0]
            user_id = user['id']
            print(f"✅ User created with ID: {user_id}")
        else:
            print("❌ Failed to create user")
            return False
        
        # 2. Create KYC record
        print("2. Creating KYC record...")
        kyc_data = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'full_name': 'Test User',
            'id_number': '12345678',
            'date_of_birth': '1990-01-01',
            'status': 'pending',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        create_result = supabase.table('kyc_verifications').insert(kyc_data).execute()
        if create_result.data:
            kyc_id = create_result.data[0]['id']
            print(f"✅ KYC record created with ID: {kyc_id}")
        else:
            print("❌ Failed to create KYC record")
            return False
        
        # 3. Update KYC to verified
        print("3. Updating KYC status to verified...")
        update_result = supabase.table('kyc_verifications').update({
            'status': 'verified',
            'verified_at': datetime.now(timezone.utc).isoformat(),
            'verification_score': 95,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }).eq('id', kyc_id).execute()
        
        if update_result.data:
            print("✅ KYC status updated to verified")
        else:
            print("❌ Failed to update KYC status")
            return False
        
        # 4. Retrieve KYC record to verify persistence
        print("4. Retrieving KYC record to verify persistence...")
        retrieve_result = supabase.table('kyc_verifications').select('*').eq('user_id', user_id).execute()
        
        if retrieve_result.data:
            kyc_record = retrieve_result.data[0]
            status = kyc_record.get('status')
            verified_at = kyc_record.get('verified_at')
            score = kyc_record.get('verification_score')
            
            print(f"✅ KYC record retrieved successfully:")
            print(f"   Status: {status}")
            print(f"   Verified at: {verified_at}")
            print(f"   Score: {score}")
            
            if status == 'verified':
                print("✅ KYC persistence test PASSED!")
                success = True
            else:
                print(f"❌ KYC persistence test FAILED - expected 'verified', got '{status}'")
                success = False
        else:
            print("❌ Failed to retrieve KYC record")
            success = False
        
        # 5. Cleanup - delete test records
        print("5. Cleaning up test records...")
        try:
            supabase.table('kyc_verifications').delete().eq('user_id', user_id).execute()
            supabase.table('users').delete().eq('id', user_id).execute()
            print("✅ Test records cleaned up")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {str(e)}")
        
        return success
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        return False

def test_kyc_retrieval():
    """Test KYC retrieval for existing users"""
    print("\n🔍 Testing KYC Retrieval for Existing Users...")
    
    try:
        # Get all users
        all_users = supabase_service.get_all_users()
        if not all_users:
            print("ℹ️ No users found in Supabase")
            return True
        
        print(f"Found {len(all_users)} users in Supabase")
        
        # Check KYC records for each user
        verified_count = 0
        pending_count = 0
        no_kyc_count = 0
        
        for user in all_users[:5]:  # Check first 5 users
            username = user.get('username', 'Unknown')
            user_id = user.get('id')
            
            if not user_id:
                continue
            
            # Get KYC record
            kyc_result = supabase.table('kyc_verifications').select('*').eq('user_id', user_id).execute()
            
            if kyc_result.data:
                kyc_record = kyc_result.data[0]
                status = kyc_record.get('status', 'unknown')
                print(f"  {username}: KYC status = {status}")
                
                if status == 'verified':
                    verified_count += 1
                elif status == 'pending':
                    pending_count += 1
            else:
                print(f"  {username}: No KYC record")
                no_kyc_count += 1
        
        print(f"\n📊 KYC Status Summary:")
        print(f"   Verified: {verified_count}")
        print(f"   Pending: {pending_count}")
        print(f"   No KYC: {no_kyc_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ KYC retrieval test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting KYC Persistence Tests...\n")
    
    # Test 1: KYC Persistence
    test1_passed = test_kyc_persistence()
    
    # Test 2: KYC Retrieval
    test2_passed = test_kyc_retrieval()
    
    print(f"\n📋 Test Results:")
    print(f"   KYC Persistence: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"   KYC Retrieval: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All KYC persistence tests PASSED!")
        sys.exit(0)
    else:
        print("\n💥 Some KYC persistence tests FAILED!")
        sys.exit(1)