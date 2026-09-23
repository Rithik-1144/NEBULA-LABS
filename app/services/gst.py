from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


TWO_PLACES = Decimal('0.01')


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def compute_gst_breakdown(taxable_amount: Decimal, gst_rate: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    gst_rate = Decimal(str(gst_rate))
    taxable_amount = Decimal(str(taxable_amount))
    total_gst = (taxable_amount * gst_rate / Decimal('100')).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    cgst = (total_gst / Decimal('2')).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    sgst = (total_gst - cgst).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    return cgst, sgst, total_gst


def calculate_item_total(unit_price: Decimal, quantity: int, gst_rate: Decimal) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal]:
    taxable_amount = (Decimal(str(unit_price)) * Decimal(quantity)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    cgst, sgst, total_gst = compute_gst_breakdown(taxable_amount, gst_rate)
    total = (taxable_amount + total_gst).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    return taxable_amount, cgst, sgst, total_gst, total
