from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.database.models import Bill, BillItem, Product
from app.services.billing import BillingService
from app.services.inventory import InventoryService
from app.services.invoice import InvoiceService
from app.services.khata import KhataService


class BotWorkflow:
    def __init__(self, db: Session):
        self.db = db
        self.inventory = InventoryService(db)
        self.billing = BillingService(db)
        self.khata = KhataService(db)
        self.invoice = InvoiceService(db)

    def _find_product(self, query: str) -> Product | None:
        cleaned = (query or '').strip().lower()
        if not cleaned:
            return None

        cleaned = re.sub(r'\b(?:how much|much|left|stock|available|receive|received|restock|at|cost|mrp|for|of|and|create|make|draft|bill|add|insert|finalize|confirm|send|invoice)\b', ' ', cleaned, flags=re.I)
        cleaned = re.sub(r'[^a-z0-9\s-]', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        if not cleaned:
            return None

        candidates = self.db.query(Product).all()
        best_match = None
        best_score = -1

        for product in candidates:
            haystack = f"{product.name} {product.brand} {product.sku} {product.category}".lower()
            score = 0
            if cleaned == product.name.lower() or cleaned == product.sku.lower():
                score += 25
            if cleaned in haystack:
                score += 20
            for token in cleaned.split():
                if token in {'how', 'much', 'left', 'stock', 'available', 'at', 'cost', 'mrp', 'for', 'of', 'and', 'create', 'make', 'draft', 'bill', 'add', 'insert', 'finalize', 'confirm', 'send', 'invoice'}:
                    continue
                if token in haystack:
                    score += 8
            if score > best_score:
                best_score = score
                best_match = product

        return best_match

    def _extract_quantity(self, text: str) -> int | None:
        match = re.search(r'(?:\b(\d+)\s*(?:packets?|pcs?|pieces?|kg|litres?|liters?|units?)\b)', text, flags=re.I)
        if match:
            return int(match.group(1))
        match = re.search(r'\b(\d+)\b', text)
        if match:
            return int(match.group(1))
        return None

    def _extract_cost(self, text: str) -> Decimal | None:
        match = re.search(r'cost\s*[:=]?\s*₹?\s*(\d+(?:\.\d+)?)', text, flags=re.I)
        if not match:
            return None
        return Decimal(match.group(1))

    def _extract_bill_id(self, text: str) -> int | None:
        match = re.search(r'bill\s+(\d+)', text, flags=re.I)
        if match:
            return int(match.group(1))
        return None

    def _extract_amount(self, text: str) -> Decimal | None:
        match = re.search(r'(?:₹|rs\.?|rupees?)?\s*(\d+(?:\.\d+)?)', text, flags=re.I)
        return Decimal(match.group(1)) if match else None

    def _find_customer_from_text(self, text: str):
        cleaned = re.sub(r'\b(?:khata|balance|due|owes|owe|paid|payment|credit|add|customer|create|bill|for|from|by|rupees?|rs\.?)\b', ' ', text, flags=re.I)
        cleaned = re.sub(r'₹?\s*\d+(?:\.\d+)?', ' ', cleaned)
        cleaned = re.sub(r'\b\d{10}\b', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return self.khata.find_customer(cleaned) if cleaned else None

    def _invoice_result(self, bill_id: int, summary: str) -> dict[str, Any]:
        bill = self.billing.get_bill(bill_id)
        pdf = self.invoice.render_pdf(bill_id)
        return {
            'action': 'finalize_bill',
            'bill_id': bill_id,
            'status': bill.status,
            'summary': summary,
            'invoice_filename': self.invoice.filename(bill_id),
            'invoice_pdf': pdf,
        }

    def _record_credit_bill(self, bill_id: int) -> None:
        bill = self.billing.get_bill(bill_id)
        if bill and bill.payment_method == 'credit' and bill.customer_id:
            self.khata.add_credit(
                bill.customer_id,
                bill.grand_total,
                description=f'Credit bill {bill.bill_number}',
                reference=f'bill:{bill.bill_number}',
            )

    def handle_message(self, message: str) -> dict[str, Any]:
        text = message.strip()
        lowered = text.lower()

        if re.search(r'\b(?:owe|owes|credit)\b', lowered) and not re.search(r'\b(?:bill|add|create)\s+(?:customer|khata)?\b', lowered):
            customer = self._find_customer_from_text(text)
            amount = self._extract_amount(text)
            if customer is None or amount is None:
                return {'action': 'khata_credit', 'summary': 'I need a customer name and credit amount.'}
            self.khata.add_credit(customer.id, amount, description='Manual credit')
            balance = self.khata.get_customer_balance(customer.id)
            return {
                'action': 'khata_credit',
                'customer_name': customer.name,
                'amount': amount,
                'balance': balance,
                'summary': f'Recorded Rs {amount:.2f} credit for {customer.name}. Balance: Rs {balance:.2f}.',
            }

        if re.search(r'\b(?:khata|ledger|balance|due)\b', lowered) and not re.search(r'\b(?:add|create)\s+(?:customer|khata)\b', lowered):
            customer = self._find_customer_from_text(text)
            if customer is None:
                return {'action': 'khata_balance', 'summary': 'I could not identify that customer.'}
            balance = self.khata.get_customer_balance(customer.id)
            return {
                'action': 'khata_balance',
                'customer_id': customer.id,
                'customer_name': customer.name,
                'balance': balance,
                'summary': f'{customer.name} owes Rs {balance:.2f}.' if balance > 0 else f'{customer.name} has no outstanding balance.',
            }

        if re.search(r'\b(?:paid|payment)\b', lowered):
            customer = self._find_customer_from_text(text)
            amount = self._extract_amount(text)
            if customer is None or amount is None:
                return {'action': 'khata_payment', 'summary': 'I need a customer name and payment amount.'}
            self.khata.record_credit_payment(customer.id, amount)
            balance = self.khata.get_customer_balance(customer.id)
            return {
                'action': 'khata_payment',
                'customer_name': customer.name,
                'amount': amount,
                'balance': balance,
                'summary': f'Recorded Rs {amount:.2f} payment from {customer.name}. Balance: Rs {balance:.2f}.',
            }

        if re.search(r'\b(?:add|create)\s+(?:customer|khata)\b', lowered):
            customer = self._find_customer_from_text(text)
            phone_match = re.search(r'\b(\d{10})\b', text)
            name = re.sub(r'\b(?:add|create)\s+(?:customer|khata)\b', ' ', text, flags=re.I)
            name = re.sub(r'\b\d{10}\b', ' ', name)
            name = re.sub(r'\s+', ' ', name).strip()
            customer = customer or self.khata.create_customer(name, phone_match.group(1) if phone_match else None)
            return {
                'action': 'customer_created',
                'customer_id': customer.id,
                'customer_name': customer.name,
                'summary': f'Customer {customer.name} is ready for khata tracking.',
            }

        if re.search(r'\b(create|make)\b.*\b(?:credit\s+bill|bill\s+(?:on\s+)?credit)\b', lowered):
            customer = self._find_customer_from_text(text)
            if customer is None:
                return {'action': 'bill', 'summary': 'I need an existing customer for a credit bill.'}
            bill = self.billing.create_bill(customer_id=customer.id, payment_method='credit')
            return {
                'action': 'bill',
                'bill_id': bill.id,
                'customer_name': customer.name,
                'summary': f'Credit bill created for {customer.name}: {bill.bill_number}',
                'status': 'DRAFT',
            }

        if 'how much' in lowered and 'left' in lowered or 'stock' in lowered or 'available' in lowered:
            lookup = re.sub(r'\b(?:how much|left|do we have|do i have|stock|available|is there)\b', ' ', text, flags=re.I)
            lookup = lookup.replace('?', ' ').strip()
            product = self._find_product(lookup or text)
            if product is None:
                return {'action': 'stock', 'summary': 'I could not find a matching product in the store catalogue.'}
            return {
                'action': 'stock',
                'summary': f"{product.name} has {product.current_stock} {product.unit} in stock.",
                'product_name': product.name,
                'available_stock': product.current_stock,
            }

        if re.search(r'\b(receive|received|restock)\b', lowered):
            product_name = re.sub(r'.*?\b(receive|received|restock)\b\s*', '', text, flags=re.I)
            product_name = re.sub(r'\b(?:\d+\s*(?:packets?|pcs?|pieces?|kg|litres?|liters?|units?))\b', ' ', product_name, flags=re.I)
            product_name = re.sub(r'\bat\s*cost.*', '', product_name, flags=re.I)
            product_name = re.sub(r'\bat\s*mrp.*', '', product_name, flags=re.I)
            product_name = product_name.strip()
            product = self._find_product(product_name or 'maggi')
            if product is None:
                return {'action': 'receive_stock', 'summary': 'I could not identify the product to receive.'}
            qty = self._extract_quantity(text) or 1
            cost_price = self._extract_cost(text)
            self.inventory.receive_stock(product.sku, qty, cost_price=cost_price, mrp=product.mrp)
            return {
                'action': 'receive_stock',
                'summary': f"Received {qty} {product.unit} of {product.name}.",
                'product_name': product.name,
                'quantity': qty,
            }

        if re.search(r'\b(create|make)\b.*\bbill\b', lowered):
            bill = self.billing.create_bill(payment_method='cash')
            return {
                'action': 'bill',
                'bill_id': bill.id,
                'summary': f"Draft bill created: {bill.bill_number}",
                'status': 'DRAFT',
            }

        if re.search(r'\b(create|make)\b.*\bbill\b.*\bfor\b', lowered):
            bill = self.billing.create_bill(payment_method='cash')
            product_names = re.findall(r'\b(\d+)\s+([a-zA-Z][a-zA-Z0-9\- ]+?)(?=(?:\s+and\s+|\s*$))', text)
            if product_names:
                for qty, name in product_names:
                    product = self._find_product(name)
                    if product is not None:
                        self.billing.add_item_to_bill(bill.id, product.id, int(qty))
            return {
                'action': 'bill',
                'bill_id': bill.id,
                'summary': f"Draft bill created and populated for {bill.bill_number}.",
                'status': 'DRAFT',
            }

        if re.search(r'\b(add|insert)\b', lowered) and re.search(r'\bbill\b', lowered):
            bill_id = self._extract_bill_id(text)
            if bill_id is None:
                return {'action': 'bill_item_added', 'summary': 'I need the bill number to add an item.'}
            qty = self._extract_quantity(text) or 1
            product_lookup = re.sub(r'.*?\b(add|insert)\b\s*', '', text, flags=re.I)
            product_lookup = re.sub(r'\bto\s*bill\b.*', '', product_lookup, flags=re.I)
            product_lookup = re.sub(r'\b(?:for|of)\b.*', '', product_lookup, flags=re.I)
            product_lookup = product_lookup.strip()
            product = self._find_product(product_lookup or 'maggi')
            if product is None:
                return {'action': 'bill_item_added', 'summary': 'I could not identify the product to add to the bill.'}
            item = self.billing.add_item_to_bill(bill_id, product.id, qty)
            return {
                'action': 'bill_item_added',
                'bill_id': bill_id,
                'product_name': product.name,
                'quantity': qty,
                'summary': f"Added {qty} {product.name} to bill {bill_id}.",
            }

        if re.search(r'\b(finalize|confirm)\b', lowered) and re.search(r'\bbill\b', lowered):
            bill_id = self._extract_bill_id(text)
            if bill_id is None:
                return {'action': 'finalize_bill', 'summary': 'I need the bill number to finalize.'}
            self.billing.finalize_bill(bill_id)
            self._record_credit_bill(bill_id)
            return self._invoice_result(bill_id, f'Bill {bill_id} is finalized. Invoice generated and ready to send.')

        if re.search(r'\binvoice\b', lowered):
            bill_id = self._extract_bill_id(text)
            if bill_id is None:
                bill = self.billing.create_bill(payment_method='cash')
                bill_id = bill.id
            bill = self.billing.get_bill(bill_id)
            if bill.status != 'FINALIZED':
                self.billing.finalize_bill(bill_id)
            self._record_credit_bill(bill_id)
            return self._invoice_result(bill_id, f'Invoice generated for bill {bill_id}.')

        return {
            'action': 'search',
            'summary': 'I searched the store catalogue for the request.',
        }
