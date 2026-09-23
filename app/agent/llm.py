from __future__ import annotations

import json
from typing import Any

import httpx

from app.config.settings import get_settings


class BaseLLMProvider:
    provider_name = 'mock'

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or ''
        self.model = model or 'mock-router'

    def generate(self, system_prompt: str, messages: list[dict[str, str]], **kwargs: Any) -> str:
        if not messages:
            return 'I am ready to help with stock, billing, and customer khata.'
        last_message = messages[-1].get('content', '').strip()
        lowered = last_message.lower()
        if 'maggi' in lowered or 'stock' in lowered or 'left' in lowered:
            return 'I can check Maggi stock and tell you how much is left in the store inventory.'
        if 'bill' in lowered:
            return 'I can create a draft bill, add items, and finalize it with invoice generation.'
        if 'khata' in lowered or 'customer' in lowered:
            return 'I can help with customer ledgers, credit entries, and payment tracking.'
        return 'I can help with inventory, billing, khata, and invoice operations for the store.'

    def generate_with_tools(self, system_prompt: str, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None, **kwargs: Any) -> dict[str, Any]:
        last_message = messages[-1].get('content', '').strip() if messages else ''
        lower = last_message.lower()
        if 'maggi' in lower or 'stock' in lower or 'left' in lower:
            return {
                'tool': 'search_products',
                'arguments': {'query': 'Maggi' if 'maggi' in lower else 'stock'},
                'message': 'I checked the relevant supermarket products and stock details.',
            }
        if 'bill' in lower and 'final' in lower:
            return {
                'tool': 'finalize_bill',
                'arguments': {'query': last_message},
                'message': 'I can finalize the open bill and generate the invoice.',
            }
        if 'bill' in lower:
            return {
                'tool': 'create_bill',
                'arguments': {'payment_method': 'cash'},
                'message': 'I started a draft bill for the request.',
            }
        if 'khata' in lower or 'customer' in lower:
            return {
                'tool': 'report_customer_balance',
                'arguments': {'customer_name': 'Anita'},
                'message': 'I looked up the customer ledger context.',
            }
        return {
            'tool': 'search_products',
            'arguments': {'query': last_message or 'store'},
            'message': 'I searched the store catalogue for the requested products.',
        }


class OpenAIProvider(BaseLLMProvider):
    provider_name = 'openai'

    def __init__(self, api_key: str | None = None, model: str | None = None):
        super().__init__(api_key, model)
        self.url = 'https://api.openai.com/v1/chat/completions'

    def generate(self, system_prompt: str, messages: list[dict[str, str]], **kwargs: Any) -> str:
        if not self.api_key:
            return BaseLLMProvider.generate(self, system_prompt, messages)

        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                *messages,
            ],
            'temperature': float(kwargs.get('temperature', 0.2)),
            'max_tokens': int(kwargs.get('max_tokens', 350)),
        }
        response = httpx.post(
            self.url,
            headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content'].strip()

    def generate_with_tools(self, system_prompt: str, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None, **kwargs: Any) -> dict[str, Any]:
        if not self.api_key:
            return super().generate_with_tools(system_prompt, messages, tools, **kwargs)

        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                *messages,
            ],
            'tools': [{'type': 'function', 'function': {'name': tool['name'], 'description': tool.get('description', ''), 'parameters': {'type': 'object', 'properties': tool.get('arguments', {}), 'required': []}}} for tool in (tools or [])],
            'tool_choice': 'auto',
            'temperature': float(kwargs.get('temperature', 0.2)),
            'max_tokens': int(kwargs.get('max_tokens', 350)),
        }
        response = httpx.post(
            self.url,
            headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        message = data['choices'][0]['message']
        if message.get('tool_calls'):
            call = message['tool_calls'][0]['function']
            return {
                'tool': call['name'],
                'arguments': json.loads(call.get('arguments', '{}')),
                'message': 'I used the relevant store tool to answer your request.',
            }
        return {'tool': None, 'arguments': {}, 'message': message.get('content', '').strip()}


class GeminiProvider(BaseLLMProvider):
    provider_name = 'gemini'

    def __init__(self, api_key: str | None = None, model: str | None = None):
        super().__init__(api_key, model)
        self.url = f'https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent'

    def generate(self, system_prompt: str, messages: list[dict[str, str]], **kwargs: Any) -> str:
        if not self.api_key:
            return BaseLLMProvider.generate(self, system_prompt, messages)

        prompt = '\n'.join(
            [f"{entry.get('role', 'user').capitalize()}: {entry.get('content', '')}" for entry in messages]
        )
        payload = {
            'contents': [{'parts': [{'text': f'{system_prompt}\n\n{prompt}'}]}],
            'generationConfig': {
                'temperature': float(kwargs.get('temperature', 0.2)),
                'maxOutputTokens': int(kwargs.get('max_tokens', 350)),
            },
        }
        response = httpx.post(
            f'{self.url}?key={self.api_key}',
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text'].strip()

    def generate_with_tools(self, system_prompt: str, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None, **kwargs: Any) -> dict[str, Any]:
        if not self.api_key:
            return super().generate_with_tools(system_prompt, messages, tools, **kwargs)

        prompt = '\n'.join(
            [f"{entry.get('role', 'user').capitalize()}: {entry.get('content', '')}" for entry in messages]
        )
        payload = {
            'contents': [{'parts': [{'text': f'{system_prompt}\n\n{prompt}'}]}],
            'tools': [{'functionDeclarations': [{
                'name': tool['name'],
                'description': tool.get('description', ''),
                'parameters': {
                    'type': 'OBJECT',
                    'properties': {k: {'type': 'STRING'} for k in (tool.get('arguments', {}) or {})},
                    'required': [],
                },
            } for tool in (tools or [])]}],
            'generationConfig': {
                'temperature': float(kwargs.get('temperature', 0.2)),
                'maxOutputTokens': int(kwargs.get('max_tokens', 350)),
            },
        }
        response = httpx.post(
            f'{self.url}?key={self.api_key}',
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        candidate = data['candidates'][0]
        part = candidate['content']['parts'][0]
        if 'functionCall' in part:
            function = part['functionCall']
            return {'tool': function['name'], 'arguments': dict(function.get('args', {})), 'message': 'I used the relevant store tool to answer your request.'}
        return {'tool': None, 'arguments': {}, 'message': part.get('text', '').strip()}


def get_llm_provider() -> BaseLLMProvider:
    settings = get_settings()
    provider_name = (settings.llm_provider or 'mock').lower()
    if provider_name == 'openai':
        return OpenAIProvider(settings.openai_api_key or settings.llm_api_key, settings.openai_model or settings.llm_model)
    if provider_name == 'gemini':
        return GeminiProvider(settings.gemini_api_key or settings.llm_api_key, settings.gemini_model or settings.llm_model)
    return BaseLLMProvider()


def build_system_prompt(context: dict[str, Any] | None = None) -> str:
    context = context or {}
    last_action = context.get('last_action', 'general')
    last_product = context.get('last_product', 'the product in focus')
    last_customer = context.get('last_customer', 'the relevant customer')
    return (
        'You are Nebula, a practical supermarket operations assistant. '
        'Focus on store operations, inventory, billing, and customer khata. '
        f'Keep the current context in mind: last action={last_action}, last product={last_product}, last customer={last_customer}. '
        'Answer clearly, keep suggestions actionable, and prefer concise business summaries.'
    )
