"""
Telegram-бот для фильтрации недвижимости из канала @zats_denis
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

BOT_TOKEN = "8691313667:AAFtI9CUFia_Ew2_3vXLJ7Zivgy1C7Yzx0s"
CHANNEL   = "zats_denis"
DB_FILE   = "properties.json"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_PROPERTIES = [
    {
        "id": 1041,
        "title": "Готовые апартаменты в центре города",
        "city": "Лимассол", "district": "Мессагитония",
        "type": "апартаменты", "bedrooms": [1, 2, 3],
        "price_from": 317000, "price_to": 700000,
        "ready": "Q2/2026",
        "link": "https://t.me/zats_denis/1041",
        "desc": "Первая линия, вид на море. 1 сп от 317k, 2 сп от 436k, 3 сп от 513k евро"
    },
    {
        "id": 1054,
        "title": "Пресейл рядом с пляжем Ледис Майл",
        "city": "Лимассол", "district": "Закаки",
        "type": "апартаменты", "bedrooms": [0, 1, 2],
        "price_from": 185000, "price_to": 450000,
        "ready": "Q3/2028",
        "link": "https://t.me/zats_denis/1054",
        "desc": "Студия от 185k, 1 сп от 230k, 2 сп от 340k евро. Рассрочка"
    },
    {
        "id": 1060,
        "title": "Старт продаж на холмах",
        "city": "Лимассол", "district": "Гермасоя",
        "type": "апартаменты", "bedrooms": [1, 2, 3],
        "price_from": 232000, "price_to": 600000,
        "ready": "Q3/2028",
        "link": "https://t.me/zats_denis/1060",
        "desc": "Вид на море и горы. 1 сп от 232k, 2 сп от 378k, 3 сп от 486k евро. Рассрочка"
    },
    {
        "id": 1005,
        "title": "Виллы в приватном комплексе",
        "city": "Лимассол", "district": "Гермасоя",
        "type": "вилла", "bedrooms": [4, 5],
        "price_from": 1400000, "price_to": 3000000,
        "ready": "Готово",
        "link": "https://t.me/zats_denis/1005",
        "desc": "6 вилл, холмы, вид на море. 10 мин до центра"
    },
]

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

def fmt(p):
    return "€{:,}".format(p).replace(",", " ")

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

S_TYPE, S_CITY, S_DISTRICT, S_BEDROOMS, S_PRICE = range(5)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    kb = [
        [InlineKeyboardButton("🔍 Подобрать объект", callback_data="search")],
        [InlineKeyboardButton("📋 Все объекты",       callback_data="all")],
        [InlineKeyboardButton("🔄 Обновить из канала", callback_data="sync")],
    ]
    await update.message.reply_text(
        "Привет! Недвижимость на Кипре из @zats_denis\n\nВ базе: {} объектов".format(len(PROPERTIES)),
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
    await q.edit_message_text("Проверяю канал на новые объекты...")
    if not ANTHROPIC_API_KEY:
        await q.edit_message_text(
            "Для авто-парсинга нужен ключ Anthropic API.\nВставь его в переменную ANTHROPIC_API_KEY в Railway Variables.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data="back")]])
        )
        return
    await q.edit_message_text(
        "Готово! Всего в базе: {}".format(len(PROPERTIES)),
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
        "В базе: {} объектов".format(len(PROPERTIES)),
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def search_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["filters"] = {}
    return await ask_type(q)

async def ask_type(q):
    kb = [[InlineKeyboardButton(t.capitalize(), callback_data="type_{}".format(t))] for t in uniq("type")]
    kb.append([InlineKeyboardButton("Любой тип", callback_data="type_любой")])
    await q.edit_message_text("Тип объекта:", reply_markup=InlineKeyboardMarkup(kb))
    return S_TYPE

async def got_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    ctx.user_data["filters"]["type"] = q.data.replace("type_", "")
    cities = uniq("city")
    kb = [[InlineKeyboardButton(c, callback_data="city_{}".format(c))] for c in cities]
    kb.append([InlineKeyboardButton("Любой город", callback_data="city_любой")])
    await q.edit_message_text("Город:", reply_markup=InlineKeyboardMarkup(kb))
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
    kb = [[InlineKeyboardButton(d, callback_data="dist_{}".format(d))] for d in districts]
    kb.append([InlineKeyboardButton("Любой район", callback_data="dist_любой")])
    await q.edit_message_text("Район:", reply_markup=InlineKeyboardMarkup(kb))
    return S_DISTRICT

async def got_district(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    ctx.user_data["filters"]["district"] = q.data.replace("dist_", "")
    kb = [
        [InlineKeyboardButton("Студия",      callback_data="bed_0")],
        [InlineKeyboardButton("1 спальня",   callback_data="bed_1")],
        [InlineKeyboardButton("2 спальни",   callback_data="bed_2")],
        [InlineKeyboardButton("3 спальни",   callback_data="bed_3")],
        [InlineKeyboardButton("4+ спален",   callback_data="bed_4")],
        [InlineKeyboardButton("Не важно",    callback_data="bed_-1")],
    ]
    await q.edit_message_text("Спальни:", reply_markup=InlineKeyboardMarkup(kb))
    return S_BEDROOMS

async def got_bedrooms(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    ctx.user_data["filters"]["bedrooms"] = int(q.data.replace("bed_", ""))
    kb = [
        [InlineKeyboardButton("до 200 000 евро",     callback_data="price_0_200000")],
        [InlineKeyboardButton("200k - 400k евро",    callback_data="price_200000_400000")],
        [InlineKeyboardButton("400k - 700k евро",    callback_data="price_400000_700000")],
        [InlineKeyboardButton("700k - 1.5М евро",    callback_data="price_700000_1500000")],
        [InlineKeyboardButton("от 1.5М евро",        callback_data="price_1500000_99999999")],
        [InlineKeyboardButton("Любой бюджет",        callback_data="price_0_99999999")],
    ]
    await q.edit_message_text("Бюджет:", reply_markup=InlineKeyboardMarkup(kb))
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
            "Ничего не найдено по этим критериям. Попробуй изменить фильтры.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Новый поиск", callback_data="search")
            ]])
        )
        return

    text = "Найдено: {} объект(ов)\n\n".format(len(results))
    kb = []
    for p in results:
        beds = ", ".join("студия" if b == 0 else "{} сп.".format(b) for b in p.get("bedrooms", []))
        text += (
            "{}\n"
            "Город: {}, {}\n"
            "Спальни: {}\n"
            "Цена: от {}\n"
            "Ключи: {}\n"
            "{}\n\n"
        ).format(
            p["title"],
            p.get("city",""), p.get("district",""),
            beds,
            fmt(p["price_from"]),
            p.get("ready",""),
            p.get("desc","")
        )
        short = p["title"][:38] + ("..." if len(p["title"]) > 38 else "")
        kb.append([InlineKeyboardButton("Открыть: {}".format(short), url=p["link"])])
    kb.append([
        InlineKeyboardButton("Новый поиск", callback_data="search"),
        InlineKeyboardButton("Все объекты", callback_data="all"),
    ])
    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(kb),
        disable_web_page_preview=True,
    )

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено. /start — начать заново")
    return ConversationHandler.END

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
    print("Бот запущен. Объектов в базе: {}".format(len(PROPERTIES)))
    app.run_polling()

if __name__ == "__main__":
    main()
