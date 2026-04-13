---
name: telegram-bot
description: Develop Telegram Bots using aiogram 3.x patterns
---

# Telegram Bot Skill

## Overview
Best practices for building Telegram bots with aiogram 3.x.

## Project Structure
```
bot/
├── main.py           # Bootstrap
├── config.py         # Settings (Pydantic)
├── routers/          # Handlers by feature
├── states/           # FSM states
├── services/         # Business logic
└── db/               # Models, repositories
```

## Handler Pattern
```python
from aiogram import Router, F
from aiogram.types import Message

router = Router()

@router.message(F.text == "/start")
async def start_handler(message: Message):
    await message.answer("Привет! 👋")
```

## FSM (Finite State Machine)
```python
from aiogram.fsm.state import State, StatesGroup

class OrderStates(StatesGroup):
    waiting_for_product = State()
    waiting_for_address = State()
    waiting_for_payment = State()
```

## Middleware Pattern
```python
from aiogram import BaseMiddleware

class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        # Pre-processing
        user = await get_user(event.from_user.id)
        data["user"] = user
        return await handler(event, data)
```

## Keyboard Helpers
```python
from aiogram.utils.keyboard import InlineKeyboardBuilder

def product_keyboard(products: list):
    builder = InlineKeyboardBuilder()
    for p in products:
        builder.button(text=p.name, callback_data=f"product:{p.id}")
    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup()
```

## Resources
- [aiogram 3.x Docs](https://docs.aiogram.dev/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
