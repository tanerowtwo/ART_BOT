import os
import asyncio
import random
import aiohttp
from aiohttp import web
import google.generativeai as genai
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# === ENV ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# Твой личный Telegram ID (число без минуса)
TARGET_USER_ID = int(os.environ.get("TARGET_USER_ID", 0))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Настройка Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# === СПИСОК ХУДОЖНИКОВ ===
ARTISTS = [
    "Михаил Врубель",
    "Франсиско Гойя",
    "Каспар Давид Фридрих",
    "Гюстав Доре",
    "Альбрехт Дюрер",
    "Караваджо",
    "Вильгельм Котарбинский",
    "Здзислав Бексиньский",
    "Рембрандт",
    "Ян Вермеер",
    "Эдвард Хоппер",
    "Уильям Тернер",
    "Илья Репин",
    "Клод Моне",
    "Диего Веласкес"
]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def fetch_artist_info(artist_name: str) -> str:
    prompt = f"""
    Сделай краткий, но емкий ресерч по художнику: {artist_name}. 
    Ты помогаешь видеооператору изучать живопись для вдохновения (работа со светом, композиция, цвет).
    
    Выдай ответ строго в чистом HTML формате без лишних Markdown символов вроде ```html:
    🎨 <b>Имя:</b> {artist_name}
    ⏳ <b>Годы жизни:</b> [годы]
    🏛 <b>Эпоха:</b> [эпоха]
    🖌 <b>Стиль:</b> [стиль]
    
    🖼 <b>Самые значимые картины:</b>
    - [Название]
    - [Название]
    
    🎬 <b>Операторский фокус:</b> [1-2 предложения: работа со светом, кьяроскуро, цветовой контраст или работа с планами]
    
    🔗 <b>Где почитать:</b>
    1. <a href="[ссылка]">[Название ресурса]</a>
    2. <a href="[ссылка]">[Название ресурса]</a>
    """
    try:
        response = await model.generate_content_async(prompt)
        text = response.text
        text = text.replace("```html", "").replace("```", "").strip()
        return text
    except Exception as e:
        return f"❌ Ошибка при поиске информации о {artist_name}:\n{e}"

async def send_daily_artist():
    if not TARGET_USER_ID:
        print("❌ Ошибка: TARGET_USER_ID не задан в переменной окружения!")
        return

    if not ARTISTS:
        await bot.send_message(TARGET_USER_ID, "Списки художников закончились!")
        return

    artist = random.choice(ARTISTS)
    print(f"🔍 Сбор данных по: {artist}...")
    info = await fetch_artist_info(artist)
    
    try:
        await bot.send_message(
            TARGET_USER_ID, 
            info, 
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        print("✅ Пост про художника успешно отправлен в личку!")
    except Exception as e:
        print(f"❌ Ошибка парсинга HTML, отправка простым текстом: {e}")
        await bot.send_message(TARGET_USER_ID, info, disable_web_page_preview=True)

# Реакция на команды /start и /test в личке
@dp.message(Command("start", "test"))
async def cmd_test(message: Message):
    await message.answer("🛠 Генерирую карточку художника...")
    await send_daily_artist()

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
    print("🤖 Бот запущен")
    
    await web_server()
    
    scheduler = AsyncIOScheduler(timezone="Asia/Yekaterinburg")
    scheduler.add_job(
        send_daily_artist, 
        trigger='cron', 
        hour=9, 
        minute=0, 
        misfire_grace_time=3600
    )
    scheduler.start()
    print("⏰ Расписание настроено на 09:00 (Екб)")

    await bot.delete_webhook(drop_pending_updates=True)

    # 🚀 ТЕСТОВЫЙ ЗАПУСК ПРИ СТАРТЕ СЕРВЕРА
    print("🧪 Выполняю тестовую отправку в личку...")
    asyncio.create_task(send_daily_artist())

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
