from app.agent.agent import NebulaAgent
from app.agent.llm import get_llm_provider
from app.database.database import SessionLocal
from app.seed import seed_demo_data


def test_llm_provider_falls_back_to_mock_when_unconfigured():
    provider = get_llm_provider()
    reply = provider.generate(
        system_prompt='You are a store assistant.',
        messages=[{'role': 'user', 'content': 'How much Maggi is left?'}],
    )
    assert 'Maggi' in reply or 'stock' in reply.lower()


def test_agent_persists_memory_per_user():
    seed_demo_data()
    db = SessionLocal()
    try:
        agent = NebulaAgent(db)

        first = agent.run('Create customer Priya 9999999999', user_id='assistant-user-42')
        second = agent.run('What is Priya balance?', user_id='assistant-user-42')

        assert first['action'] == 'customer_created'
        assert second['action'] == 'khata_balance'
        assert len(agent.get_recent_messages('assistant-user-42')) >= 2
    finally:
        db.close()
