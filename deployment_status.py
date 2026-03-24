#!/usr/bin/env python3
"""
Quick deployment status check
"""

import requests
import time

def check_deployment_status():
    """Check if the deployment is working"""
    url = "https://securendkee.onrender.com"
    
    print("🔍 Checking deployment status...")
    print(f"Testing URL: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ Deployment is live!")
            print(f"Content length: {len(response.text)} characters")
            
            # Check if it's the actual Django app or an error page
            if "P2P Secure-Lend" in response.text:
                print("✅ Django app is running correctly!")
            elif "This page isn't working" in response.text:
                print("❌ Getting browser error page - deployment might be failing")
            else:
                print("⚠️ Getting unexpected content")
                print("First 200 characters:")
                print(response.text[:200])
        else:
            print(f"❌ Deployment issue - Status: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out - deployment might be starting up")
    except requests.exceptions.ConnectionError:
        print("🔌 Connection error - deployment might be down")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_deployment_status()