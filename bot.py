# bot.py
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

BOT_TOKEN = os.environ["BOT_TOKEN"]

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def on_start(m: Message):
    # Никаких кнопок. Пользователь жмёт нижнюю меню-кнопку
    # «Заявка на трансфер», которую ты настроил через BotFather (/setmenubutton → Web App).
    await m.answer(
        "Здравствуйте! Чтобы оформить поездку, нажмите нижнюю кнопку "
        "«Заявка на трансфер»."
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
