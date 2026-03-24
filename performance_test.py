#!/usr/bin/env python3
"""
Performance test script to verify loading speed optimizations
"""

import time
import requests
from urllib.parse import urljoin

def test_page_load_speed(base_url, pages):
    """Test loading speed of various pages"""
    print("🚀 Testing page load speeds...\n")
    
    results = {}
    
    for page_name, path in pages.items():
        url = urljoin(base_url, path)
        
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            end_time = time.time()
            
            load_time = end_time - start_time
            results[page_name] = {
                'load_time': load_time,
                'status_code': response.status_code,
                'success': response.status_code == 200
            }
            
            status = "✅" if load_time < 1.0 else "⚠️" if load_time < 2.0 else "❌"
            print(f"{status} {page_name}: {load_time:.2f}s (Status: {response.status_code})")
            
        except requests.exceptions.RequestException as e:
            results[page_name] = {
                'load_time': None,
                'status_code': None,
                'success': False,
                'error': str(e)
            }
            print(f"❌ {page_name}: Failed - {str(e)}")
    
    return results

def analyze_results(results):
    """Analyze performance test results"""
    print("\n📊 Performance Analysis:")
    print("=" * 50)
    
    successful_tests = [r for r in results.values() if r['success']]
    
    if not successful_tests:
        print("❌ No successful page loads detected!")
        return
    
    load_times = [r['load_time'] for r in successful_tests]
    avg_load_time = sum(load_times) / len(load_times)
    max_load_time = max(load_times)
    min_load_time = min(load_times)
    
    print(f"Average load time: {avg_load_time:.2f}s")
    print(f"Fastest load time: {min_load_time:.2f}s")
    print(f"Slowest load time: {max_load_time:.2f}s")
    
    fast_pages = len([t for t in load_times if t < 1.0])
    medium_pages = len([t for t in load_times if 1.0 <= t < 2.0])
    slow_pages = len([t for t in load_times if t >= 2.0])
    
    print(f"\n🎯 Performance Goals:")
    print(f"✅ Sub-1-second loads: {fast_pages}/{len(load_times)} pages")
    print(f"⚠️  1-2 second loads: {medium_pages}/{len(load_times)} pages")
    print(f"❌ 2+ second loads: {slow_pages}/{len(load_times)} pages")
    
    if avg_load_time < 1.0:
        print("\n🎉 EXCELLENT! Average load time under 1 second!")
    elif avg_load_time < 2.0:
        print("\n👍 GOOD! Average load time under 2 seconds!")
    else:
        print("\n⚠️  NEEDS IMPROVEMENT! Average load time over 2 seconds!")

def main():
    print("🔥 P2P Secure-Lend Performance Test")
    print("=" * 40)
    
    # Test pages (update URL when deployed)
    base_url = input("Enter the base URL (e.g., https://yourapp.onrender.com): ").strip()
    if not base_url:
        base_url = "http://localhost:8000"  # Default for local testing
    
    # Pages to test
    pages = {
        "Home Page": "/",
        "Login Page": "/login/",
        "Register Page": "/register/",
        # Add more pages after authentication is set up
    }
    
    print(f"Testing against: {base_url}")
    print(f"Target: All pages should load in under 1 second\n")
    
    # Run tests
    results = test_page_load_speed(base_url, pages)
    
    # Analyze results
    analyze_results(results)
    
    print("\n💡 Optimization Tips:")
    print("- Caching is enabled for database queries")
    print("- CSS/JS loads asynchronously")
    print("- Django ORM used for local queries")
    print("- Supabase calls are cached")
    print("- Session data is cached")

if __name__ == "__main__":
    main()