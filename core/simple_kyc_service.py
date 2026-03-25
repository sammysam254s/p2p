import re
import os
import hashlib
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


class SimpleKYCVerificationService:
    """
    Simple KYC verification service without external dependencies
    
    This service performs basic verification using:
    - Text matching between provided information and user input
    - Basic image file validation (size, format)
    - Simple similarity checks
    
    No external AI/ML libraries required - works with standard Python only.
    """
    
    def __init__(self):
        self.min_name_length = 2
        self.min_id_length = 6
        self.min_image_size = 5000  # 5KB minimum
        self.max_image_size = 10 * 1024 * 1024  # 10MB maximum
        
    def verify_kyc_submission(self, kyc_verification):
        """Main verification method for KYC submission"""
        verification_result = {
            'overall_score': 0.0,
            'text_verification': {},
            'image_validation': {},
            'recommendations': [],
            'passed': False,
            'message': '',
            'details': ''
        }
        
        try:
            logger.info(f"Starting simple KYC verification for user: {kyc_verification.user.username}")
            
            # 1. Verify text information
            text_result = self._verify_text_information(
                kyc_verification.full_name,
                kyc_verification.id_number,
                kyc_verification.date_of_birth
            )
            verification_result['text_verification'] = text_result
            
            # 2. Validate uploaded images
            image_result = self._validate_images(
                kyc_verification.id_front_image,
                kyc_verification.id_back_image,
                kyc_verification.selfie_image
            )
            verification_result['image_validation'] = image_result
            
            # 3. Calculate overall score
            overall_score = self._calculate_simple_score(text_result, image_result)
            verification_result['overall_score'] = overall_score
            
            # 4. Generate recommendations
            recommendations = self._generate_simple_recommendations(text_result, image_result)
            verification_result['recommendations'] = recommendations
            
            # 5. Determine if verification passed
            passed = overall_score >= 80.0  # 80% threshold for simple verification
            verification_result['passed'] = passed
            
            if passed:
                verification_result['message'] = 'KYC verification completed successfully'
                verification_result['details'] = 'All required information provided and validated'
                logger.info(f"KYC approved for {kyc_verification.user.username} with score {overall_score:.1f}%")
            else:
                verification_result['message'] = 'KYC verification failed - please check your information'
                verification_result['details'] = 'Some required information is missing or invalid'
                logger.warning(f"KYC rejected for {kyc_verification.user.username} with score {overall_score:.1f}%")
            
        except Exception as e:
            logger.error(f"Simple KYC verification error: {str(e)}")
            verification_result['error'] = str(e)
            verification_result['message'] = 'Technical error during verification'
            verification_result['recommendations'].append("System error occurred. Please try again or contact support.")
        
        return verification_result
    
    def _verify_text_information(self, full_name, id_number, date_of_birth):
        """Verify the text information provided by user"""
        result = {
            'name_valid': False,
            'id_valid': False,
            'dob_valid': False,
            'name_score': 0.0,
            'id_score': 0.0,
            'dob_score': 0.0,
            'text_score': 0.0
        }
        
        try:
            # Validate full name
            if full_name and len(full_name.strip()) >= self.min_name_length:
                # Check if name contains only valid characters
                name_clean = re.sub(r'[^a-zA-Z\s\-\']', '', full_name.strip())
                if len(name_clean) >= self.min_name_length:
                    # Check if name has at least 2 words (first and last name)
                    name_words = [word for word in name_clean.split() if len(word) > 0]
                    if len(name_words) >= 2:
                        result['name_valid'] = True
                        result['name_score'] = 100.0
                        logger.info(f"Name validation passed: {len(name_words)} words found")
                    else:
                        result['name_score'] = 50.0  # Single name provided
                        logger.warning("Name validation: Only single name provided")
                else:
                    logger.warning("Name validation failed: Invalid characters")
            else:
                logger.warning("Name validation failed: Too short or empty")
            
            # Validate ID number
            if id_number and len(id_number.strip()) >= self.min_id_length:
                # Remove spaces and special characters
                id_clean = re.sub(r'[^a-zA-Z0-9]', '', id_number.strip())
                if len(id_clean) >= self.min_id_length:
                    # Check if ID contains numbers (most IDs have numbers)
                    if re.search(r'\d', id_clean):
                        result['id_valid'] = True
                        result['id_score'] = 100.0
                        logger.info(f"ID validation passed: {len(id_clean)} characters")
                    else:
                        result['id_score'] = 70.0  # ID without numbers (unusual but possible)
                        logger.warning("ID validation: No numbers found in ID")
                else:
                    logger.warning("ID validation failed: Too short after cleaning")
            else:
                logger.warning("ID validation failed: Too short or empty")
            
            # Validate date of birth
            if date_of_birth:
                try:
                    # Check if DOB is reasonable (between 18 and 100 years old)
                    today = date.today()
                    age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
                    
                    if 18 <= age <= 100:
                        result['dob_valid'] = True
                        result['dob_score'] = 100.0
                        logger.info(f"DOB validation passed: Age {age}")
                    else:
                        result['dob_score'] = 30.0  # Invalid age range
                        logger.warning(f"DOB validation failed: Age {age} out of range")
                except Exception as e:
                    logger.error(f"DOB validation error: {str(e)}")
                    result['dob_score'] = 0.0
            else:
                logger.warning("DOB validation failed: No date provided")
            
            # Calculate overall text score
            result['text_score'] = (result['name_score'] + result['id_score'] + result['dob_score']) / 3
            
        except Exception as e:
            logger.error(f"Text verification error: {str(e)}")
        
        return result
    
    def _validate_images(self, id_front, id_back, selfie):
        """Validate uploaded images without external libraries"""
        result = {
            'id_front_valid': False,
            'id_back_valid': False,
            'selfie_valid': False,
            'id_front_score': 0.0,
            'id_back_score': 0.0,
            'selfie_score': 0.0,
            'image_score': 0.0
        }
        
        try:
            # Validate ID front image
            if id_front:
                result['id_front_valid'], result['id_front_score'] = self._validate_single_image(id_front, "ID Front")
            
            # Validate ID back image
            if id_back:
                result['id_back_valid'], result['id_back_score'] = self._validate_single_image(id_back, "ID Back")
            
            # Validate selfie image
            if selfie:
                result['selfie_valid'], result['selfie_score'] = self._validate_single_image(selfie, "Selfie")
            
            # Calculate overall image score
            result['image_score'] = (result['id_front_score'] + result['id_back_score'] + result['selfie_score']) / 3
            
        except Exception as e:
            logger.error(f"Image validation error: {str(e)}")
        
        return result
    
    def _validate_single_image(self, image_field, image_type):
        """Validate a single image file"""
        try:
            if not image_field:
                logger.warning(f"{image_type} validation failed: No image provided")
                return False, 0.0
            
            # Check if file exists
            if not hasattr(image_field, 'path') or not os.path.exists(image_field.path):
                logger.warning(f"{image_type} validation failed: File does not exist")
                return False, 0.0
            
            # Check file size
            file_size = os.path.getsize(image_field.path)
            
            if file_size < self.min_image_size:
                logger.warning(f"{image_type} validation failed: File too small ({file_size} bytes)")
                return False, 20.0
            
            if file_size > self.max_image_size:
                logger.warning(f"{image_type} validation failed: File too large ({file_size} bytes)")
                return False, 30.0
            
            # Check file extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
            file_extension = os.path.splitext(image_field.name)[1].lower()
            
            if file_extension not in valid_extensions:
                logger.warning(f"{image_type} validation failed: Invalid extension {file_extension}")
                return False, 40.0
            
            # Basic file header check for common image formats
            try:
                with open(image_field.path, 'rb') as f:
                    header = f.read(10)
                    
                # Check for common image file signatures
                if (header.startswith(b'\xff\xd8\xff') or  # JPEG
                    header.startswith(b'\x89PNG\r\n\x1a\n') or  # PNG
                    header.startswith(b'BM') or  # BMP
                    header.startswith(b'GIF87a') or header.startswith(b'GIF89a')):  # GIF
                    
                    # Calculate score based on file size (larger files generally better quality)
                    if file_size >= 100000:  # 100KB+
                        score = 100.0
                    elif file_size >= 50000:   # 50KB+
                        score = 90.0
                    elif file_size >= 20000:   # 20KB+
                        score = 80.0
                    else:
                        score = 70.0
                    
                    logger.info(f"{image_type} validation passed: {file_size} bytes, score {score}")
                    return True, score
                else:
                    logger.warning(f"{image_type} validation failed: Invalid file header")
                    return False, 10.0
                    
            except Exception as e:
                logger.error(f"{image_type} header check error: {str(e)}")
                return False, 10.0
            
        except Exception as e:
            logger.error(f"{image_type} validation error: {str(e)}")
            return False, 0.0
    
    def _calculate_simple_score(self, text_result, image_result):
        """Calculate overall score using simple weighted average"""
        try:
            # Weight text verification more heavily (70%) than image validation (30%)
            text_weight = 0.7
            image_weight = 0.3
            
            text_score = text_result.get('text_score', 0.0)
            image_score = image_result.get('image_score', 0.0)
            
            overall_score = (text_score * text_weight) + (image_score * image_weight)
            
            # Bonus points if all required fields are valid
            if (text_result.get('name_valid', False) and 
                text_result.get('id_valid', False) and 
                text_result.get('dob_valid', False) and
                image_result.get('id_front_valid', False) and
                image_result.get('selfie_valid', False)):
                overall_score = min(overall_score + 10, 100)  # 10 point bonus, max 100
            
            return overall_score
            
        except Exception as e:
            logger.error(f"Score calculation error: {str(e)}")
            return 0.0
    
    def _generate_simple_recommendations(self, text_result, image_result):
        """Generate simple recommendations based on validation results"""
        recommendations = []
        
        try:
            # Text validation recommendations
            if not text_result.get('name_valid', False):
                if text_result.get('name_score', 0) == 0:
                    recommendations.append("❌ Full name is required. Please provide your complete name as it appears on your ID.")
                else:
                    recommendations.append("⚠️ Please provide both first and last name as they appear on your ID.")
            
            if not text_result.get('id_valid', False):
                recommendations.append("❌ Valid ID number is required. Please enter your complete ID number (minimum 6 characters).")
            
            if not text_result.get('dob_valid', False):
                recommendations.append("❌ Valid date of birth is required. You must be between 18 and 100 years old.")
            
            # Image validation recommendations
            if not image_result.get('id_front_valid', False):
                recommendations.append("❌ Valid ID front image is required. Please upload a clear photo of the front of your ID.")
            
            if not image_result.get('id_back_valid', False):
                recommendations.append("⚠️ ID back image recommended. Please upload a photo of the back of your ID if available.")
            
            if not image_result.get('selfie_valid', False):
                recommendations.append("❌ Valid selfie image is required. Please upload a clear photo of yourself.")
            
            # Quality recommendations
            if image_result.get('image_score', 0) < 70:
                recommendations.append("📸 Image quality could be improved. Use good lighting and ensure images are clear and readable.")
            
            # Success message
            if not recommendations:
                recommendations.append("✅ All verification requirements met! KYC approved.")
            
            # General tips
            if recommendations and len([r for r in recommendations if r.startswith("❌")]) > 0:
                recommendations.append("💡 Tip: Ensure all information matches exactly what appears on your official ID document.")
                recommendations.append("📱 Tip: Take photos in good lighting with a steady hand for best results.")
            
        except Exception as e:
            logger.error(f"Recommendations generation error: {str(e)}")
            recommendations.append("⚠️ Error generating recommendations. Please ensure all fields are completed.")
        
        return recommendations
    
    def get_verification_status_message(self, kyc_verification):
        """Get a simple status message for the KYC verification"""
        try:
            if not kyc_verification:
                return "KYC verification not started"
            
            status = kyc_verification.status
            
            if status == 'verified':
                return "✅ KYC Verified - You can now apply for loans"
            elif status == 'under_review':
                return "⏳ KYC Under Review - Processing your information"
            elif status == 'rejected':
                return "❌ KYC Rejected - Please review and resubmit"
            else:
                return "⚠️ KYC Pending - Please complete your verification"
                
        except Exception as e:
            logger.error(f"Status message error: {str(e)}")
            return "❓ KYC Status Unknown"


# Global service instance
simple_kyc_service = SimpleKYCVerificationService()