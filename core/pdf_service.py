from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from django.conf import settings
from django.core.files.base import ContentFile
import os
from datetime import datetime
import io


class LoanContractPDFGenerator:
    """Generate loan contract PDFs with borrower details and images"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=12,
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        ))
    
    def generate_contract_pdf(self, loan):
        """Generate complete loan contract PDF"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Build the PDF content
        story = []
        
        # Header
        story.append(Paragraph("P2P SECURE-LEND KENYA", self.styles['CustomTitle']))
        story.append(Paragraph("LOAN AGREEMENT CONTRACT", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Contract details
        story.extend(self._add_contract_details(loan))
        story.append(Spacer(1, 20))
        
        # Borrower information
        story.extend(self._add_borrower_info(loan))
        story.append(Spacer(1, 20))
        
        # Loan details
        story.extend(self._add_loan_details(loan))
        story.append(Spacer(1, 20))
        
        # Terms and conditions
        story.extend(self._add_terms_and_conditions(loan))
        story.append(Spacer(1, 20))
        
        # Images section
        story.extend(self._add_borrower_images(loan))
        story.append(Spacer(1, 20))
        
        # Signatures
        story.extend(self._add_signature_section(loan))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer
    
    def _add_contract_details(self, loan):
        """Add contract basic details"""
        content = []
        
        content.append(Paragraph("CONTRACT DETAILS", self.styles['CustomHeading']))
        
        details_data = [
            ['Contract Number:', f'PL-{loan.id:06d}'],
            ['Date:', datetime.now().strftime('%B %d, %Y')],
            ['Status:', loan.status.upper()],
            ['Platform:', 'P2P Secure-Lend Kenya'],
        ]
        
        details_table = Table(details_data, colWidths=[2*inch, 3*inch])
        details_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        content.append(details_table)
        return content
    
    def _add_borrower_info(self, loan):
        """Add borrower information"""
        content = []
        borrower = loan.borrower
        
        content.append(Paragraph("BORROWER INFORMATION", self.styles['CustomHeading']))
        
        # Get KYC info if available
        kyc_info = None
        try:
            kyc_info = borrower.kyc
        except:
            pass
        
        borrower_data = [
            ['Full Name:', kyc_info.full_name if kyc_info else f'{borrower.first_name} {borrower.last_name}'],
            ['Username:', borrower.username],
            ['Email:', borrower.email],
            ['Phone Number:', borrower.phone_number],
            ['National ID:', kyc_info.id_number if kyc_info else borrower.national_id],
            ['Date of Birth:', kyc_info.date_of_birth.strftime('%B %d, %Y') if kyc_info and kyc_info.date_of_birth else 'Not provided'],
        ]
        
        borrower_table = Table(borrower_data, colWidths=[2*inch, 3*inch])
        borrower_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        content.append(borrower_table)
        return content
    
    def _add_loan_details(self, loan):
        """Add loan financial details"""
        content = []
        
        content.append(Paragraph("LOAN DETAILS", self.styles['CustomHeading']))
        
        loan_data = [
            ['Principal Amount:', f'KES {loan.principal_amount:,.2f}'],
            ['Interest Rate:', f'{loan.interest_rate}% per month'],
            ['Duration:', f'{loan.duration_months} months'],
            ['Platform Fee:', f'KES {loan.calculate_platform_fee():,.2f}'],
            ['Insurance Fee:', f'KES {loan.calculate_insurance_fee():,.2f}'],
            ['Monthly Payment:', f'KES {loan.calculate_monthly_payment():,.2f}'],
            ['Total Repayment:', f'KES {loan.calculate_total_repayment():,.2f}'],
            ['Funded Amount:', f'KES {loan.funded_amount:,.2f}'],
            ['Funding Status:', f'{loan.get_funding_percentage():.1f}% funded'],
        ]
        
        loan_table = Table(loan_data, colWidths=[2*inch, 3*inch])
        loan_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, -3), (-1, -1), colors.lightgrey),
        ]))
        
        content.append(loan_table)
        
        # Collateral details
        content.append(Spacer(1, 12))
        content.append(Paragraph("COLLATERAL DETAILS", self.styles['CustomHeading']))
        
        collateral = loan.collateral
        collateral_data = [
            ['Item Type:', collateral.item_type],
            ['Brand/Model:', collateral.brand_model],
            ['Market Value:', f'KES {collateral.market_value:,.2f}'],
            ['Verified Value:', f'KES {collateral.get_current_value():,.2f}'],
            ['Max Loan Amount:', f'KES {collateral.calculate_max_loan_amount():,.2f}'],
            ['Verification Status:', collateral.status.title()],
        ]
        
        collateral_table = Table(collateral_data, colWidths=[2*inch, 3*inch])
        collateral_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        content.append(collateral_table)
        return content
    
    def _add_terms_and_conditions(self, loan):
        """Add terms and conditions"""
        content = []
        
        content.append(Paragraph("TERMS AND CONDITIONS", self.styles['CustomHeading']))
        
        terms = [
            "1. <b>Loan Purpose:</b> This loan is secured by the collateral described above and must be repaid according to the agreed schedule.",
            
            "2. <b>Interest and Fees:</b> The borrower agrees to pay interest at the rate specified above, plus platform and insurance fees.",
            
            "3. <b>Repayment Schedule:</b> Monthly payments are due on the same date each month. Late payments will incur additional penalties.",
            
            "4. <b>Collateral Security:</b> The collateral remains in the custody of P2P Secure-Lend Kenya until full loan repayment.",
            
            "5. <b>Default Consequences:</b> Failure to make payments for 30 days will result in loan default and collateral forfeiture.",
            
            "6. <b>Early Repayment:</b> The borrower may repay the loan early without penalty, with interest calculated pro-rata.",
            
            "7. <b>Platform Responsibilities:</b> P2P Secure-Lend Kenya facilitates the loan but is not the lender. Lenders assume credit risk.",
            
            "8. <b>Dispute Resolution:</b> Any disputes will be resolved through arbitration under Kenyan law.",
            
            "9. <b>Data Protection:</b> Personal information is protected according to Kenya's Data Protection Act.",
            
            "10. <b>Agreement Binding:</b> This agreement is legally binding upon signature by all parties."
        ]
        
        for term in terms:
            content.append(Paragraph(term, self.styles['CustomBody']))
            content.append(Spacer(1, 6))
        
        return content
    
    def _add_borrower_images(self, loan):
        """Add borrower KYC images"""
        content = []
        
        try:
            kyc = loan.borrower.kyc
            if kyc and kyc.status == 'verified':
                content.append(Paragraph("BORROWER IDENTIFICATION", self.styles['CustomHeading']))
                
                # Create image table
                images_data = []
                image_row = []
                
                # Add images if they exist
                if kyc.id_front_image:
                    try:
                        img = Image(kyc.id_front_image.path, width=2*inch, height=1.5*inch)
                        image_row.append(img)
                    except:
                        image_row.append("ID Front\n(Image not available)")
                
                if kyc.id_back_image:
                    try:
                        img = Image(kyc.id_back_image.path, width=2*inch, height=1.5*inch)
                        image_row.append(img)
                    except:
                        image_row.append("ID Back\n(Image not available)")
                
                if kyc.selfie_image:
                    try:
                        img = Image(kyc.selfie_image.path, width=2*inch, height=1.5*inch)
                        image_row.append(img)
                    except:
                        image_row.append("Selfie\n(Image not available)")
                
                if image_row:
                    images_data.append(image_row)
                    images_data.append(['ID Front', 'ID Back', 'Selfie Photo'])
                    
                    images_table = Table(images_data, colWidths=[2*inch, 2*inch, 2*inch])
                    images_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('FONTSIZE', (0, 1), (-1, 1), 8),
                        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
                    ]))
                    
                    content.append(images_table)
                    
                    # Add note about image removal
                    content.append(Spacer(1, 12))
                    content.append(Paragraph(
                        "<i>Note: These images have been removed from the user's account for security purposes after contract generation.</i>",
                        self.styles['CustomBody']
                    ))
        except:
            content.append(Paragraph("BORROWER IDENTIFICATION", self.styles['CustomHeading']))
            content.append(Paragraph("KYC verification pending or images not available.", self.styles['CustomBody']))
        
        return content
    
    def _add_signature_section(self, loan):
        """Add signature section"""
        content = []
        
        content.append(Paragraph("SIGNATURES", self.styles['CustomHeading']))
        
        # Borrower signature
        try:
            kyc = loan.borrower.kyc
            if kyc and kyc.signature_image:
                content.append(Paragraph("Borrower Signature:", self.styles['CustomBody']))
                try:
                    sig_img = Image(kyc.signature_image.path, width=2*inch, height=1*inch)
                    content.append(sig_img)
                except:
                    content.append(Paragraph("(Signature not available)", self.styles['CustomBody']))
            else:
                content.append(Paragraph("Borrower Signature: _________________________", self.styles['CustomBody']))
        except:
            content.append(Paragraph("Borrower Signature: _________________________", self.styles['CustomBody']))
        
        content.append(Spacer(1, 20))
        content.append(Paragraph(f"Borrower Name: {loan.borrower.username}", self.styles['CustomBody']))
        content.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", self.styles['CustomBody']))
        
        content.append(Spacer(1, 30))
        content.append(Paragraph("Platform Representative: _________________________", self.styles['CustomBody']))
        content.append(Spacer(1, 20))
        content.append(Paragraph("P2P Secure-Lend Kenya", self.styles['CustomBody']))
        content.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", self.styles['CustomBody']))
        
        return content
    
    def save_contract_pdf(self, loan):
        """Generate and save contract PDF to loan model"""
        pdf_buffer = self.generate_contract_pdf(loan)
        
        # Create filename
        filename = f'loan_contract_{loan.id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        # Save to loan model
        loan.contract_pdf.save(
            filename,
            ContentFile(pdf_buffer.getvalue()),
            save=True
        )
        
        return loan.contract_pdf.url


# Global instance
pdf_generator = LoanContractPDFGenerator()