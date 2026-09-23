from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    success: bool
    message: str
    data: dict[str, Any] | None = None


class ProductSearchResult(BaseModel):
    sku: str
    name: str
    brand: str
    unit: str
    current_stock: int
    selling_price: Decimal


class BillDraftSummary(BaseModel):
    bill_id: int
    subtotal: Decimal
    cgst: Decimal
    sgst: Decimal
    total_gst: Decimal
    grand_total: Decimal
    payment_method: str
    status: Literal['DRAFT', 'FINALIZED', 'CANCELLED']
