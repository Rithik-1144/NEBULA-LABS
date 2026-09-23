from decimal import Decimal

from app.database.database import SessionLocal
from app.seed import seed_demo_data
from app.telegram.bot import BotWorkflow


def test_telegram_workflow_stock_and_bill():
    seed_demo_data()
    db = SessionLocal()
    try:
        workflow = BotWorkflow(db)

        stock_result = workflow.handle_message('How much Maggi left?')
        assert stock_result['action'] == 'stock'
        assert 'Maggi' in stock_result['summary']

        bill_result = workflow.handle_message('Create a draft bill')
        assert bill_result['action'] == 'bill'
        assert bill_result['bill_id'] > 0
    finally:
        db.close()


def test_telegram_workflow_receipt_and_bill_edit_finalize():
    seed_demo_data()
    db = SessionLocal()
    try:
        workflow = BotWorkflow(db)

        receive_result = workflow.handle_message('Receive 20 packets of Maggi at cost 12 and mrp 18')
        assert receive_result['action'] == 'receive_stock'
        assert receive_result['quantity'] == 20

        bill_result = workflow.handle_message('Create a bill for 2 Maggi and 1 Amul Butter')
        assert bill_result['action'] == 'bill'
        assert 'bill_id' in bill_result

        add_item_result = workflow.handle_message(f'Add 2 Maggi to bill {bill_result["bill_id"]}')
        assert add_item_result['action'] == 'bill_item_added'
        assert add_item_result['quantity'] == 2

        finalize_result = workflow.handle_message(f'Finalize bill {bill_result["bill_id"]} and send invoice')
        assert finalize_result['action'] == 'finalize_bill'
        assert finalize_result['status'] == 'FINALIZED'
        assert 'invoice' in finalize_result['summary'].lower()
    finally:
        db.close()


def test_telegram_workflow_customer_khata_and_pdf_invoice():
    seed_demo_data()
    db = SessionLocal()
    try:
        workflow = BotWorkflow(db)

        customer_result = workflow.handle_message('Create customer Anita 9876543210')
        assert customer_result['action'] == 'customer_created'
        assert customer_result['customer_name'] == 'Anita'
        starting_balance = workflow.khata.get_customer_balance(customer_result['customer_id'])

        payment_result = workflow.handle_message('Anita paid Rs 250')
        assert payment_result['action'] == 'khata_payment'
        assert payment_result['balance'] == starting_balance - Decimal('250.00')

        balance_result = workflow.handle_message('Khata balance Anita')
        assert balance_result['action'] == 'khata_balance'
        assert balance_result['balance'] == starting_balance - Decimal('250.00')

        bill_result = workflow.handle_message('Create a bill for 1 Maggi')
        add_result = workflow.handle_message(f'Add 1 Maggi to bill {bill_result["bill_id"]}')
        assert add_result['action'] == 'bill_item_added'
        invoice_result = workflow.handle_message(f'Finalize bill {bill_result["bill_id"]}')
        assert invoice_result['invoice_filename'].endswith('.pdf')
        assert invoice_result['invoice_pdf'].startswith(b'%PDF')
        assert len(invoice_result['invoice_pdf']) > 1000
    finally:
        db.close()


def test_telegram_workflow_credit_bill_posts_to_khata_once():
    seed_demo_data()
    db = SessionLocal()
    try:
        workflow = BotWorkflow(db)
        customer_result = workflow.handle_message('Create customer Maya Test 9876543211')
        customer_id = customer_result['customer_id']
        bill_result = workflow.handle_message('Create credit bill for Maya Test')
        add_result = workflow.handle_message(f'Add 1 Maggi to bill {bill_result["bill_id"]}')
        assert add_result['action'] == 'bill_item_added'

        before = workflow.khata.get_customer_balance(customer_id)
        workflow.handle_message(f'Finalize bill {bill_result["bill_id"]}')
        after_first = workflow.khata.get_customer_balance(customer_id)
        workflow.handle_message(f'Finalize bill {bill_result["bill_id"]}')
        after_second = workflow.khata.get_customer_balance(customer_id)

        assert after_first > before
        assert after_second == after_first
    finally:
        db.close()
