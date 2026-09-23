from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import select

from app.agent.llm import build_system_prompt, get_llm_provider
from app.agent.tool_registry import get_tool_catalog
from app.database.models import AgentSession, ConversationMessage
from app.telegram.bot import BotWorkflow


class NebulaAgent:
    """Conversational supermarket agent with session memory and richer intent handling."""

    def __init__(self, db_session: Any | None = None):
        self.db_session = db_session
        self.workflow = BotWorkflow(db_session) if db_session is not None else None

    def _get_or_create_session(self, user_id: str | int | None, session_id: int | None = None) -> AgentSession | None:
        if self.db_session is None or user_id is None:
            return None
        key = str(user_id)
        if session_id is not None:
            session = self.db_session.get(AgentSession, session_id)
            if session and session.telegram_user_id == key:
                return session
        sessions = self.db_session.execute(
            select(AgentSession)
            .where(AgentSession.telegram_user_id == key)
            .order_by(AgentSession.updated_at.desc())
        ).scalars().all()
        if sessions:
            return sessions[0]
        session = AgentSession(telegram_user_id=key, context='{}')
        self.db_session.add(session)
        self.db_session.commit()
        self.db_session.refresh(session)
        return session

    def create_session(self, user_id: str | int | None) -> AgentSession | None:
        if self.db_session is None or user_id is None:
            return None
        session = AgentSession(telegram_user_id=str(user_id), context='{}')
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

    def list_users(self) -> list[str]:
        if self.db_session is None:
            return []
        users = self.db_session.execute(
            select(AgentSession.telegram_user_id)
            .distinct()
            .order_by(AgentSession.telegram_user_id)
        ).scalars().all()
        return [str(user) for user in users]

    def get_sessions_for_user(self, user_id: str | int | None) -> list[dict[str, Any]]:
        if self.db_session is None or user_id is None:
            return []
        key = str(user_id)
        sessions = self.db_session.execute(
            select(AgentSession)
            .where(AgentSession.telegram_user_id == key)
            .order_by(AgentSession.updated_at.desc())
        ).scalars().all()
        result = []
        for session in sessions:
            messages = self.db_session.execute(
                select(ConversationMessage)
                .where(ConversationMessage.session_id == session.id)
                .order_by(ConversationMessage.created_at.desc())
                .limit(10)
            ).scalars().all()
            result.append({
                'id': session.id,
                'user_id': session.telegram_user_id,
                'updated_at': session.updated_at.isoformat() if session.updated_at else None,
                'message_count': len(messages),
                'last_message': messages[0].content if messages else '',
            })
        return result

    def get_session_messages(self, user_id: str | int | None, session_id: int | None = None, limit: int = 30) -> list[dict[str, Any]]:
        session = self._get_or_create_session(user_id, session_id)
        if session is None:
            return []
        rows = self.db_session.execute(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session.id)
            .order_by(ConversationMessage.created_at.asc())
            .limit(limit)
        ).scalars().all()
        return [
            {'role': row.role, 'content': row.content, 'created_at': row.created_at.isoformat() if row.created_at else None}
            for row in rows
        ]

    def get_recent_messages(self, user_id: str | int | None, limit: int = 10) -> list[str]:
        session = self._get_or_create_session(user_id)
        if session is None:
            return []
        rows = self.db_session.execute(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session.id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(limit)
        ).scalars().all()
        return [row.content for row in reversed(rows)]

    def _help_response(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            'action': 'help',
            'summary': 'Nebula can manage stock, billing, khata, invoices, and store guidance in one conversational flow.',
            'suggestions': self._build_suggestions('help'),
            'tools': get_tool_catalog(),
            'session_context': context,
        }

    def _should_use_direct_message(self, message: str) -> bool:
        lowered = message.lower()
        direct_patterns = [
            r'\bcreate customer\b',
            r'\bcreate.*bill\b',
            r'\bhow much .* left\b',
            r'\bwhat is .*balance\b',
            r'\bkhata balance\b',
            r'\bfinalize bill\b',
            r'\breceive .*\b',
            r'\badd .* to bill\b',
        ]
        return any(re.search(pattern, lowered) for pattern in direct_patterns)

    def _resolve_tool_command(self, tool_name: str | None, arguments: dict[str, Any] | None, original_message: str) -> str:
        args = arguments or {}
        if tool_name == 'search_products':
            query = str(args.get('query') or args.get('product') or original_message).strip()
            if 'how much' in query.lower() or 'stock' in query.lower() or 'left' in query.lower():
                return query
            return f"How much {query} left?"
        if tool_name == 'create_bill':
            return 'Create a draft bill'
        if tool_name == 'finalize_bill':
            bill_id = args.get('bill_id')
            return f'Finalize bill {bill_id}' if bill_id else 'Finalize the current bill and send invoice'
        if tool_name == 'report_customer_balance':
            customer_name = args.get('customer_name') or 'Anita'
            return f'Khata balance {customer_name}'
        if tool_name == 'receive_stock':
            sku = args.get('sku') or 'Maggi'
            qty = args.get('quantity') or 5
            return f'Receive {qty} packets of {sku} at cost 14'
        return original_message

    def run(self, user_text: str, user_id: str | int | None = None, session_id: int | None = None, **kwargs: Any) -> dict[str, Any]:
        if not user_text or not self._normalize_text(user_text):
            raise ValueError('User text is required.')

        session = self._get_or_create_session(user_id, session_id)
        context = self._read_session_context(session)
        normalized = self._normalize_text(user_text).lower()

        if re.search(r'\b(what can you do|help|capabilities|features)\b', normalized):
            response = self._help_response(context)
            self._save_turn(session, 'user', user_text)
            self._save_turn(session, 'assistant', json.dumps(response, default=str))
            return response

        if self.workflow is None:
            raise ValueError('NebulaAgent requires a database session to execute store workflows.')

        history = self.get_session_messages(user_id, session.id, limit=8) if session else []
        provider = get_llm_provider()
        system_prompt = build_system_prompt(context)
        tool_plan = provider.generate_with_tools(
            system_prompt=system_prompt,
            messages=[{'role': 'user', 'content': user_text}] + [{'role': 'assistant', 'content': item['content']} for item in history[-5:]],
            tools=get_tool_catalog(),
        )

        tool_name = tool_plan.get('tool') if isinstance(tool_plan, dict) else None
        if tool_name and not self._should_use_direct_message(user_text):
            command = self._resolve_tool_command(tool_name, tool_plan.get('arguments'), user_text)
            result = self.workflow.handle_message(command)
            assistant_text = tool_plan.get('message') or result.get('summary', '')
        else:
            result = self.workflow.handle_message(user_text)
            assistant_text = tool_plan.get('message') if isinstance(tool_plan, dict) else str(tool_plan)

        if not isinstance(result, dict):
            result = {'action': 'general', 'summary': str(result)}

        result.setdefault('conversation_id', session.id if session else None)
        result['suggestions'] = self._build_suggestions(result.get('action'))
        result['session_context'] = context
        result['assistant_reply'] = assistant_text
        result['provider'] = provider.provider_name
        result['tool_call'] = tool_name

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
            self._save_turn(session, 'assistant', assistant_text or result.get('summary', ''))

        return result
