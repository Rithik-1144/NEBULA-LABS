from app.agent.agent import NebulaAgent
from app.database.database import SessionLocal
from app.seed import seed_demo_data


def test_agent_tracks_conversation_and_lists_capabilities():
    seed_demo_data()
    db = SessionLocal()
    try:
        agent = NebulaAgent(db)

        stock_response = agent.run('How much Maggi left?', user_id='telegram-user-1')
        assert stock_response['action'] == 'stock'
        assert 'Maggi' in stock_response['summary']
        assert stock_response['conversation_id'] is not None
        assert 'suggestions' in stock_response

        capabilities = agent.run('What can you do?', user_id='telegram-user-1')
        assert capabilities['action'] == 'help'
        assert isinstance(capabilities['suggestions'], list)
        assert len(capabilities['suggestions']) >= 3
    finally:
        db.close()


def test_agent_remembers_recent_context():
    seed_demo_data()
    db = SessionLocal()
    try:
        agent = NebulaAgent(db)

        first = agent.run('Create customer Anita 9876543210', user_id='telegram-user-2')
        second = agent.run('What is Anita’s balance?', user_id='telegram-user-2')

        assert first['action'] == 'customer_created'
        assert second['action'] == 'khata_balance'
        assert second['session_context']
    finally:
        db.close()
