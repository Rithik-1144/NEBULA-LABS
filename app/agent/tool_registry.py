from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(slots=True)
class ToolDefinition:
    name: str
    description: str
    arguments: dict[str, str] = field(default_factory=dict)
    handler: Callable[..., Any] | None = None


TOOLS: dict[str, ToolDefinition] = {}


def register_tool(name: str, description: str, arguments: dict[str, str] | None = None):
    def decorator(func: Callable[..., Any]):
        TOOLS[name] = ToolDefinition(
            name=name,
            description=description,
            arguments=arguments or {},
            handler=func,
        )
        return func
    return decorator


def get_tool_catalog() -> list[dict[str, Any]]:
    return [
        {
            'name': tool.name,
            'description': tool.description,
            'arguments': tool.arguments,
        }
        for tool in TOOLS.values()
    ]
