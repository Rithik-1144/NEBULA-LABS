from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.agent import NebulaAgent
from app.database.database import SessionLocal
from app.database.models import Bill, BillItem, Customer, Product
from app.services.billing import BillingService
from app.services.inventory import InventoryService
from app.services.invoice import InvoiceService
from app.services.khata import KhataService

router = APIRouter(prefix='/api/dashboard', tags=['dashboard'])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def money(value: Decimal | None) -> float:
    return float(value or 0)


def product_payload(product: Product) -> dict[str, Any]:
    return {
        'id': product.id, 'sku': product.sku, 'name': product.name, 'brand': product.brand,
        'category': product.category, 'unit': product.unit, 'cost_price': money(product.cost_price),
        'selling_price': money(product.selling_price), 'mrp': money(product.mrp),
        'gst_rate': money(product.gst_rate), 'hsn_code': product.hsn_code,
        'current_stock': product.current_stock, 'reorder_level': product.reorder_level,
        'stock_state': 'critical' if product.current_stock <= max(1, product.reorder_level // 2) else 'low' if product.current_stock <= product.reorder_level else 'healthy',
    }


@router.get('/snapshot')
def snapshot(db: Session = Depends(get_db)):
    inventory = InventoryService(db)
    products = db.query(Product).order_by(Product.name).all()
    bills = db.query(Bill).order_by(Bill.id.desc()).limit(20).all()
    customers = db.query(Customer).order_by(Customer.name).all()
    khata = KhataService(db)
    return {
        'products': [product_payload(product) for product in products],
        'low_stock': [product_payload(product) for product in inventory.get_low_stock_products()],
        'bills': [{'id': bill.id, 'bill_number': bill.bill_number, 'status': bill.status, 'payment_method': bill.payment_method, 'grand_total': money(bill.grand_total), 'customer_id': bill.customer_id} for bill in bills],
        'customers': [{'id': customer.id, 'name': customer.name, 'phone': customer.phone, 'balance': money(khata.get_customer_balance(customer.id))} for customer in customers],
    }


@router.get('/telegram-status')
def telegram_status():
    from app.config.settings import get_settings
    configured = bool(get_settings().telegram_bot_token)
    return {
        'configured': configured,
        'running': configured,
        'message': 'Telegram polling is active.' if configured else 'Telegram bot token is not configured. Add TELEGRAM_BOT_TOKEN to .env and restart the app.',
    }


@router.get('/products')
def products(query: str = '', db: Session = Depends(get_db)):
    inventory = InventoryService(db)
    found = inventory.search_products(query) if query else db.query(Product).order_by(Product.name).all()
    return {'items': [product_payload(product) for product in found]}


@router.post('/inventory/receive')
def receive_stock(payload: dict[str, Any], db: Session = Depends(get_db)):
    try:
        product = InventoryService(db).receive_stock(payload['sku'], int(payload['quantity']), Decimal(str(payload.get('cost_price'))) if payload.get('cost_price') is not None else None, Decimal(str(payload.get('mrp'))) if payload.get('mrp') is not None else None)
        return product_payload(product)
    except (KeyError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post('/inventory/adjust')
def adjust_stock(payload: dict[str, Any], db: Session = Depends(get_db)):
    try:
        product = InventoryService(db).adjust_stock(payload['sku'], int(payload['quantity_delta']))
        return product_payload(product)
    except (KeyError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post('/bills')
def create_bill(payload: dict[str, Any] | None = None, db: Session = Depends(get_db)):
    payload = payload or {}
    bill = BillingService(db).create_bill(payload.get('customer_id'), payload.get('payment_method', 'cash'))
    return {'id': bill.id, 'bill_number': bill.bill_number, 'status': bill.status, 'payment_method': bill.payment_method}


@router.get('/bills/{bill_id}')
def get_bill(bill_id: int, db: Session = Depends(get_db)):
    billing = BillingService(db)
    bill = billing.get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail='Bill not found.')
    items = db.query(BillItem, Product).join(Product, Product.id == BillItem.product_id).filter(BillItem.bill_id == bill_id).all()
    totals = billing.calculate_bill(bill_id)
    return {
        'id': bill.id, 'bill_number': bill.bill_number, 'status': bill.status, 'payment_method': bill.payment_method,
        'customer_id': bill.customer_id, 'items': [{'id': item.id, 'product_id': product.id, 'product_name': product.name, 'quantity': item.quantity, 'unit_price': money(item.unit_price), 'total': money(item.total)} for item, product in items],
        'subtotal': money(totals['subtotal']), 'cgst': money(totals['cgst']), 'sgst': money(totals['sgst']), 'grand_total': money(totals['grand_total']),
    }


@router.post('/bills/{bill_id}/items')
def add_bill_item(bill_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
    try:
        item = BillingService(db).add_item_to_bill(bill_id, int(payload['product_id']), int(payload['quantity']))
        return {'id': item.id, 'bill_id': item.bill_id, 'quantity': item.quantity}
    except (KeyError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post('/bills/{bill_id}/finalize')
def finalize_bill(bill_id: int, db: Session = Depends(get_db)):
    try:
        bill = BillingService(db).finalize_bill(bill_id)
        invoice = InvoiceService(db)
        return {'id': bill.id, 'bill_number': bill.bill_number, 'status': bill.status, 'grand_total': money(bill.grand_total), 'invoice_url': f'/api/dashboard/bills/{bill_id}/invoice'}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get('/customers')
def customers(db: Session = Depends(get_db)):
    khata = KhataService(db)
    return {'items': [{'id': customer.id, 'name': customer.name, 'phone': customer.phone, 'balance': money(khata.get_customer_balance(customer.id))} for customer in db.query(Customer).order_by(Customer.name).all()]}


@router.post('/customers')
def create_customer(payload: dict[str, Any], db: Session = Depends(get_db)):
    try:
        customer = KhataService(db).create_customer(payload['name'], payload.get('phone'))
        return {'id': customer.id, 'name': customer.name, 'phone': customer.phone, 'balance': 0}
    except KeyError as error:
        raise HTTPException(status_code=400, detail='Customer name is required.') from error


@router.get('/chat/users')
def chat_users(db: Session = Depends(get_db)):
    agent = NebulaAgent(db)
    users = []
    for user_id in agent.list_users():
        sessions = agent.get_sessions_for_user(user_id)
        users.append({'user_id': user_id, 'session_count': len(sessions), 'last_session': sessions[0] if sessions else None})
    return {'users': users}


@router.get('/chat/sessions')
def chat_sessions(user_id: str = 'web-operator', db: Session = Depends(get_db)):
    agent = NebulaAgent(db)
    return {'sessions': agent.get_sessions_for_user(user_id), 'user_id': user_id}


@router.get('/chat/history')
def chat_history(user_id: str = 'web-operator', session_id: int | None = None, db: Session = Depends(get_db)):
    agent = NebulaAgent(db)
    session = agent._get_or_create_session(user_id, session_id)
    messages = agent.get_session_messages(user_id, session.id if session else None)
    return {'user_id': user_id, 'session_id': session.id if session else None, 'messages': messages, 'sessions': agent.get_sessions_for_user(user_id)}


@router.post('/chat/send')
def chat_send(payload: dict[str, Any], db: Session = Depends(get_db)):
    user_id = str(payload.get('user_id') or 'web-operator')
    message = str(payload.get('message', '')).strip()
    session_id = payload.get('session_id')
    if not message:
        raise HTTPException(status_code=400, detail='Message is required.')
    agent = NebulaAgent(db)
    response = agent.run(message, user_id=user_id, session_id=session_id)
    return {
        'response': response,
        'messages': agent.get_session_messages(user_id, response.get('conversation_id')),
        'sessions': agent.get_sessions_for_user(user_id),
    }


@router.get('/bills/{bill_id}/invoice')
def invoice(bill_id: int, db: Session = Depends(get_db)):
    from fastapi.responses import Response
    service = InvoiceService(db)
    try:
        return Response(service.render_pdf(bill_id), media_type='application/pdf', headers={'Content-Disposition': f'inline; filename="{service.filename(bill_id)}"'})
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
