import cv2
import numpy as np
from PIL import Image, ExifTags
import face_recognition
import pytesseract
import re
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


class KYCAIVerificationService:
    """AI-powered KYC verification service"""
    
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
        """Verify face match between selfie and ID photo"""
        try:
            # Load images
            selfie = face_recognition.load_image_file(selfie_image.path)
            id_photo = face_recognition.load_image_file(id_image.path)
            
            # Find face encodings
            selfie_encodings = face_recognition.face_encodings(selfie)
            id_encodings = face_recognition.face_encodings(id_photo)
            
            if not selfie_encodings or not id_encodings:
                return 0.0  # No faces found
            
            # Compare faces (use first face found in each image)
            face_distances = face_recognition.face_distance(
                [selfie_encodings[0]], 
                id_encodings[0]
            )
            
            # Convert distance to similarity score (0-100)
            similarity = (1 - face_distances[0]) * 100
            
            # Apply lenient threshold for aging
            if similarity >= 40:  # Very lenient for aging
                return min(similarity * 1.5, 100)  # Boost score for reasonable matches
            
            return similarity
            
        except Exception as e:
            logger.error(f"Face verification error: {str(e)}")
            return 0.0
    
    def _extract_and_verify_id_text(self, id_image, provided_name, provided_id, provided_dob):
        """Extract text from ID and verify against provided information"""
        result = {
            'name_match': False,
            'id_match': False,
            'dob_match': False,
            'extracted_text': '',
            'confidence': 0.0
        }
        
        try:
            # Load and preprocess image
            image = cv2.imread(id_image.path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Enhance image for better OCR
            enhanced = cv2.bilateralFilter(gray, 11, 17, 17)
            enhanced = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            # Extract text using OCR
            custom_config = r'--oem 3 --psm 6'
            extracted_text = pytesseract.image_to_string(enhanced, config=custom_config)
            result['extracted_text'] = extracted_text
            
            # Clean extracted text
            cleaned_text = re.sub(r'[^\w\s]', ' ', extracted_text.upper())
            
            # Verify name (flexible matching)
            provided_name_clean = re.sub(r'[^\w\s]', ' ', provided_name.upper())
            name_words = provided_name_clean.split()
            
            name_matches = 0
            for word in name_words:
                if len(word) > 2 and word in cleaned_text:
                    name_matches += 1
            
            result['name_match'] = name_matches >= len(name_words) * 0.6  # 60% of name words must match
            
            # Verify ID number
            id_pattern = re.sub(r'\D', '', provided_id)  # Remove non-digits
            extracted_numbers = re.findall(r'\d{7,8}', cleaned_text)
            result['id_match'] = any(id_pattern in num for num in extracted_numbers)
            
            # Verify date of birth (if provided)
            if provided_dob:
                dob_patterns = [
                    provided_dob.strftime('%d/%m/%Y'),
                    provided_dob.strftime('%d-%m-%Y'),
                    provided_dob.strftime('%d.%m.%Y'),
                    provided_dob.strftime('%Y-%m-%d'),
                ]
                
                result['dob_match'] = any(pattern in extracted_text for pattern in dob_patterns)
            
            # Calculate confidence based on matches
            matches = sum([result['name_match'], result['id_match'], result['dob_match']])
            result['confidence'] = (matches / 3) * 100
            
        except Exception as e:
            logger.error(f"ID text extraction error: {str(e)}")
            result['error'] = str(e)
        
        return result
    
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
        """Assess individual image quality"""
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return 0.0
            
            # Check image size
            height, width = image.shape[:2]
            size_score = min((width * height) / (640 * 480), 1.0) * 30  # Up to 30 points for size
            
            # Check sharpness using Laplacian variance
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness_score = min(laplacian_var / 100, 1.0) * 40  # Up to 40 points for sharpness
            
            # Check brightness
            brightness = np.mean(gray)
            brightness_score = 30 - abs(brightness - 128) / 4  # Optimal around 128, up to 30 points
            brightness_score = max(brightness_score, 0)
            
            total_score = size_score + sharpness_score + brightness_score
            return min(total_score, 100)
            
        except Exception as e:
            logger.error(f"Image quality assessment error: {str(e)}")
            return 0.0
    
    def _calculate_overall_score(self, face_score, id_text_result, quality_result):
        """Calculate overall verification score"""
        # Weighted scoring
        face_weight = 0.4  # 40% weight for face matching
        text_weight = 0.4  # 40% weight for text verification
        quality_weight = 0.2  # 20% weight for document quality
        
        overall_score = (
            face_score * face_weight +
            id_text_result['confidence'] * text_weight +
            quality_result['overall_quality'] * quality_weight
        )
        
        return min(overall_score, 100)
    
    def _generate_recommendations(self, face_score, id_text_result, quality_result):
        """Generate recommendations based on verification results"""
        recommendations = []
        
        # Face matching recommendations
        if face_score < 40:
            recommendations.append("Face match score is low. Consider retaking selfie with better lighting.")
        elif face_score < 60:
            recommendations.append("Face match is acceptable but could be improved. Ensure clear facial visibility.")
        
        # Text verification recommendations
        if not id_text_result['name_match']:
            recommendations.append("Name verification failed. Ensure ID is clear and name matches exactly.")
        
        if not id_text_result['id_match']:
            recommendations.append("ID number verification failed. Check ID clarity and number accuracy.")
        
        if not id_text_result['dob_match']:
            recommendations.append("Date of birth verification failed. Ensure DOB is clearly visible on ID.")
        
        # Quality recommendations
        if quality_result['overall_quality'] < 50:
            recommendations.append("Document quality is poor. Retake photos with better lighting and focus.")
        
        if quality_result['id_front_quality'] < 60:
            recommendations.append("ID front image quality needs improvement.")
        
        if quality_result['id_back_quality'] < 60:
            recommendations.append("ID back image quality needs improvement.")
        
        if quality_result['selfie_quality'] < 60:
            recommendations.append("Selfie quality needs improvement.")
        
        # Success message
        if not recommendations:
            recommendations.append("All verification checks passed successfully.")
        
        return recommendations


# Global service instance
kyc_ai_service = KYCAIVerificationService()