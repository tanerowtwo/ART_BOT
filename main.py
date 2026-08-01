import os
import re
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATA_FILE = "cards.md"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def load_cards():
    """Загружает все карточки из файла cards.md."""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Разделяем по тегам <!-- START_CARD: DAY_\d+ -->
    cards = re.split(r'<!-- START_CARD: DAY_\d+ -->', content)
    cleaned_cards = []
    for card in cards:
        card_text = card.replace('<!-- END_CARD -->', '').strip()
        if card_text:
            cleaned_cards.append(card_text)
    return cleaned_cards

async def get_saved_index(chat_id: int) -> int:
    """Считывает сохраненный индекс из закрепленного сообщения."""
    try:
        chat = await bot.get_chat(chat_id)
        if chat.pinned_message and chat.pinned_message.text.startswith("INDEX:"):
            return int(chat.pinned_message.text.split(":")[1])
    except Exception:
        pass
    return 0

async def save_index(chat_id: int, index: int):
    """Обновляет закрепленное сообщение с новым индексом."""
    try:
        chat = await bot.get_chat(chat_id)
        text = f"INDEX:{index}"
        
        if chat.pinned_message and chat.pinned_message.text.startswith("INDEX:"):
            # Редактируем существующий закреп
            await bot.edit_message_text(text, chat_id=chat_id, message_id=chat.pinned_message.message_id)
        else:
            # Создаем новый закреп, если его не было
            msg = await bot.send_message(chat_id, text)
            await bot.pin_chat_message(chat_id, msg.message_id)
    except Exception as e:
        print(f"Ошибка сохранения прогресса: {e}")

@dp.message(CommandStart())
async def send_next_artist(message: Message):
    cards = load_cards()
    
    if not cards:
        await message.answer("❌ Ошибка: Файл cards.md не найден или пуст.")
        return

    index = await get_saved_index(message.chat.id)

    if index >= len(cards):
        await message.answer("🎉 Вы прошли весь список художников!")
        return

    card_text = cards[index]

    try:
        await message.answer(card_text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception:
        # Резервный вариант, если в тексте спецсимволы
        await message.answer(card_text, disable_web_page_preview=True)

    # Сохраняем следующий индекс в Telegram
    await save_index(message.chat.id, index + 1)

# === HTTP SERVER ДЛЯ UPTIMEROBOT ===
async def handle(request):
    return web.Response(text="OK", status=200)

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(
        runner, 
        "0.0.0.0", 
        int(os.environ.get("PORT", 8080))
    )
    await site.start()
    print("🌐 Внутренний веб-сервер запущен")

# === MAIN ===
async def main():
    print("🤖 Бот запущен...")
    await web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
