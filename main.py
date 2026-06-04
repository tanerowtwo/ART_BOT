import os
import asyncio
import random
import aiohttp
from aiohttp import web
import google.generativeai as genai
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# === ENV ===
BOT_TOKEN = os.environ["BOT_TOKEN"]
TARGET_USER_ID = int(os.environ["TARGET_USER_ID"])
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
RENDER_APP_URL = os.environ.get("RENDER_APP_URL", "https://your-app-name.onrender.com")

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
    
    Выдай ответ строго в таком формате (используй HTML-теги для красоты):
    🎨 <b>Имя:</b> {artist_name}
    ⏳ <b>Годы жизни:</b> [годы]
    🏛 <b>Эпоха:</b> [эпоха]
    🖌 <b>Стиль:</b> [стиль]
    
    🖼 <b>Самые значимые картины (3-5 шт):</b>
    - [Название]
    - [Название]
    
    🔗 <b>Где почитать (3 качественные ссылки на статьи, Википедию или арт-блоги):</b>
    1. <a href="[ссылка]">[Название ресурса]</a>
    2. <a href="[ссылка]">[Название ресурса]</a>
    3. <a href="[ссылка]">[Название ресурса]</a>
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Ошибка при поиске информации о {artist_name}:\n{e}"

async def send_daily_artist():
    if not ARTISTS:
        await bot.send_message(TARGET_USER_ID, "Списки художников закончились!")
        return

    artist = random.choice(ARTISTS)
    ARTISTS.remove(artist) 
    
    print(f"🔍 Сбор данных по: {artist}...")
    info = await fetch_artist_info(artist)
    
    await bot.send_message(
        TARGET_USER_ID, 
        info, 
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    print("✅ Пост про художника отправлен!")

# === HTTP SERVER ДЛЯ RENDER ===
async def handle(request):
    return web.Response(text="Бот-искусствовед активен!")

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

# === KEEP ALIVE (Пинг внешнего URL, чтобы не спать) ===
async def keep_alive():
    await asyncio.sleep(30)  # Даем время на запуск
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(RENDER_APP_URL, timeout=10) as response:
                    print(f"🔄 Ping OK. Статус: {response.status}")
        except Exception as e:
            print(f"❌ Ping fail: {e}")
        await asyncio.sleep(120)  # Пингуем каждые 2 минуты

# === MAIN ===
async def main():
    print("🤖 Бот запущен")
    
    # Запускаем веб-сервер, чтобы Render не ругался на отсутствие порта
    await web_server()
    
    # Запускаем планировщик
    scheduler = AsyncIOScheduler(timezone="Asia/Yekaterinburg")
    scheduler.add_job(send_daily_artist, trigger='cron', hour=9, minute=0)
    scheduler.start()
    print("⏰ Расписание настроено на 09:00 (Екб)")

    # Фоновое удержание от сна
    asyncio.create_task(keep_alive())

    # Запуск поллинга aiogram
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
