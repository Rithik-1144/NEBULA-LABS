from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, Integer, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class Store(Base):
    __tablename__ = 'stores'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    gstin: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Product(Base):
    __tablename__ = 'products'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand: Mapped[str] = mapped_column(String(200), default='Generic')
    category: Mapped[str] = mapped_column(String(100), default='General')
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit: Mapped[str] = mapped_column(String(50), default='piece')
    is_loose: Mapped[bool] = mapped_column(Boolean, default=False)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal('0'))
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal('0'))
    mrp: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal('0'))
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal('0'))
    hsn_code: Mapped[str] = mapped_column(String(30), default='0000')
    reorder_level: Mapped[int] = mapped_column(Integer, default=0)
    current_stock: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InventoryTransaction(Base):
    __tablename__ = 'inventory_transactions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))
    transaction_type: Mapped[str] = mapped_column(String(50))
    quantity: Mapped[int] = mapped_column(Integer)
    previous_stock: Mapped[int] = mapped_column(Integer)
    new_stock: Mapped[int] = mapped_column(Integer)
    reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Customer(Base):
    __tablename__ = 'customers'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KhataTransaction(Base):
    __tablename__ = 'khata_transactions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey('customers.id'))
    type: Mapped[str] = mapped_column(String(20))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal('0'))
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Bill(Base):
    __tablename__ = 'bills'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bill_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey('customers.id'), nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal('0'))
    cgst: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal('0'))
    sgst: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal('0'))
    total_gst: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal('0'))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal('0'))
    payment_method: Mapped[str] = mapped_column(String(30), default='cash')
    payment_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='DRAFT')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class BillItem(Base):
    __tablename__ = 'bill_items'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey('bills.id'))
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal('0'))
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal('0'))
    hsn_code: Mapped[str] = mapped_column(String(30), default='0000')
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal('0'))
    cgst: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal('0'))
    sgst: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal('0'))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal('0'))


class AgentSession(Base):
    __tablename__ = 'agent_sessions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_user_id: Mapped[str] = mapped_column(String(50), index=True)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConversationMessage(Base):
    __tablename__ = 'conversation_messages'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey('agent_sessions.id'))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserPreference(Base):
    __tablename__ = 'user_preferences'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_user_id: Mapped[str] = mapped_column(String(50), index=True, unique=True)
    default_payment_method: Mapped[str] = mapped_column(String(30), default='cash')
    preferred_brand: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    invoice_preferences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IdempotencyRecord(Base):
    __tablename__ = 'idempotency_records'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    operation: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
