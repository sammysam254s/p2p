#!/usr/bin/env python
"""
Test script for Simple KYC Verification Service
Tests the lightweight KYC verification without external dependencies
"""

import os
import sys
import django
from datetime import date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'secure_lend.settings')
django.setup()

from core.simple_kyc_service import simple_kyc_service
from core.models import CustomUser, KYCVerification
from django.core.files.uploadedfile import SimpleUploadedFile


def test_simple_kyc():
    """Test the simple KYC verification service"""
    print("🧪 Testing Simple KYC Verification Service")
    print("=" * 50)
    
    # Test 1: Text validation
    print("\n1️⃣ Testing text validation...")
    
    # Create a mock KYC object
    class MockKYC:
        def __init__(self):
            self.full_name = "John Doe Smith"
            self.id_number = "12345678"
            self.date_of_birth = date(1990, 5, 15)
            self.id_front_image = None
            self.id_back_image = None
            self.selfie_image = None
            self.user = type('User', (), {'username': 'testuser'})()
    
    mock_kyc = MockKYC()
    
    # Test text verification
    text_result = simple_kyc_service._verify_text_information(
        mock_kyc.full_name,
        mock_kyc.id_number,
        mock_kyc.date_of_birth
    )
    
    print(f"   Name valid: {text_result['name_valid']} (Score: {text_result['name_score']:.1f}%)")
    print(f"   ID valid: {text_result['id_valid']} (Score: {text_result['id_score']:.1f}%)")
    print(f"   DOB valid: {text_result['dob_valid']} (Score: {text_result['dob_score']:.1f}%)")
    print(f"   Overall text score: {text_result['text_score']:.1f}%")
    
    # Test 2: Invalid data
    print("\n2️⃣ Testing invalid data...")
    
    mock_kyc_invalid = MockKYC()
    mock_kyc_invalid.full_name = "X"  # Too short
    mock_kyc_invalid.id_number = "123"  # Too short
    mock_kyc_invalid.date_of_birth = date(2010, 1, 1)  # Too young
    
    text_result_invalid = simple_kyc_service._verify_text_information(
        mock_kyc_invalid.full_name,
        mock_kyc_invalid.id_number,
        mock_kyc_invalid.date_of_birth
    )
    
    print(f"   Name valid: {text_result_invalid['name_valid']} (Score: {text_result_invalid['name_score']:.1f}%)")
    print(f"   ID valid: {text_result_invalid['id_valid']} (Score: {text_result_invalid['id_score']:.1f}%)")
    print(f"   DOB valid: {text_result_invalid['dob_valid']} (Score: {text_result_invalid['dob_score']:.1f}%)")
    print(f"   Overall text score: {text_result_invalid['text_score']:.1f}%")
    
    # Test 3: Full verification
    print("\n3️⃣ Testing full verification...")
    
    # Create mock image files
    class MockImageField:
        def __init__(self, name, size=50000):
            self.name = name
            self.path = f"/tmp/{name}"
            self.size = size
            # Create a mock file
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, 'wb') as f:
                # Write JPEG header
                f.write(b'\xff\xd8\xff\xe0')
                # Write some dummy data
                f.write(b'0' * (size - 4))
    
    mock_kyc.id_front_image = MockImageField("id_front.jpg")
    mock_kyc.id_back_image = MockImageField("id_back.jpg")
    mock_kyc.selfie_image = MockImageField("selfie.jpg")
    
    # Run full verification
    result = simple_kyc_service.verify_kyc_submission(mock_kyc)
    
    print(f"   Overall score: {result['overall_score']:.1f}%")
    print(f"   Verification passed: {result['passed']}")
    print(f"   Message: {result['message']}")
    
    if result['recommendations']:
        print("   Recommendations:")
        for rec in result['recommendations']:
            print(f"     • {rec}")
    
    # Test 4: Status messages
    print("\n4️⃣ Testing status messages...")
    
    class MockKYCStatus:
        def __init__(self, status):
            self.status = status
    
    statuses = ['pending', 'under_review', 'verified', 'rejected']
    for status in statuses:
        mock_status = MockKYCStatus(status)
        message = simple_kyc_service.get_verification_status_message(mock_status)
        print(f"   {status}: {message}")
    
    # Cleanup
    print("\n🧹 Cleaning up test files...")
    try:
        os.remove("/tmp/id_front.jpg")
        os.remove("/tmp/id_back.jpg")
        os.remove("/tmp/selfie.jpg")
    except:
        pass
    
    print("\n✅ Simple KYC Service Test Completed!")
    print("=" * 50)
    
    return result['passed']


if __name__ == "__main__":
    try:
        success = test_simple_kyc()
        if success:
            print("\n🎉 All tests passed! Simple KYC service is working correctly.")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed. Please check the implementation.")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {str(e)}")
        sys.exit(1)