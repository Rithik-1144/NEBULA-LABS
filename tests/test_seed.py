from app.seed import seed_demo_data


def test_seed_data_populates_products():
    seed_demo_data()
    from app.database.database import SessionLocal
    from app.database.models import Product
    db = SessionLocal()
    try:
        count = db.query(Product).count()
        assert count >= 10
    finally:
        db.close()
