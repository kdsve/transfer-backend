# run.py
import os
import asyncio
import contextlib

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

import uvicorn
from uvicorn.config import Config
from uvicorn.server import Server

# импорт FastAPI-приложения (твой backend)
from app.main import app

# ==== настройки бота ====
BOT_TOKEN = os.environ["BOT_TOKEN"]  # токен твоего бота

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def on_start(m: Message):
    # Никаких WebApp-кнопок. Пользователь открывает мини-апп
    # через нижнюю меню-кнопку «Заявка на трансфер»
    # (настраивается в BotFather -> /setmenubutton -> Web App).
    await m.answer(
        "Здравствуйте! Чтобы оформить поездку, нажмите нижнюю кнопку "
        "«Заявка на трансфер»."
    )


# ==== запуск Uvicorn (FastAPI) в этом же процессе ====
async def run_uvicorn() -> None:
    port = int(os.environ.get("PORT", "10000"))  # Render прокидывает PORT
    config = Config(
        app=app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        # reload=False — обязателен на Render/проде
    )
    server = Server(config)
    await server.serve()


async def main() -> None:
    # Поднимаем сервер API и бота одновременно.
    api_task = asyncio.create_task(run_uvicorn(), name="uvicorn")
    bot_task = asyncio.create_task(dp.start_polling(bot), name="bot")

    # Ждём первую ошибку, вторую аккуратно гасим
    done, pending = await asyncio.wait(
        {api_task, bot_task},
        return_when=asyncio.FIRST_EXCEPTION,
    )
    for task in pending:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


if __name__ == "__main__":
    asyncio.run(main())
