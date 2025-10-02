# bot.py
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
)

BOT_TOKEN = os.environ["BOT_TOKEN"]                 # токен вашего основного бота
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://ride-request-bot.lovable.app/")       # URL Lovable/вашего домена с мини-аппом

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def on_start(m: Message):
    # Кнопка, которая откроет ваш мини-апп
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True
    )
    await m.answer(
        "Здравствуйте! Нажмите кнопку ниже, чтобы открыть мини-приложение и оформить заявку.",
        reply_markup=kb
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
