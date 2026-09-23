from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import select

from app.agent.tool_registry import get_tool_catalog
from app.database.models import AgentSession, ConversationMessage
from app.telegram.bot import BotWorkflow


class NebulaAgent:
    """Conversational supermarket agent with session memory and richer intent handling."""

    def __init__(self, db_session: Any | None = None):
        self.db_session = db_session
        self.workflow = BotWorkflow(db_session) if db_session is not None else None

    def _get_or_create_session(self, user_id: str | int | None) -> AgentSession | None:
        if self.db_session is None or user_id is None:
            return None
        key = str(user_id)
        session = self.db_session.execute(
            select(AgentSession)
            .where(AgentSession.telegram_user_id == key)
            .order_by(AgentSession.updated_at.desc())
        ).scalars().first()
        if session is None:
            session = AgentSession(telegram_user_id=key, context='{}')
            self.db_session.add(session)
            self.db_session.commit()
            self.db_session.refresh(session)
        return session

    def _read_session_context(self, session: AgentSession | None) -> dict[str, Any]:
        if session is None or not session.context:
            return {}
        try:
            value = json.loads(session.context)
            return value if isinstance(value, dict) else {}
        except (TypeError, ValueError):
            return {}

    def _write_session_context(self, session: AgentSession | None, payload: dict[str, Any]) -> None:
        if session is None:
            return
        session.context = json.dumps(payload, default=str)
        session.updated_at = __import__('datetime').datetime.utcnow()
        self.db_session.add(session)
        self.db_session.commit()

    def _save_turn(self, session: AgentSession | None, role: str, content: str) -> None:
        if session is None or not content:
            return
        self.db_session.add(
            ConversationMessage(
                session_id=session.id,
                role=role,
                content=content,
            )
        )
        self.db_session.commit()

    @staticmethod
    def _normalize_text(value: str) -> str:
        return ' '.join((value or '').strip().split())

    @staticmethod
    def _build_suggestions(action: str | None) -> list[str]:
        suggestions = {
            'stock': [
                'Check stock for Maggi',
                'How much Aashirvaad Atta is left?',
                'Show low-stock items',
            ],
            'bill': [
                'Create a draft bill',
                'Add 2 Maggi to the current bill',
                'Finalize the latest bill',
            ],
            'khata_balance': [
                'Show customer khata for Anita',
                'Record a payment from Maya',
                'Create a customer ledger',
            ],
            'customer_created': [
                'Add a payment entry',
                'Check customer balance',
                'Create a draft bill for this customer',
            ],
            'help': [
                'Check stock for Maggi',
                'Create a bill for 2 Maggi',
                'Show khata balance for Anita',
            ],
        }
        return suggestions.get(action or 'help', suggestions['help'])

    def _help_response(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            'action': 'help',
            'summary': 'Nebula can manage stock, billing, khata, invoices, and store guidance in one conversational flow.',
            'suggestions': self._build_suggestions('help'),
            'tools': get_tool_catalog(),
            'session_context': context,
        }

    def run(self, user_text: str, user_id: str | int | None = None, **kwargs: Any) -> dict[str, Any]:
        if not user_text or not self._normalize_text(user_text):
            raise ValueError('User text is required.')

        session = self._get_or_create_session(user_id)
        context = self._read_session_context(session)
        normalized = self._normalize_text(user_text).lower()

        if re.search(r'\b(what can you do|help|capabilities|features)\b', normalized):
            response = self._help_response(context)
            self._save_turn(session, 'user', user_text)
            self._save_turn(session, 'assistant', json.dumps(response, default=str))
            return response

        if self.workflow is None:
            raise ValueError('NebulaAgent requires a database session to execute store workflows.')

        result = self.workflow.handle_message(user_text)
        if not isinstance(result, dict):
            result = {'action': 'general', 'summary': str(result)}

        result.setdefault('conversation_id', session.id if session else None)
        result['suggestions'] = self._build_suggestions(result.get('action'))
        result['session_context'] = context

        if session is not None:
            if result.get('product_name'):
                context['last_product'] = result['product_name']
            if result.get('customer_name'):
                context['last_customer'] = result['customer_name']
            if result.get('bill_id') is not None:
                context['last_bill_id'] = result['bill_id']
            context['last_action'] = result.get('action', 'general')
            context['last_summary'] = result.get('summary', '')
            self._write_session_context(session, context)
            result['session_context'] = self._read_session_context(session)
            self._save_turn(session, 'user', user_text)
            self._save_turn(session, 'assistant', result.get('summary', ''))

        return result
