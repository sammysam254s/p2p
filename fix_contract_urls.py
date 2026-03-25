#!/usr/bin/env python
"""
Fix contract URLs to use Supabase Storage instead of Django media
Run with: python fix_contract_urls.py
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

def fix_contract_urls():
    """Fix contract URLs to use proper Supabase Storage URLs"""
    print("🔧 Fixing Contract URLs to use Supabase Storage...")
    print("=" * 60)
    
    try:
        # Get all contracts from database
        contracts_result = supabase.table('loan_contracts').select('*').execute()
        
        if not contracts_result.data:
            print("📭 No contracts found in database")
            return
        
        print(f"📋 Found {len(contracts_result.data)} contracts to check")
        
        fixed_count = 0
        error_count = 0
        
        for contract in contracts_result.data:
            contract_id = contract['id']
            current_url = contract['pdf_url']
            
            print(f"\n🔍 Checking contract {contract_id[:8]}...")
            print(f"   Current URL: {current_url}")
            
            # Check if URL is a Django media URL
            if '/media/contracts/' in current_url:
                print("   ❌ Found Django media URL - needs fixing")
                
                # Extract filename from URL
                filename = current_url.split('/media/contracts/')[-1]
                print(f"   📁 Extracted filename: {filename}")
                
                try:
                    # Generate proper Supabase Storage URL
                    proper_url = supabase.storage.from_('contracts').get_public_url(filename)
                    print(f"   🔗 New Supabase URL: {proper_url}")
                    
                    # Update contract in database
                    update_result = supabase.table('loan_contracts').update({
                        'pdf_url': proper_url
                    }).eq('id', contract_id).execute()
                    
                    if update_result.data:
                        print("   ✅ Contract URL updated successfully")
                        fixed_count += 1
                    else:
                        print("   ❌ Failed to update contract URL")
                        error_count += 1
                        
                except Exception as e:
                    print(f"   ❌ Error fixing URL: {str(e)}")
                    error_count += 1
                    
            elif 'supabase' in current_url.lower():
                print("   ✅ Already using Supabase URL - no fix needed")
            else:
                print(f"   ⚠️ Unknown URL format: {current_url}")
        
        # Summary
        print(f"\n" + "="*60)
        print("📊 FIX SUMMARY:")
        print(f"✅ Fixed: {fixed_count} contracts")
        print(f"❌ Errors: {error_count} contracts")
        print(f"📋 Total checked: {len(contracts_result.data)} contracts")
        
        if fixed_count > 0:
            print(f"\n🎉 Successfully fixed {fixed_count} contract URLs!")
            print("📱 Contract downloads should now work properly.")
        
        if error_count > 0:
            print(f"\n⚠️ {error_count} contracts had errors. Check logs for details.")
            
        # Test one URL
        if contracts_result.data:
            test_contract = contracts_result.data[0]
            test_url = test_contract['pdf_url']
            print(f"\n🧪 Test URL: {test_url}")
            print("   Try accessing this URL in your browser to verify it works")
            
    except Exception as e:
        print(f"❌ Script failed: {str(e)}")
        logger.error(f"Fix contract URLs failed: {str(e)}")

if __name__ == "__main__":
    fix_contract_urls()