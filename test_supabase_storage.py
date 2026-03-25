#!/usr/bin/env python
"""
Test script to verify Supabase Storage is working for PDF contracts
Run with: python test_supabase_storage.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'secure_lend.settings')
django.setup()

from core.supabase_client import supabase
from io import BytesIO

def test_supabase_storage():
    """Test Supabase Storage for contract PDFs"""
    print("🔍 Testing Supabase Storage for PDF Contracts...")
    print("=" * 50)
    
    try:
        # Test 1: Check if we can connect to Supabase
        print("1️⃣ Testing Supabase connection...")
        try:
            # Try to list buckets
            buckets = supabase.storage.list_buckets()
            print(f"   ✅ Connected to Supabase Storage - {len(buckets)} buckets found")
            
            # Check if contracts bucket exists
            contracts_bucket_exists = any(bucket.name == 'contracts' for bucket in buckets)
            if contracts_bucket_exists:
                print("   ✅ 'contracts' bucket exists")
            else:
                print("   ❌ 'contracts' bucket NOT found")
                print("   💡 Create 'contracts' bucket in Supabase Dashboard > Storage")
                
        except Exception as e:
            print(f"   ❌ Supabase connection error: {str(e)}")
            return
        
        # Test 2: Try to upload a test file
        print("\n2️⃣ Testing file upload...")
        try:
            test_content = b"Test PDF content for Supabase Storage"
            test_filename = "test_contract.pdf"
            
            upload_result = supabase.storage.from_('contracts').upload(
                test_filename,
                test_content,
                file_options={'content-type': 'application/pdf'}
            )
            
            if upload_result:
                print(f"   ✅ Test file uploaded successfully")
                
                # Test 3: Get public URL
                print("\n3️⃣ Testing public URL generation...")
                try:
                    public_url = supabase.storage.from_('contracts').get_public_url(test_filename)
                    print(f"   ✅ Public URL generated: {public_url}")
                    
                    # Test 4: Clean up test file
                    print("\n4️⃣ Cleaning up test file...")
                    try:
                        supabase.storage.from_('contracts').remove([test_filename])
                        print("   ✅ Test file removed successfully")
                    except Exception as cleanup_error:
                        print(f"   ⚠️ Cleanup warning: {str(cleanup_error)}")
                    
                except Exception as url_error:
                    print(f"   ❌ Public URL error: {str(url_error)}")
                    
            else:
                print(f"   ❌ Test file upload failed")
                
        except Exception as upload_error:
            print(f"   ❌ Upload error: {str(upload_error)}")
            if "bucket" in str(upload_error).lower():
                print("   💡 Make sure 'contracts' bucket exists in Supabase Storage")
            if "policy" in str(upload_error).lower():
                print("   💡 Check RLS policies on 'contracts' bucket")
        
        # Test 5: Check existing contracts
        print("\n5️⃣ Checking existing contracts...")
        try:
            files = supabase.storage.from_('contracts').list()
            if files:
                print(f"   📄 Found {len(files)} existing files in contracts bucket")
                for file in files[:3]:  # Show first 3
                    print(f"      - {file['name']} ({file.get('metadata', {}).get('size', 'unknown')} bytes)")
            else:
                print("   📭 No files found in contracts bucket")
        except Exception as list_error:
            print(f"   ❌ Error listing files: {str(list_error)}")
        
        print("\n" + "=" * 50)
        print("📋 RECOMMENDATIONS:")
        
        if not contracts_bucket_exists:
            print("🔧 Create 'contracts' bucket:")
            print("   1. Go to Supabase Dashboard > Storage")
            print("   2. Click 'New bucket'")
            print("   3. Name: 'contracts'")
            print("   4. Set to Public bucket")
            print("   5. Save")
        
        print("\n🔧 Ensure bucket policies:")
        print("   1. Go to Supabase Dashboard > Storage > contracts bucket")
        print("   2. Click 'Policies' tab")
        print("   3. Add policy: 'Allow public read access'")
        print("   4. Add policy: 'Allow authenticated uploads'")
        
        print("\n✅ If all tests pass, PDF contract generation should work!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")

if __name__ == "__main__":
    test_supabase_storage()