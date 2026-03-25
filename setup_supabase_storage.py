#!/usr/bin/env python
"""
Setup Supabase Storage for PDF contracts
Run with: python setup_supabase_storage.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'secure_lend.settings')
django.setup()

from core.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

def setup_supabase_storage():
    """Setup Supabase Storage for contract PDFs"""
    print("🚀 Setting up Supabase Storage for PDF Contracts...")
    print("=" * 60)
    
    try:
        # Step 1: Check connection
        print("1️⃣ Testing Supabase connection...")
        try:
            buckets = supabase.storage.list_buckets()
            print(f"   ✅ Connected - found {len(buckets)} buckets")
        except Exception as e:
            print(f"   ❌ Connection failed: {str(e)}")
            return
        
        # Step 2: Check if contracts bucket exists
        print("\n2️⃣ Checking for 'contracts' bucket...")
        contracts_bucket = None
        for bucket in buckets:
            if bucket.name == 'contracts':
                contracts_bucket = bucket
                break
        
        if contracts_bucket:
            print("   ✅ 'contracts' bucket exists")
            print(f"   📊 Bucket ID: {contracts_bucket.id}")
            print(f"   🔒 Public: {contracts_bucket.public}")
        else:
            print("   ❌ 'contracts' bucket NOT found")
            print("\n🔧 MANUAL SETUP REQUIRED:")
            print("   1. Go to Supabase Dashboard > Storage")
            print("   2. Click 'New bucket'")
            print("   3. Name: 'contracts'")
            print("   4. Check 'Public bucket'")
            print("   5. Click 'Save'")
            return
        
        # Step 3: Test upload
        print("\n3️⃣ Testing file upload...")
        test_content = b"Test PDF content for contract system"
        test_filename = f"test_upload_{int(os.urandom(4).hex(), 16)}.pdf"
        
        try:
            upload_result = supabase.storage.from_('contracts').upload(
                test_filename,
                test_content,
                file_options={'content-type': 'application/pdf'}
            )
            
            if upload_result:
                print("   ✅ Upload successful")
                
                # Step 4: Test public URL
                print("\n4️⃣ Testing public URL generation...")
                try:
                    public_url = supabase.storage.from_('contracts').get_public_url(test_filename)
                    print(f"   ✅ Public URL: {public_url}")
                    
                    # Verify URL format
                    if 'supabase' in public_url and 'contracts' in public_url:
                        print("   ✅ URL format is correct")
                    else:
                        print(f"   ⚠️ Unexpected URL format: {public_url}")
                    
                except Exception as url_error:
                    print(f"   ❌ Public URL error: {str(url_error)}")
                
                # Step 5: Cleanup
                print("\n5️⃣ Cleaning up test file...")
                try:
                    supabase.storage.from_('contracts').remove([test_filename])
                    print("   ✅ Test file removed")
                except Exception as cleanup_error:
                    print(f"   ⚠️ Cleanup warning: {str(cleanup_error)}")
                
            else:
                print("   ❌ Upload failed")
                
        except Exception as upload_error:
            print(f"   ❌ Upload error: {str(upload_error)}")
            
            if "bucket" in str(upload_error).lower():
                print("   💡 Bucket may not exist or be accessible")
            if "policy" in str(upload_error).lower() or "rls" in str(upload_error).lower():
                print("   💡 RLS policy issue - check bucket permissions")
                print("\n🔧 POLICY SETUP:")
                print("   1. Go to Supabase Dashboard > Storage > contracts")
                print("   2. Click 'Policies' tab")
                print("   3. Add policy for INSERT: 'Allow authenticated users to upload'")
                print("   4. Add policy for SELECT: 'Allow public read access'")
        
        # Step 6: Check existing files
        print("\n6️⃣ Checking existing contract files...")
        try:
            files = supabase.storage.from_('contracts').list()
            if files:
                print(f"   📄 Found {len(files)} existing files")
                contract_files = [f for f in files if f['name'].startswith('loan_contract_')]
                print(f"   📋 Contract files: {len(contract_files)}")
                
                if contract_files:
                    print("   📁 Recent contracts:")
                    for file in contract_files[-3:]:  # Show last 3
                        size_kb = file.get('metadata', {}).get('size', 0) / 1024 if file.get('metadata', {}).get('size') else 0
                        print(f"      - {file['name']} ({size_kb:.1f} KB)")
            else:
                print("   📭 No files found")
        except Exception as list_error:
            print(f"   ❌ Error listing files: {str(list_error)}")
        
        print(f"\n" + "="*60)
        print("✅ SUPABASE STORAGE SETUP COMPLETE!")
        print("\n📋 NEXT STEPS:")
        print("1. Run: python fix_contract_urls.py")
        print("2. Run: python manage.py generate_missing_contracts --force")
        print("3. Test contract downloads in the app")
        
    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")
        logger.error(f"Supabase Storage setup failed: {str(e)}")

if __name__ == "__main__":
    setup_supabase_storage()