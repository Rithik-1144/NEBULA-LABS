from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import InventoryTransaction, Product


class InventoryService:
    def __init__(self, db: Session):
        self.db = db

    def get_product_by_id(self, product_id: int) -> Product | None:
        return self.db.get(Product, product_id)

    def get_product_by_sku(self, sku: str) -> Product | None:
        return self.db.execute(select(Product).where(Product.sku == sku)).scalar_one_or_none()

    def search_products(self, query: str) -> list[Product]:
        q = f'%{query.lower()}%'
        return self.db.execute(
            select(Product).where(Product.name.ilike(q) | Product.brand.ilike(q) | Product.sku.ilike(q))
        ).scalars().all()

    def receive_stock(self, sku: str, quantity: int, cost_price: Decimal | None = None, mrp: Decimal | None = None) -> Product:
        product = self.get_product_by_sku(sku)
        if not product:
            raise ValueError(f'Product with SKU {sku} not found.')
        previous = product.current_stock
        product.current_stock += int(quantity)
        if cost_price is not None:
            product.cost_price = cost_price
        if mrp is not None:
            product.mrp = mrp
        self.db.add(InventoryTransaction(
            product_id=product.id,
            transaction_type='RECEIVE',
            quantity=int(quantity),
            previous_stock=previous,
            new_stock=product.current_stock,
            reference_id=f'receive:{product.id}:{quantity}',
        ))
        self.db.commit()
        self.db.refresh(product)
        return product

    def check_stock(self, sku: str) -> Product:
        product = self.get_product_by_sku(sku)
        if not product:
            raise ValueError(f'Product with SKU {sku} not found.')
        return product

    def get_low_stock_products(self, threshold: int | None = None) -> list[Product]:
        products = self.db.execute(select(Product)).scalars().all()
        if threshold is None:
            threshold = 0
        return [p for p in products if p.current_stock <= max(p.reorder_level, threshold)]

    def adjust_stock(self, sku: str, quantity_delta: int) -> Product:
        product = self.get_product_by_sku(sku)
        if not product:
            raise ValueError(f'Product with SKU {sku} not found.')
        new_total = product.current_stock + int(quantity_delta)
        if new_total < 0:
            raise ValueError(f'Cannot reduce stock below zero for {product.name}.')
        previous = product.current_stock
        product.current_stock = new_total
        self.db.add(InventoryTransaction(
            product_id=product.id,
            transaction_type='ADJUSTMENT',
            quantity=int(quantity_delta),
            previous_stock=previous,
            new_stock=new_total,
            reference_id=f'adjust:{product.id}:{quantity_delta}'
        ))
        self.db.commit()
        self.db.refresh(product)
        return product
