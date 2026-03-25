import { NextRequest, NextResponse } from 'next/server'
import { PDFDocument, rgb, StandardFonts } from 'pdf-lib'
import { createClient } from '@/utils/supabase/server'

export async function GET(
  req: NextRequest,
  { params }: { params: { loanId: string } }
) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { data: loan, error } = await supabase
    .from('loans')
    .select('*, borrower:users!loans_borrower_id_fkey(username, email), collateral(*)')
    .eq('id', params.loanId)
    .single()

  if (error || !loan) {
    return NextResponse.json({ error: 'Loan not found' }, { status: 404 })
  }

  // Only borrower, admin, or assigned agent can download
  const { data: profile } = await supabase.from('users').select('role').eq('id', user.id).single()
  const isOwner = loan.borrower_id === user.id
  const isAdminOrAgent = profile?.role === 'admin' || profile?.role === 'agent'
  if (!isOwner && !isAdminOrAgent) {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 })
  }

  // Calculations
  const principal = parseFloat(loan.principal_amount)
  const duration = loan.duration_months
  const interestRate = loan.interest_rate || 13
  const totalInterest = principal * (interestRate / 100) * duration
  const platformFee = principal * 0.01
  const insuranceFee = principal * 0.01
  const totalRepayment = principal + totalInterest + platformFee + insuranceFee
  const monthlyPayment = totalRepayment / duration

  // Build PDF
  const pdfDoc = await PDFDocument.create()
  const font = await pdfDoc.embedFont(StandardFonts.Helvetica)
  const fontBold = await pdfDoc.embedFont(StandardFonts.HelveticaBold)
  const page = pdfDoc.addPage([595.28, 841.89]) // A4

  const { width, height } = page.getSize()

  const drawText = (text: string, x: number, y: number, size = 10, bold = false, color = rgb(0, 0, 0)) => {
    page.drawText(text, { x, y, size, font: bold ? fontBold : font, color })
  }

  const drawLine = (y: number) => {
    page.drawLine({ start: { x: 50, y }, end: { x: width - 50, y }, thickness: 0.5, color: rgb(0.7, 0.7, 0.7) })
  }

  // Header
  page.drawRectangle({ x: 0, y: height - 80, width, height: 80, color: rgb(0.05, 0.34, 0.73) })
  drawText('P2P SECURE-LEND', 50, height - 35, 20, true, rgb(1, 1, 1))
  drawText('LOAN CONTRACT AGREEMENT', 50, height - 58, 12, false, rgb(0.8, 0.9, 1))
  drawText(`Generated: ${new Date().toLocaleDateString('en-KE', { year: 'numeric', month: 'long', day: 'numeric' })}`, width - 230, height - 50, 9, false, rgb(0.8, 0.9, 1))

  let y = height - 110

  // Loan ID
  drawText(`Loan Reference: #${loan.id.substring(0, 8).toUpperCase()}`, 50, y, 10, true)
  drawText(`Status: ${loan.status.toUpperCase()}`, width - 180, y, 10, true)
  y -= 20
  drawLine(y)
  y -= 20

  // Borrower
  drawText('BORROWER DETAILS', 50, y, 12, true, rgb(0.05, 0.34, 0.73))
  y -= 18
  drawText(`Full Name / Username: ${loan.borrower?.username || 'N/A'}`, 50, y, 10)
  y -= 16
  drawText(`Email: ${loan.borrower?.email || 'N/A'}`, 50, y, 10)
  y -= 20
  drawLine(y)
  y -= 20

  // Loan Terms
  drawText('LOAN TERMS', 50, y, 12, true, rgb(0.05, 0.34, 0.73))
  y -= 18

  const leftCol = 50
  const rightCol = 310

  const terms = [
    ['Principal Amount:', `KES ${principal.toFixed(2)}`],
    ['Interest Rate:', `${interestRate}% per month`],
    ['Loan Duration:', `${duration} months`],
    ['Start Date:', `${new Date(loan.created_at).toLocaleDateString()}`],
  ]
  const rightTerms = [
    ['Platform Fee (1%):', `KES ${platformFee.toFixed(2)}`],
    ['Insurance Fee (1%):', `KES ${insuranceFee.toFixed(2)}`],
    ['Total Interest:', `KES ${totalInterest.toFixed(2)}`],
    ['Total Repayment:', `KES ${totalRepayment.toFixed(2)}`],
  ]

  for (let i = 0; i < terms.length; i++) {
    drawText(terms[i][0], leftCol, y, 10, false, rgb(0.4, 0.4, 0.4))
    drawText(terms[i][1], leftCol + 120, y, 10, true)
    drawText(rightTerms[i][0], rightCol, y, 10, false, rgb(0.4, 0.4, 0.4))
    drawText(rightTerms[i][1], rightCol + 120, y, 10, true)
    y -= 16
  }

  // Monthly Payment highlight
  y -= 10
  page.drawRectangle({ x: 50, y: y - 5, width: width - 100, height: 28, color: rgb(0.9, 0.95, 1) })
  drawText('MONTHLY PAYMENT:', 60, y + 8, 11, true, rgb(0.05, 0.34, 0.73))
  drawText(`KES ${monthlyPayment.toFixed(2)}`, 200, y + 8, 13, true, rgb(0.05, 0.34, 0.73))
  y -= 30
  drawLine(y)
  y -= 20

  // Collateral
  if (loan.collateral) {
    drawText('COLLATERAL DETAILS', 50, y, 12, true, rgb(0.05, 0.34, 0.73))
    y -= 18
    drawText(`Item Type: ${loan.collateral.item_type || 'N/A'}`, 50, y, 10)
    drawText(`Brand/Model: ${loan.collateral.brand_model || 'N/A'}`, 310, y, 10)
    y -= 16
    drawText(`Market Value: KES ${parseFloat(loan.collateral.market_value || 0).toFixed(2)}`, 50, y, 10)
    drawText(`Status: ${loan.collateral.status || 'N/A'}`, 310, y, 10)
    y -= 20
    drawLine(y)
    y -= 20
  }

  // Terms & Conditions
  drawText('TERMS & CONDITIONS', 50, y, 12, true, rgb(0.05, 0.34, 0.73))
  y -= 18
  const clauses = [
    '1. The borrower agrees to repay the loan amount plus accrued interest within the agreed duration.',
    '2. Failure to repay on time will result in additional penalties as per the platform policy.',
    '3. The collateral listed above is held as security for this loan.',
    '4. This contract is legally binding and governed by Kenyan financial law.',
    '5. All disputes shall be resolved through the P2P Secure-Lend arbitration process.',
  ]
  for (const clause of clauses) {
    drawText(clause, 50, y, 9, false, rgb(0.3, 0.3, 0.3))
    y -= 14
  }

  y -= 20
  drawLine(y)
  y -= 30

  // Signature section
  drawText('AUTHORIZED SIGNATURES', 50, y, 11, true)
  y -= 30
  drawText('Borrower Signature:', 50, y, 10, false, rgb(0.4, 0.4, 0.4))
  drawText('Platform Authorized Signatory:', 310, y, 10, false, rgb(0.4, 0.4, 0.4))
  y -= 40
  page.drawLine({ start: { x: 50, y }, end: { x: 220, y }, thickness: 0.8, color: rgb(0.3, 0.3, 0.3) })
  page.drawLine({ start: { x: 310, y }, end: { x: 480, y }, thickness: 0.8, color: rgb(0.3, 0.3, 0.3) })
  y -= 12
  drawText('Borrower', 50, y, 9, false, rgb(0.5, 0.5, 0.5))
  drawText('P2P Secure-Lend Platform', 310, y, 9, false, rgb(0.5, 0.5, 0.5))

  // Footer
  page.drawRectangle({ x: 0, y: 0, width, height: 30, color: rgb(0.95, 0.95, 0.95) })
  drawText('P2P Secure-Lend Platform | Confidential Document | Generated automatically', 50, 10, 8, false, rgb(0.5, 0.5, 0.5))
  drawText(`Loan: #${loan.id.substring(0, 8).toUpperCase()}`, width - 140, 10, 8, false, rgb(0.5, 0.5, 0.5))

  const pdfBytes = await pdfDoc.save()

  return new NextResponse(Buffer.from(pdfBytes), {
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="loan-contract-${loan.id.substring(0, 8)}.pdf"`,
    },
  })
}
