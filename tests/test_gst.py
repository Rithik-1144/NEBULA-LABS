from decimal import Decimal

from app.services.gst import calculate_item_total, compute_gst_breakdown


def test_gst_breakdown_rounding():
    cgst, sgst, total_gst = compute_gst_breakdown(Decimal('100'), Decimal('18'))
    assert cgst == Decimal('9.00')
    assert sgst == Decimal('9.00')
    assert total_gst == Decimal('18.00')


def test_item_total_calculation():
    taxable, cgst, sgst, total_gst, total = calculate_item_total(Decimal('50'), 2, Decimal('12'))
    assert taxable == Decimal('100.00')
    assert cgst == Decimal('6.00')
    assert sgst == Decimal('6.00')
    assert total_gst == Decimal('12.00')
    assert total == Decimal('112.00')
