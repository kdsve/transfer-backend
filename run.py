# run.py
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

import uvicorn
from uvicorn.config import Config
from uvicorn.server import Server

# импортируем уже существующее FastAPI-приложение
from app.main import app

# ==== настройки бота ====
BOT_TOKEN = os.environ["BOT_TOKEN"]  # токен твоего бота
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://ride-request-bot.lovable.app/")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def on_start(m: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(
            text="Открыть приложение",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )]],
        resize_keyboard=True
    )
    await m.answer(
        "Здравствуйте! Нажмите кнопку ниже, чтобы открыть мини-приложение и оформить заявку.",
        reply_markup=kb
    )

# ==== запуск Uvicorn внутри того же процесса ====
async def run_uvicorn() -> None:
    port = int(os.environ.get("PORT", "10000"))  # Render прокидывает PORT
    config = Config(
        app=app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        # reload=False — обязателен на проде/Render
    )
    server = Server(config)
    await server.serve()

async def main() -> None:
    # Поднимаем сервер API и бота одновременно.
    api_task = asyncio.create_task(run_uvicorn(), name="uvicorn")
    bot_task = asyncio.create_task(dp.start_polling(bot), name="bot")

    # Ждём первую ошибку из задач, вторую аккуратно гасим
    done, pending = await asyncio.wait(
        {api_task, bot_task},
        return_when=asyncio.FIRST_EXCEPTION,
    )
    for task in pending:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

if __name__ == "__main__":
    import contextlib
    asyncio.run(main())
