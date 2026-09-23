from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.telegram.handlers import TelegramHandler

router = APIRouter(prefix='/telegram', tags=['telegram'])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post('/message')
def handle_telegram_message(payload: dict, db: Session = Depends(get_db)):
    message = str(payload.get('message', '')).strip()
    handler = TelegramHandler(db)
    return handler.process(message)
