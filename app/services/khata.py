from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import Customer, KhataTransaction


class KhataService:
    def __init__(self, db: Session):
        self.db = db

    def find_customer(self, customer_name: str | None = None, phone: str | None = None) -> Customer | None:
        if customer_name:
            return self.db.execute(select(Customer).where(Customer.name.ilike(customer_name))).scalars().first()
        if phone:
            return self.db.execute(select(Customer).where(Customer.phone == phone)).scalar_one_or_none()
        return None

    def create_customer(self, name: str, phone: str | None = None) -> Customer:
        existing = self.find_customer(name, phone)
        if existing:
            return existing
        customer = Customer(name=name, phone=phone)
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def add_credit(self, customer_id: int, amount: Decimal, description: str = 'Credit', reference: str | None = None) -> KhataTransaction:
        customer = self.db.get(Customer, customer_id)
        if not customer:
            raise ValueError('Customer not found.')
        if amount <= 0:
            raise ValueError('Credit amount must be positive.')
        if reference:
            existing = self.db.execute(
                select(KhataTransaction).where(KhataTransaction.reference == reference)
            ).scalars().first()
            if existing:
                return existing
        txn = KhataTransaction(
            customer_id=customer_id,
            type='CREDIT',
            amount=amount,
            reference=reference,
            description=description,
        )
        self.db.add(txn)
        self.db.commit()
        self.db.refresh(txn)
        return txn

    def record_credit_payment(self, customer_id: int, amount: Decimal, description: str = 'Payment') -> KhataTransaction:
        customer = self.db.get(Customer, customer_id)
        if not customer:
            raise ValueError('Customer not found.')
        if amount <= 0:
            raise ValueError('Payment must be positive.')
        txn = KhataTransaction(customer_id=customer_id, type='PAYMENT', amount=amount, description=description)
        self.db.add(txn)
        self.db.commit()
        self.db.refresh(txn)
        return txn

    def get_statement(self, customer_id: int) -> list[KhataTransaction]:
        customer = self.db.get(Customer, customer_id)
        if not customer:
            raise ValueError('Customer not found.')
        return self.db.execute(
            select(KhataTransaction)
            .where(KhataTransaction.customer_id == customer_id)
            .order_by(KhataTransaction.created_at, KhataTransaction.id)
        ).scalars().all()

    def get_customer_balance(self, customer_id: int) -> Decimal:
        customer = self.db.get(Customer, customer_id)
        if not customer:
            raise ValueError('Customer not found.')
        credit = self.db.execute(select(func.coalesce(func.sum(KhataTransaction.amount), 0)).where(KhataTransaction.customer_id == customer_id, KhataTransaction.type == 'CREDIT')).scalar() or Decimal('0')
        payment = self.db.execute(select(func.coalesce(func.sum(KhataTransaction.amount), 0)).where(KhataTransaction.customer_id == customer_id, KhataTransaction.type == 'PAYMENT')).scalar() or Decimal('0')
        return Decimal(str(credit)) - Decimal(str(payment))
