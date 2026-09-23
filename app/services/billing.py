from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Bill, BillItem, Customer, Product
from app.services.gst import calculate_item_total


class BillingService:
    def __init__(self, db: Session):
        self.db = db

    def create_bill(self, customer_id: int | None = None, payment_method: str = 'cash') -> Bill:
        bill_number = f'BILL-{len(self.db.query(Bill).all()) + 1:05d}'
        bill = Bill(
            bill_number=bill_number,
            customer_id=customer_id,
            payment_method=payment_method,
            status='DRAFT',
        )
        self.db.add(bill)
        self.db.commit()
        self.db.refresh(bill)
        return bill

    def add_item_to_bill(self, bill_id: int, product_id: int, quantity: int) -> BillItem:
        bill = self.db.get(Bill, bill_id)
        product = self.db.get(Product, product_id)
        if not bill or not product:
            raise ValueError('Bill or product not found.')
        if quantity <= 0:
            raise ValueError('Quantity must be positive.')
        taxable, cgst, sgst, total_gst, total = calculate_item_total(product.selling_price, quantity, product.gst_rate)
        item = BillItem(
            bill_id=bill_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=product.selling_price,
            gst_rate=product.gst_rate,
            hsn_code=product.hsn_code,
            taxable_amount=taxable,
            cgst=cgst,
            sgst=sgst,
            total=total,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        self._recalculate_bill(bill)
        return item

    def remove_item_from_bill(self, bill_id: int, item_id: int) -> Bill:
        item = self.db.get(BillItem, item_id)
        if not item or item.bill_id != bill_id:
            raise ValueError('Item not found in this bill.')
        self.db.delete(item)
        self.db.commit()
        bill = self.db.get(Bill, bill_id)
        self._recalculate_bill(bill)
        return bill

    def update_bill_item(self, bill_id: int, item_id: int, quantity: int) -> BillItem:
        item = self.db.get(BillItem, item_id)
        if not item or item.bill_id != bill_id:
            raise ValueError('Item not found in this bill.')
        product = self.db.get(Product, item.product_id)
        taxable, cgst, sgst, total_gst, total = calculate_item_total(product.selling_price, quantity, product.gst_rate)
        item.quantity = quantity
        item.taxable_amount = taxable
        item.cgst = cgst
        item.sgst = sgst
        item.total = total
        self.db.commit()
        self.db.refresh(item)
        bill = self.db.get(Bill, bill_id)
        self._recalculate_bill(bill)
        return item

    def get_bill(self, bill_id: int) -> Bill | None:
        return self.db.get(Bill, bill_id)

    def calculate_bill(self, bill_id: int) -> dict[str, Any]:
        bill = self.db.get(Bill, bill_id)
        if not bill:
            raise ValueError('Bill not found.')
        items = self.db.query(BillItem).filter(BillItem.bill_id == bill_id).all()
        subtotal = sum((item.taxable_amount for item in items), Decimal('0'))
        cgst = sum((item.cgst for item in items), Decimal('0'))
        sgst = sum((item.sgst for item in items), Decimal('0'))
        total = sum((item.total for item in items), Decimal('0'))
        return {
            'subtotal': subtotal,
            'cgst': cgst,
            'sgst': sgst,
            'total_gst': cgst + sgst,
            'grand_total': total,
        }

    def finalize_bill(self, bill_id: int) -> Bill:
        bill = self.db.get(Bill, bill_id)
        if not bill:
            raise ValueError('Bill not found.')
        items = self.db.query(BillItem).filter(BillItem.bill_id == bill_id).all()
        if not items:
            raise ValueError('Cannot finalize an empty bill.')
        bill_values = self.calculate_bill(bill_id)
        bill.subtotal = bill_values['subtotal']
        bill.cgst = bill_values['cgst']
        bill.sgst = bill_values['sgst']
        bill.total_gst = bill_values['total_gst']
        bill.grand_total = bill_values['grand_total']
        bill.status = 'FINALIZED'
        bill.finalized_at = __import__('datetime').datetime.utcnow()
        self.db.commit()
        self.db.refresh(bill)
        return bill

    def _recalculate_bill(self, bill: Bill) -> None:
        if not bill:
            return
        values = self.calculate_bill(bill.id)
        bill.subtotal = values['subtotal']
        bill.cgst = values['cgst']
        bill.sgst = values['sgst']
        bill.total_gst = values['total_gst']
        bill.grand_total = values['grand_total']
        self.db.commit()
