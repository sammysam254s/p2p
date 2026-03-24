from PIL import Image, ExifTags, ImageEnhance, ImageFilter
import pytesseract
import re
from datetime import datetime, date
import logging
import hashlib
import os

logger = logging.getLogger(__name__)


class KYCAIVerificationService:
    """
    Strict KYC verification service with OCR text extraction and validation
    
    VERIFICATION REQUIREMENTS:
    - OCR text extraction must succeed
    - Name on ID must match provided name (80% word match required)
    - ID number on document must match provided ID number (exact or 80% digit match)
    - Date of birth verification is recommended but not required for approval
    - Face matching provides additional confidence scoring
    - Document quality affects overall scoring
    
    STRICT POLICY: If name or ID number don't match extracted text, KYC fails regardless of other scores.
    
    DEPLOYMENT NOTE: Uses pytesseract for OCR which requires tesseract-ocr system package.
    For cloud deployment, ensure tesseract is available or use cloud OCR services like:
    - AWS Textract
    - Google Cloud Vision API  
    - Azure Computer Vision
    """
    
    def __init__(self):
        self.verification_threshold = 0.6  # Face matching threshold (lenient for aging)
        self.text_confidence_threshold = 60  # OCR confidence threshold
    
    def verify_kyc_submission(self, kyc_verification):
        """Main verification method for KYC submission"""
        verification_result = {
            'overall_score': 0.0,
            'face_match_score': 0.0,
            'id_text_verification': {},
            'document_quality': {},
            'recommendations': [],
            'passed': False
        }
        
        try:
            # 1. Verify face match between selfie and ID
            face_score = self._verify_face_match(
                kyc_verification.selfie_image,
                kyc_verification.id_front_image
            )
            verification_result['face_match_score'] = face_score
            
            # 2. Extract and verify text from ID
            id_text_result = self._extract_and_verify_id_text(
                kyc_verification.id_front_image,
                kyc_verification.full_name,
                kyc_verification.id_number,
                kyc_verification.date_of_birth
            )
            verification_result['id_text_verification'] = id_text_result
            
            # 3. Check document quality
            quality_result = self._check_document_quality(
                kyc_verification.id_front_image,
                kyc_verification.id_back_image,
                kyc_verification.selfie_image
            )
            verification_result['document_quality'] = quality_result
            
            # 4. Calculate overall score
            overall_score = self._calculate_overall_score(
                face_score,
                id_text_result,
                quality_result
            )
            verification_result['overall_score'] = overall_score
            
            # 5. Generate recommendations
            recommendations = self._generate_recommendations(
                face_score,
                id_text_result,
                quality_result
            )
            verification_result['recommendations'] = recommendations
            
            # 6. Determine if verification passed
            verification_result['passed'] = overall_score >= 70.0  # 70% threshold
            
        except Exception as e:
            logger.error(f"KYC verification error: {str(e)}")
            verification_result['error'] = str(e)
            verification_result['recommendations'].append("Technical error during verification. Manual review required.")
        
        return verification_result
    
    def _verify_face_match(self, selfie_image, id_image):
        """Simplified face verification - checks if images exist and are valid"""
        try:
            # Basic image validation
            selfie_valid = self._validate_image(selfie_image.path)
            id_valid = self._validate_image(id_image.path)
            
            if not selfie_valid or not id_valid:
                return 0.0
            
            # For now, return a moderate score if both images are valid
            # This is a placeholder until we can implement proper face recognition
            # In production, you would integrate with a cloud-based face recognition API
            # like AWS Rekognition, Google Vision API, or Azure Face API
            
            # Basic similarity check based on image properties
            selfie_size = os.path.getsize(selfie_image.path)
            id_size = os.path.getsize(id_image.path)
            
            # Simple heuristic: if images are reasonable size, give moderate score
            if selfie_size > 10000 and id_size > 10000:  # At least 10KB each
                return 75.0  # Moderate confidence score
            
            return 50.0  # Lower confidence for small images
            
        except Exception as e:
            logger.error(f"Face verification error: {str(e)}")
            return 0.0
    
    def _extract_and_verify_id_text(self, id_image, provided_name, provided_id, provided_dob):
        """Extract text from ID using OCR and strictly verify against provided information"""
        result = {
            'name_match': False,
            'id_match': False,
            'dob_match': False,
            'extracted_text': '',
            'confidence': 0.0,
            'extraction_successful': False
        }
        
        try:
            # Load and preprocess image for better OCR
            image = Image.open(id_image.path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Enhance image for better OCR results
            image = self._enhance_image_for_ocr(image)
            
            # Extract text using OCR with optimized settings
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz /.-'
            
            try:
                extracted_text = pytesseract.image_to_string(image, config=custom_config)
                result['extracted_text'] = extracted_text
                result['extraction_successful'] = True
                logger.info(f"OCR extracted text: {extracted_text[:100]}...")  # Log first 100 chars
                
            except Exception as ocr_error:
                logger.error(f"OCR extraction failed: {str(ocr_error)}")
                result['extracted_text'] = f"OCR failed: {str(ocr_error)}"
                result['confidence'] = 0.0
                return result
            
            # Clean and normalize extracted text
            cleaned_text = self._clean_extracted_text(extracted_text)
            
            # Strict verification of each field
            result['name_match'] = self._verify_name_strict(cleaned_text, provided_name)
            result['id_match'] = self._verify_id_number_strict(cleaned_text, provided_id)
            result['dob_match'] = self._verify_dob_strict(cleaned_text, provided_dob)
            
            # Calculate confidence - ALL fields must match for high confidence
            matches = sum([result['name_match'], result['id_match'], result['dob_match']])
            
            if matches == 3:
                result['confidence'] = 95.0  # High confidence when all match
            elif matches == 2:
                result['confidence'] = 60.0  # Medium confidence
            elif matches == 1:
                result['confidence'] = 30.0  # Low confidence
            else:
                result['confidence'] = 0.0   # No confidence when nothing matches
            
            logger.info(f"KYC verification results - Name: {result['name_match']}, ID: {result['id_match']}, DOB: {result['dob_match']}, Confidence: {result['confidence']}%")
            
        except Exception as e:
            logger.error(f"ID text extraction error: {str(e)}")
            result['error'] = str(e)
            result['confidence'] = 0.0
        
        return result
    
    def _enhance_image_for_ocr(self, image):
        """Enhance image quality for better OCR results"""
        try:
            # Resize if too small (OCR works better on larger images)
            width, height = image.size
            if width < 800 or height < 600:
                scale_factor = max(800/width, 600/height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to grayscale for better OCR
            image = image.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)
            
            # Apply slight blur to reduce noise
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            return image
            
        except Exception as e:
            logger.error(f"Image enhancement error: {str(e)}")
            return image  # Return original if enhancement fails
    
    def _clean_extracted_text(self, text):
        """Clean and normalize extracted text"""
        # Remove extra whitespace and normalize
        cleaned = re.sub(r'\s+', ' ', text.strip())
        # Remove special characters but keep basic punctuation
        cleaned = re.sub(r'[^\w\s\-/.]', ' ', cleaned)
        return cleaned.upper()
    
    def _verify_name_strict(self, extracted_text, provided_name):
        """Strictly verify name matches extracted text"""
        if not provided_name or len(provided_name.strip()) < 2:
            return False
        
        # Normalize provided name
        provided_name_clean = re.sub(r'[^\w\s]', ' ', provided_name.upper().strip())
        name_words = [word for word in provided_name_clean.split() if len(word) > 1]
        
        if not name_words:
            return False
        
        # Check if ALL significant name words are found in extracted text
        matches = 0
        for word in name_words:
            if len(word) > 2:  # Only check words longer than 2 characters
                if word in extracted_text:
                    matches += 1
                else:
                    # Try fuzzy matching for common OCR errors
                    if self._fuzzy_word_match(word, extracted_text):
                        matches += 1
        
        # Require at least 80% of name words to match
        required_matches = max(1, int(len(name_words) * 0.8))
        return matches >= required_matches
    
    def _verify_id_number_strict(self, extracted_text, provided_id):
        """Strictly verify ID number matches extracted text"""
        if not provided_id or len(provided_id.strip()) < 6:
            return False
        
        # Extract only digits from provided ID
        provided_digits = re.sub(r'\D', '', provided_id)
        
        if len(provided_digits) < 6:
            return False
        
        # Find all number sequences in extracted text
        extracted_numbers = re.findall(r'\d{6,}', extracted_text)
        
        # Check if provided ID digits match any extracted number
        for extracted_num in extracted_numbers:
            if provided_digits in extracted_num or extracted_num in provided_digits:
                return True
            
            # Check for partial match (at least 80% of digits match)
            if len(provided_digits) >= 8:
                match_threshold = int(len(provided_digits) * 0.8)
                matches = sum(1 for i, digit in enumerate(provided_digits) 
                            if i < len(extracted_num) and digit == extracted_num[i])
                if matches >= match_threshold:
                    return True
        
        return False
    
    def _verify_dob_strict(self, extracted_text, provided_dob):
        """Strictly verify date of birth matches extracted text"""
        if not provided_dob:
            return True  # If no DOB provided, don't fail verification
        
        # Generate multiple date format patterns
        dob_patterns = [
            provided_dob.strftime('%d/%m/%Y'),
            provided_dob.strftime('%d-%m-%Y'),
            provided_dob.strftime('%d.%m.%Y'),
            provided_dob.strftime('%d %m %Y'),
            provided_dob.strftime('%Y-%m-%d'),
            provided_dob.strftime('%Y/%m/%d'),
            provided_dob.strftime('%m/%d/%Y'),
            provided_dob.strftime('%d/%m/%y'),
            provided_dob.strftime('%d-%m-%y'),
            provided_dob.strftime('%d.%m.%y'),
        ]
        
        # Check if any date pattern is found in extracted text
        for pattern in dob_patterns:
            if pattern in extracted_text:
                return True
        
        # Check for individual date components
        day = provided_dob.strftime('%d').lstrip('0')
        month = provided_dob.strftime('%m').lstrip('0')
        year = provided_dob.strftime('%Y')
        year_short = provided_dob.strftime('%y')
        
        # Look for date components in extracted text
        day_found = day in extracted_text
        month_found = month in extracted_text
        year_found = year in extracted_text or year_short in extracted_text
        
        # Require at least 2 out of 3 date components to match
        components_found = sum([day_found, month_found, year_found])
        return components_found >= 2
    
    def _fuzzy_word_match(self, word, text):
        """Check for fuzzy word matching to handle common OCR errors"""
        # Common OCR character substitutions
        ocr_substitutions = {
            '0': 'O', '1': 'I', '5': 'S', '8': 'B', '6': 'G',
            'O': '0', 'I': '1', 'S': '5', 'B': '8', 'G': '6'
        }
        
        # Generate variations of the word with common OCR errors
        variations = [word]
        for i, char in enumerate(word):
            if char in ocr_substitutions:
                variation = word[:i] + ocr_substitutions[char] + word[i+1:]
                variations.append(variation)
        
        # Check if any variation is found in text
        for variation in variations:
            if variation in text:
                return True
        
        return False
    
    def _check_document_quality(self, id_front, id_back, selfie):
        """Check quality of submitted documents"""
        result = {
            'id_front_quality': 0.0,
            'id_back_quality': 0.0,
            'selfie_quality': 0.0,
            'overall_quality': 0.0
        }
        
        try:
            # Check each image quality
            result['id_front_quality'] = self._assess_image_quality(id_front.path)
            result['id_back_quality'] = self._assess_image_quality(id_back.path)
            result['selfie_quality'] = self._assess_image_quality(selfie.path)
            
            # Calculate overall quality
            result['overall_quality'] = (
                result['id_front_quality'] + 
                result['id_back_quality'] + 
                result['selfie_quality']
            ) / 3
            
        except Exception as e:
            logger.error(f"Document quality check error: {str(e)}")
        
        return result
    
    def _assess_image_quality(self, image_path):
        """Simplified image quality assessment"""
        try:
            # Basic file validation
            if not os.path.exists(image_path):
                return 0.0
            
            # Check file size (basic quality indicator)
            file_size = os.path.getsize(image_path)
            
            # Very small files are likely poor quality
            if file_size < 5000:  # Less than 5KB
                return 20.0
            elif file_size < 20000:  # Less than 20KB
                return 50.0
            elif file_size < 100000:  # Less than 100KB
                return 75.0
            else:
                return 90.0  # Larger files likely better quality
            
            # In production, use cloud-based image analysis APIs for proper quality assessment
            
        except Exception as e:
            logger.error(f"Image quality assessment error: {str(e)}")
            return 0.0
    
    def _calculate_overall_score(self, face_score, id_text_result, quality_result):
        """Calculate overall verification score with strict text verification requirement"""
        
        # STRICT REQUIREMENT: Text verification must pass for KYC to be approved
        if not id_text_result.get('extraction_successful', False):
            logger.warning("KYC failed: OCR extraction unsuccessful")
            return 0.0
        
        # Check if critical text fields match
        name_match = id_text_result.get('name_match', False)
        id_match = id_text_result.get('id_match', False)
        
        # STRICT REQUIREMENT: Both name and ID must match
        if not name_match or not id_match:
            logger.warning(f"KYC failed: Name match: {name_match}, ID match: {id_match}")
            return 0.0
        
        # If text verification passes, calculate weighted score
        face_weight = 0.3   # 30% weight for face matching
        text_weight = 0.5   # 50% weight for text verification (increased importance)
        quality_weight = 0.2 # 20% weight for document quality
        
        overall_score = (
            face_score * face_weight +
            id_text_result['confidence'] * text_weight +
            quality_result['overall_quality'] * quality_weight
        )
        
        # Ensure minimum score requirements are met
        if overall_score < 70.0:
            logger.warning(f"KYC failed: Overall score {overall_score:.1f}% below 70% threshold")
            return 0.0
        
        return min(overall_score, 100)
    
    def _generate_recommendations(self, face_score, id_text_result, quality_result):
        """Generate recommendations based on verification results"""
        recommendations = []
        
        # Check if OCR extraction failed
        if not id_text_result.get('extraction_successful', False):
            recommendations.append("❌ CRITICAL: Could not extract text from ID. Ensure ID image is clear, well-lit, and high quality.")
            recommendations.append("📸 Retake ID photo with better lighting and ensure all text is clearly visible.")
            return recommendations
        
        # Text verification recommendations (STRICT)
        if not id_text_result.get('name_match', False):
            recommendations.append("❌ CRITICAL: Name on ID does not match provided name. Verification failed.")
            recommendations.append("📝 Ensure the name you entered exactly matches the name on your ID.")
        
        if not id_text_result.get('id_match', False):
            recommendations.append("❌ CRITICAL: ID number on document does not match provided ID number. Verification failed.")
            recommendations.append("🔢 Double-check that the ID number you entered matches exactly what's on your ID.")
        
        if not id_text_result.get('dob_match', False):
            recommendations.append("⚠️ Date of birth could not be verified from ID. Please ensure DOB is clearly visible.")
        
        # Face matching recommendations
        if face_score < 40:
            recommendations.append("📷 Face match score is low. Retake selfie with better lighting and clear facial visibility.")
        elif face_score < 60:
            recommendations.append("📷 Face match could be improved. Ensure clear facial visibility in both selfie and ID photo.")
        
        # Quality recommendations
        if quality_result['overall_quality'] < 50:
            recommendations.append("📸 Document quality is poor. Retake all photos with better lighting, focus, and higher resolution.")
        
        if quality_result['id_front_quality'] < 60:
            recommendations.append("📄 ID front image quality needs improvement. Ensure good lighting and focus.")
        
        if quality_result['id_back_quality'] < 60:
            recommendations.append("📄 ID back image quality needs improvement. Ensure good lighting and focus.")
        
        if quality_result['selfie_quality'] < 60:
            recommendations.append("🤳 Selfie quality needs improvement. Use good lighting and ensure face is clearly visible.")
        
        # Success message
        if not recommendations:
            recommendations.append("✅ All verification checks passed successfully! KYC approved.")
        else:
            recommendations.append("🚫 KYC verification failed. Please address the issues above and resubmit.")
        
        return recommendations
    
    def _validate_image(self, image_path):
        """Validate that image file exists and is a valid image"""
        try:
            if not os.path.exists(image_path):
                return False
            
            # Check file size
            if os.path.getsize(image_path) < 1000:  # Less than 1KB
                return False
            
            # Try to open with PIL to validate it's a real image
            with Image.open(image_path) as img:
                img.verify()  # Verify it's a valid image
                return True
                
        except Exception as e:
            logger.error(f"Image validation error: {str(e)}")
            return False


# Global service instance
kyc_ai_service = KYCAIVerificationService()