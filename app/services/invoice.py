from __future__ import annotations

from io import BytesIO
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.database.models import Bill, BillItem, Customer, Product


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def render_pdf(self, bill_id: int) -> bytes:
        bill = self.db.get(Bill, bill_id)
        if not bill:
            raise ValueError('Bill not found.')
        if bill.status != 'FINALIZED':
            raise ValueError('Only finalized bills can be exported as invoices.')

        items = self.db.query(BillItem, Product).join(Product, Product.id == BillItem.product_id).filter(
            BillItem.bill_id == bill_id
        ).all()
        if not items:
            raise ValueError('Cannot export an empty bill.')

        customer = self.db.get(Customer, bill.customer_id) if bill.customer_id else None
        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=16 * mm,
            leftMargin=16 * mm,
            topMargin=14 * mm,
            bottomMargin=14 * mm,
        )
        styles = getSampleStyleSheet()
        story = [
            Paragraph(self.settings.store_name, styles['Title']),
            Paragraph(self.settings.store_address, styles['Normal']),
            Paragraph(f'GSTIN: {self.settings.store_gstin}', styles['Normal']),
            Spacer(1, 8),
            Paragraph(f'<b>Tax Invoice</b> &nbsp; {bill.bill_number}', styles['Heading2']),
            Paragraph(
                f"Customer: {customer.name if customer else 'Walk-in customer'}"
                + (f" &nbsp; Phone: {customer.phone}" if customer and customer.phone else ''),
                styles['Normal'],
            ),
            Spacer(1, 8),
        ]

        rows = [['Item', 'Qty', 'Rate', 'GST', 'Total']]
        for item, product in items:
            rows.append([
                product.name,
                str(item.quantity),
                f'Rs {Decimal(item.unit_price):.2f}',
                f'{Decimal(item.gst_rate):.2f}%',
                f'Rs {Decimal(item.total):.2f}',
            ])
        rows.extend([
            ['', '', '', 'Subtotal', f'Rs {Decimal(bill.subtotal):.2f}'],
            ['', '', '', 'CGST + SGST', f'Rs {Decimal(bill.total_gst):.2f}'],
            ['', '', '', 'Grand total', f'Rs {Decimal(bill.grand_total):.2f}'],
        ])
        table = Table(rows, colWidths=[78 * mm, 18 * mm, 28 * mm, 25 * mm, 30 * mm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#17324d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#b8c2cc')),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (-2, -3), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (-2, -1), (-1, -1), colors.HexColor('#e8f0f4')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
        story.append(Spacer(1, 10))
        story.append(Paragraph(f'Payment method: {bill.payment_method}', styles['Normal']))
        document.build(story)
        return buffer.getvalue()

    def filename(self, bill_id: int) -> str:
        bill = self.db.get(Bill, bill_id)
        if not bill:
            raise ValueError('Bill not found.')
        return f'{bill.bill_number}.pdf'
