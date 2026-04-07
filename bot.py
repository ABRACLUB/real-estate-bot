"""
Telegram-бот для фильтрации недвижимости из канала @zats_denis
Запуск: python bot.py
Требования: pip install python-telegram-bot requests
"""

import logging
import json
import os
import re
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler
)

# ─────────────────────────────────────────────
# НАСТРОЙКИ
# ─────────────────────────────────────────────
BOT_TOKEN = os.environ.get("8691313667:AAFtI9CUFia_Ew2_3vXLJ7Zivgy1C7Yzx0s")
CHANNEL   = "zats_denis"
DB_FILE   = "properties.json"
# Вставь свой ключ Anthropic для авто-парсинга новых постов
# Получить: https://console.anthropic.com/
ANTHROPIC_API_KEY = ""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# БАЗА ОБЪЕКТОВ — стартовые данные
# ─────────────────────────────────────────────
DEFAULT_PROPERTIES = [
    {
        "id": 1041,
        "title": "Готовые апартаменты в центре города",
        "city": "Лимассол", "district": "Мессагитония",
        "type": "апартаменты", "bedrooms": [1, 2, 3],
        "price_from": 317000, "price_to": 700000,
        "ready": "Q2/2026",
        "link": "https://t.me/zats_denis/1041",
        "desc": "Первая линия, панорамный вид на море. 1 сп от €317k, 2 сп от €436k, 3 сп от €513k"
    },
    {
        "id": 1054,
        "title": "Пресейл комплекса рядом с пляжем Ледис Майл",
        "city": "Лимассол", "district": "Закаки",
        "type": "апартаменты", "bedrooms": [0, 1, 2],
        "price_from": 185000, "price_to": 450000,
        "ready": "Q3/2028",
        "link": "https://t.me/zats_denis/1054",
        "desc": "Студия от €185k, 1 сп от €230k, 2 сп от €340k. Беспроцентная рассрочка"
    },
    {
        "id": 1060,
        "title": "Старт продаж в комплексе на холмах",
        "city": "Лимассол", "district": "Гермасоя",
        "type": "апартаменты", "bedrooms": [1, 2, 3],
        "price_from": 232000, "price_to": 600000,
        "ready": "Q3/2028",
        "link": "https://t.me/zats_denis/1060",
        "desc": "Вид на море и горы. 1 сп от €232k, 2 сп от €378k, 3 сп от €486k. Рассрочка"
    },
    {
        "id": 1005,
        "title": "Последние виллы в приватном комплексе",
        "city": "Лимассол", "district": "Гермасоя",
        "type": "вилла", "bedrooms": [4, 5],
        "price_from": 1400000, "price_to": 3000000,
        "ready": "Готово",
        "link": "https://t.me/zats_denis/1005",
        "desc": "Приватный комплекс 6 вилл, холмы, вид на море. 10 мин до центра"
    },
]


# ─────────────────────────────────────────────
# ХРАНИЛИЩЕ
# ─────────────────────────────────────────────

def load_properties():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    save_properties(DEFAULT_PROPERTIES)
    return list(DEFAULT_PROPERTIES)

def save_properties(props):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

PROPERTIES = load_properties()


# ─────────────────────────────────────────────
# АВТО-ПАРСИНГ ЧЕРЕЗ CLAUDE AI
# ─────────────────────────────────────────────

def fetch_channel_html():
    try:
        r = requests.get(f"https://t.me/s/{CHANNEL}", timeout=10)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logger.warning(f"Не удалось получить посты канала: {e}")
        return None

def extract_post_ids(html: str) -> list:
    ids = re.findall(r't\.me/' + CHANNEL + r'/(\d+)', html)
    return sorted(set(int(i) for i in ids), reverse=True)

def parse_post_with_claude(post_text: str, post_id: int):
    if not ANTHROPIC_API_KEY:
        return None
    prompt = f"""Перед тобой пост из Telegram-канала о недвижимости на Кипре.
Извлеки данные и верни ТОЛЬКО валидный JSON без лишнего текста.

Поля:
- title: краткое название
- city: город на русском
- district: район на русском
- type: апартаменты / вилла / таунхаус / дом
- bedrooms: массив чисел [0=студия, 1, 2, 3, 4, 5]
- price_from: мин цена числом в евро
- price_to: макс цена числом (если нет — price_from * 1.5)
- ready: "Q3/2028" или "Готово"
- desc: 1-2 предложения

Если пост НЕ объявление о продаже — верни: {{"skip": true}}

Пост:
{post_text}"""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )
        raw = resp.json()["content"][0]["text"]
        raw = re.sub(r"```json|```", "", raw).strip()
        data = json.loads(raw)
        if data.get("skip"):
            return None
        data["id"]   = post_id
        data["link"] = f"https://t.me/{CHANNEL}/{post_id}"
        return data
    except Exception as e:
        logger.warning(f"Ошибка парсинга поста {post_id}: {e}")
        return None

def sync_new_posts():
    global PROPERTIES
    html = fetch_channel_html()
    if not html:
        return 0
    known_ids = {p["id"] for p in PROPERTIES}
    new_ids = [i for i in extract_post_ids(html) if i not in known_ids]
    if not new_ids:
        return 0

    added = 0
    for post_id in new_ids[:20]:
        try:
            r = requests.get(f"https://t.me/{CHANNEL}/{post_id}?embed=1", timeout=10)
            m = re.search(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
                          r.text, re.DOTALL)
            if not m:
                continue
            text = re.sub(r'<[^>]+>', ' ', m.group(1)).strip()
            if len(text) < 50:
                continue
            prop = parse_post_with_claude(text, post_id)
            if prop:
                PROPERTIES.append(prop)
                added += 1
        except Exception as e:
            logger.warning(f"Ошибка при обработке поста {post_id}: {e}")

    if added:
        save_properties(PROPERTIES)
    return added


# ─────────────────────────────────────────────
# ФИЛЬТРАЦИЯ
# ─────────────────────────────────────────────

def fmt(p):
    return f"€{p:,}".replace(",", " ")

def match(prop, f):
    if f.get("type") and f["type"] != "любой" and prop.get("type") != f["type"]:
        return False
    if f.get("city") and f["city"] != "любой" and prop.get("city") != f["city"]:
        return False
    if f.get("district") and f["district"] != "любой" and prop.get("district") != f["district"]:
        return False
    beds = f.get("bedrooms")
    if beds is not None and beds != -1 and beds not in prop.get("bedrooms", []):
        return False
    if f.get("price_max") and prop.get("price_from", 0) > f["price_max"]:
        return False
    if f.get("price_min") and prop.get("price_to", 9999999) < f["price_min"]:
        return False
    return True

def uniq(key):
    return sorted(set(p[key] for p in PROPERTIES if p.get(key)))


# ─────────────────────────────────────────────
# СОСТОЯНИЯ
# ─────────────────────────────────────────────
S_TYPE, S_CITY, S_DISTRICT, S_BEDROOMS, S_PRICE = range(5)


# ─────────────────────────────────────────────
# ХЭНДЛЕРЫ
# ─────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    kb = [
        [InlineKeyboardButton("🔍 Подобрать объект", callback_data="search")],
        [InlineKeyboardButton("📋 Все объекты",       callback_data="all")],
        [InlineKeyboardButton("🔄 Обновить из канала", callback_data="sync")],
    ]
    await update.message.reply_text(
        f"👋 Привет! Недвижимость на Кипре из @zats_denis\n\nВ базе: *{len(PROPERTIES)} объектов*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return ConversationHandler.END


async def show_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await send_results(q, PROPERTIES)


async def do_sync(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("⏳ Проверяю канал на новые объекты...")
    if not ANTHROPIC_API_KEY:
        await q.edit_message_text(
            "⚠️ Для авто-парсинга нужен ключ Anthropic API.\n"
            "Вставь его в ANTHROPIC_API_KEY в bot.py\n"
            "Получить: https://console.anthropic.com/",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Назад", callback_data="back")
            ]])
        )
        return
    added = sync_new_posts()
    await q.edit_message_text(
        f"✅ Добавлено: *{added}* новых объектов\nВсего в базе: *{len(PROPERTIES)}*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔍 Искать", callback_data="search"),
            InlineKeyboardButton("📋 Все",    callback_data="all"),
        ]])
    )


async def back(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kb = [
        [InlineKeyboardButton("🔍 Подобрать объект",  callback_data="search")],
        [InlineKeyboardButton("📋 Все объекты",        callback_data="all")],
        [InlineKeyboardButton("🔄 Обновить из канала", callback_data="sync")],
    ]
    await q.edit_message_text(
        f"В базе: *{len(PROPERTIES)} объектов*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def search_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["filters"] = {}
    return await ask_type(q)


async def ask_type(q):
    kb = [[InlineKeyboardButton(t.capitalize(), callback_data=f"type_{t}")] for t in uniq("type")]
    kb.append([InlineKeyboardButton("🔀 Любой", callback_data="type_любой")])
    await q.edit_message_text("🏠 Тип объекта:", reply_markup=InlineKeyboardMarkup(kb))
    return S_TYPE


async def got_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    ctx.user_data["filters"]["type"] = q.data.replace("type_", "")
    cities = uniq("city")
    kb = [[InlineKeyboardButton(c, callback_data=f"city_{c}")] for c in cities]
    kb.append([InlineKeyboardButton("🔀 Любой", callback_data="city_любой")])
    await q.edit_message_text("🏙 Город:", reply_markup=InlineKeyboardMarkup(kb))
    return S_CITY


async def got_city(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    val = q.data.replace("city_", "")
    ctx.user_data["filters"]["city"] = val
    chosen = val if val != "любой" else None
    districts = sorted(set(
        p["district"] for p in PROPERTIES
        if p.get("district") and (not chosen or p.get("city") == chosen)
    ))
    kb = [[InlineKeyboardButton(d, callback_data=f"dist_{d}")] for d in districts]
    kb.append([InlineKeyboardButton("🔀 Любой", callback_data="dist_любой")])
    await q.edit_message_text("📍 Район:", reply_markup=InlineKeyboardMarkup(kb))
    return S_DISTRICT


async def got_district(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    ctx.user_data["filters"]["district"] = q.data.replace("dist_", "")
    kb = [
        [InlineKeyboardButton("Студия",    callback_data="bed_0")],
        [InlineKeyboardButton("1 спальня", callback_data="bed_1")],
        [InlineKeyboardButton("2 спальни", callback_data="bed_2")],
        [InlineKeyboardButton("3 спальни", callback_data="bed_3")],
        [InlineKeyboardButton("4+ спален", callback_data="bed_4")],
        [InlineKeyboardButton("🔀 Не важно", callback_data="bed_-1")],
    ]
    await q.edit_message_text("🛏 Спальни:", reply_markup=InlineKeyboardMarkup(kb))
    return S_BEDROOMS


async def got_bedrooms(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    ctx.user_data["filters"]["bedrooms"] = int(q.data.replace("bed_", ""))
    kb = [
        [InlineKeyboardButton("до €200 000",     callback_data="price_0_200000")],
        [InlineKeyboardButton("€200k – €400k",   callback_data="price_200000_400000")],
        [InlineKeyboardButton("€400k – €700k",   callback_data="price_400000_700000")],
        [InlineKeyboardButton("€700k – €1.5М",   callback_data="price_700000_1500000")],
        [InlineKeyboardButton("от €1.5М",        callback_data="price_1500000_99999999")],
        [InlineKeyboardButton("🔀 Любой бюджет", callback_data="price_0_99999999")],
    ]
    await q.edit_message_text("💶 Бюджет:", reply_markup=InlineKeyboardMarkup(kb))
    return S_PRICE


async def got_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    _, mn, mx = q.data.split("_")
    f = ctx.user_data["filters"]
    f["price_min"] = int(mn)
    f["price_max"] = int(mx)
    results = [p for p in PROPERTIES if match(p, f)]
    await send_results(q, results)
    return ConversationHandler.END


async def send_results(q, results):
    if not results:
        await q.edit_message_text(
            "😔 Ничего не найдено по этим критериям.\nПопробуй изменить фильтры.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔍 Новый поиск", callback_data="search")
            ]])
        )
        return

    text = f"✅ *Найдено: {len(results)}*\n\n"
    kb = []
    for p in results:
        beds = ", ".join("студия" if b == 0 else f"{b} сп." for b in p.get("bedrooms", []))
        text += (
            f"🏠 *{p['title']}*\n"
            f"📍 {p.get('city','')}  {p.get('district','')}\n"
            f"🛏 {beds}   💶 от {fmt(p['price_from'])}\n"
            f"🗝 {p.get('ready','')}  —  _{p.get('desc','')}_\n\n"
        )
        short = p["title"][:38] + ("…" if len(p["title"]) > 38 else "")
        kb.append([InlineKeyboardButton(f"👁 {short}", url=p["link"])])
    kb.append([
        InlineKeyboardButton("🔍 Новый поиск", callback_data="search"),
        InlineKeyboardButton("📋 Все",         callback_data="all"),
    ])
    await q.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb),
        disable_web_page_preview=True,
    )


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено. /start — начать заново")
    return ConversationHandler.END


# ─────────────────────────────────────────────
# ЗАПУСК
# ─────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(search_start, pattern="^search$")],
        states={
            S_TYPE:     [CallbackQueryHandler(got_type,     pattern="^type_")],
            S_CITY:     [CallbackQueryHandler(got_city,     pattern="^city_")],
            S_DISTRICT: [CallbackQueryHandler(got_district, pattern="^dist_")],
            S_BEDROOMS: [CallbackQueryHandler(got_bedrooms, pattern="^bed_")],
            S_PRICE:    [CallbackQueryHandler(got_price,    pattern="^price_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_all, pattern="^all$"))
    app.add_handler(CallbackQueryHandler(do_sync,  pattern="^sync$"))
    app.add_handler(CallbackQueryHandler(back,     pattern="^back$"))
    app.add_handler(conv)

    print(f"✅ Бот запущен. Объектов в базе: {len(PROPERTIES)}")
    app.run_polling()


if __name__ == "__main__":
    main()
