from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agent.agent import NebulaAgent


class TelegramHandler:
    def __init__(self, db: Session):
        self.agent = NebulaAgent(db)

    def process(self, message: str, user_id: str | int | None = None) -> dict[str, Any]:
        return self.agent.run(message, user_id=user_id)
