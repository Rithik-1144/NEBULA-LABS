from decimal import Decimal

from sqlalchemy import select

from app.database.database import SessionLocal, init_db
from app.database.models import Product


def seed_demo_data() -> None:
    init_db()
    db = SessionLocal()
    try:
        existing = db.execute(select(Product.id).limit(1)).scalar_one_or_none()
        if existing is not None:
            return

        products = [
            Product(sku='AASH-5KG', name='Aashirvaad Atta', brand='Aashirvaad', category='Staples', description='Wheat flour 5kg', unit='kg', is_loose=False, cost_price=Decimal('140.00'), selling_price=Decimal('170.00'), mrp=Decimal('185.00'), gst_rate=Decimal('5'), hsn_code='1001', reorder_level=10, current_stock=35),
            Product(sku='TATA-SALT-1KG', name='Tata Salt', brand='Tata', category='Groceries', description='Iodized salt 1kg', unit='packet', is_loose=False, cost_price=Decimal('18.00'), selling_price=Decimal('22.00'), mrp=Decimal('24.00'), gst_rate=Decimal('5'), hsn_code='2501', reorder_level=20, current_stock=40),
            Product(sku='AMUL-BUTTER-100G', name='Amul Butter', brand='Amul', category='Dairy', description='Butter 100g', unit='packet', is_loose=False, cost_price=Decimal('44.00'), selling_price=Decimal('52.00'), mrp=Decimal('58.00'), gst_rate=Decimal('12'), hsn_code='0405', reorder_level=8, current_stock=18),
            Product(sku='FORTUNE-OIL-1L', name='Fortune Sunflower Oil', brand='Fortune', category='Cooking Oil', description='Refined oil 1L', unit='litre', is_loose=False, cost_price=Decimal('96.00'), selling_price=Decimal('110.00'), mrp=Decimal('120.00'), gst_rate=Decimal('5'), hsn_code='1512', reorder_level=8, current_stock=22),
            Product(sku='MAGGI-70G', name='Maggi', brand='Maggi', category='Snacks', description='Masala noodles 70g', unit='packet', is_loose=False, cost_price=Decimal('14.00'), selling_price=Decimal('18.00'), mrp=Decimal('20.00'), gst_rate=Decimal('5'), hsn_code='1902', reorder_level=15, current_stock=17),
            Product(sku='PARLE-G', name='Parle-G', brand='Parle', category='Biscuits', description='Cream biscuit', unit='packet', is_loose=False, cost_price=Decimal('10.00'), selling_price=Decimal('15.00'), mrp=Decimal('18.00'), gst_rate=Decimal('5'), hsn_code='1905', reorder_level=20, current_stock=30),
            Product(sku='SURF-EXCEL', name='Surf Excel', brand='Surf Excel', category='Household', description='Washing powder', unit='packet', is_loose=False, cost_price=Decimal('46.00'), selling_price=Decimal('62.00'), mrp=Decimal('69.00'), gst_rate=Decimal('18'), hsn_code='3402', reorder_level=10, current_stock=12),
            Product(sku='SUGAR-LOOSE', name='Loose Sugar', brand='Local', category='Staples', description='Loose sugar', unit='kg', is_loose=True, cost_price=Decimal('34.00'), selling_price=Decimal('40.00'), mrp=Decimal('45.00'), gst_rate=Decimal('5'), hsn_code='1701', reorder_level=10, current_stock=25),
            Product(sku='RICE-LOOSE', name='Loose Rice', brand='Local', category='Staples', description='Loose rice', unit='kg', is_loose=True, cost_price=Decimal('28.00'), selling_price=Decimal('35.00'), mrp=Decimal('38.00'), gst_rate=Decimal('5'), hsn_code='1006', reorder_level=12, current_stock=21),
            Product(sku='DAL-LOOSE', name='Loose Dal', brand='Local', category='Staples', description='Loose dal', unit='kg', is_loose=True, cost_price=Decimal('96.00'), selling_price=Decimal('110.00'), mrp=Decimal('120.00'), gst_rate=Decimal('5'), hsn_code='0713', reorder_level=9, current_stock=18),
        ]
        db.add_all(products)
        db.commit()
    finally:
        db.close()


if __name__ == '__main__':
    seed_demo_data()
