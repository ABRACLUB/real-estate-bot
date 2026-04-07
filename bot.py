"""
Telegram-бот для фильтрации недвижимости из канала @zats_denis
"""

import logging
import json
import os
import re
import urllib.request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler
)
from telegram.error import BadRequest

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL   = "@zats_denis"
DB_FILE   = "properties.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_PROPERTIES = [
    {"id":78,"title":"Роскошная вилла в комплексе Castle Residences","city":"Лимассол","district":"Марина","type":"вилла","bedrooms":[3],"price_from":3900000,"price_to":3900000,"ready":"Готово","link":"https://t.me/zats_denis/78","desc":"📍Локация: Лимассол Марина 💶Цена: €3.900.000 (комиссия 0%) Особенности: 🏗 Общая площадь: 138 м²"},
    {"id":91,"title":"Вилла в элитном пляжном комплексе Akamas Bay Villas","city":"Пафос","district":"Полис","type":"вилла","bedrooms":[1, 4],"price_from":1370000,"price_to":1370000,"ready":"Готово","link":"https://t.me/zats_denis/91","desc":"📍 Локация: Полис 💶 €1.370.000 (комиссия 0%) Особенности: 🏗 Общая площадь: 246 м² ☂️ Крытая терраса: 30 м²"},
    {"id":103,"title":"Апартаменты с видом на море и горы Princess Star","city":"Лимассол","district":"","type":"апартаменты","bedrooms":[2, 3],"price_from":689202,"price_to":969024,"ready":"Готово","link":"https://t.me/zats_denis/103","desc":"📍Локация: Лимасол, инфраструктурный район — Мутаяка 💶 Цена: 2BR - €689.202 - €804.105 3BR - €872.108 - €969.024 (комиссии нет)"},
    {"id":120,"title":"Последний юнит в апартаментах бизнес-класса Arcadia Residences 3","city":"Пафос","district":"Като Пафос","type":"апартаменты","bedrooms":[2],"price_from":470000,"price_to":470000,"ready":"Уточняйте","link":"https://t.me/zats_denis/120","desc":"📍Локация: Като Пафос 💶 Цена: €470.000 (комиссии нет) Основные особенности: 🏠 Площадь 82 м²"},
    {"id":126,"title":"Апартаменты в бутик-проекте Aktea Residences 4","city":"Лимассол","district":"","type":"апартаменты","bedrooms":[2],"price_from":510000,"price_to":510000,"ready":"Уточняйте","link":"https://t.me/zats_denis/126","desc":"📍Локация: Лимассол 💶 Цена: €510.000 (комиссии нет) Основные особенности: 🏠 Площадь 87 м²"},
    {"id":132,"title":"Роскошная вилла в комплексе Castle Residences","city":"Лимассол","district":"Марина","type":"вилла","bedrooms":[2, 6],"price_from":9600000,"price_to":9600000,"ready":"Готово","link":"https://t.me/zats_denis/132","desc":"📍Локация: Лимассол Марина 💶Цена: €9.600.000 (комиссия 0%) Особенности: 🏗 Общая площадь: 230 м²"},
    {"id":137,"title":"Таунхаус в комплексе Melrose","city":"Лимассол","district":"Агиос Тихонас","type":"таунхаус","bedrooms":[1],"price_from":799000,"price_to":799000,"ready":"Готово","link":"https://t.me/zats_denis/137","desc":"📍Локация: Один из лучших районов Лимасола — Агиос Тихонас 💶 Цена на старте: €799.000 (комиссия 0%) Основные особенности: 🏠 Площадь 54 м² ☂️ Крытая веранда 18 м²"},
    {"id":150,"title":"Апартаменты в комплексе Galaxy Residences","city":"Пафос","district":"","type":"апартаменты","bedrooms":[2, 3],"price_from":320000,"price_to":825000,"ready":"Готово","link":"https://t.me/zats_denis/150","desc":"📍Локация: Пафос, район Анаваргос 💶 Цена: 2BR - €320.000-€445.000 3BR - €430.000 - €825.000 (комиссии нет)"},
    {"id":163,"title":"Пентхаус в комплексе The heritage","city":"Пафос","district":"","type":"апартаменты","bedrooms":[3],"price_from":495000,"price_to":495000,"ready":"Готово","link":"https://t.me/zats_denis/163","desc":"📍Локация: Пафос 💶Цена: €495.000 (комиссия 0%) Особенности: 🏠 Площадь: 107.3 м²"},
    {"id":170,"title":"Закрытый пресейл на виллу в  Harmony Residences 2","city":"Пафос","district":"","type":"апартаменты","bedrooms":[3],"price_from":735000,"price_to":735000,"ready":"Уточняйте","link":"https://t.me/zats_denis/170","desc":"📍Локация: Paphos, Geroskipou 💶 Цена: €735.000 (комиссия 0%) Основные особенности: 🏠 Площадь 151 м² ☂️ Крытая веранда 47 м²"},
    {"id":176,"title":"Апартаменты в жилом комплексе Adonidos Gardens","city":"Пафос","district":"","type":"апартаменты","bedrooms":[1, 2],"price_from":210000,"price_to":290000,"ready":"Уточняйте","link":"https://t.me/zats_denis/176","desc":"📍Локация: Geroskipou, Paphos 💶Цена: ST - €170.000 - €190.000 1BR - €210.000 - €230.000 2BR - €275.000 - €290.000"},
    {"id":180,"title":"Комплекс вилл Elite Residences в горячем туристическом районе","city":"Пафос","district":"","type":"апартаменты","bedrooms":[3],"price_from":850000,"price_to":900000,"ready":"Уточняйте","link":"https://t.me/zats_denis/180","desc":"📍Локация: Paphos, Geroskipou 💶 Цена: €850.000-€900.000 (комиссия 0%) Основные особенности: 🏠 Площадь 157-190.45 м² ☂️ Крытая веранда 38-41 м²"},
    {"id":187,"title":"Пресейл комплекса Naftikos Residences в ТОП районе Лимасола","city":"Лимассол","district":"","type":"апартаменты","bedrooms":[2, 3],"price_from":680000,"price_to":950000,"ready":"Готово","link":"https://t.me/zats_denis/187","desc":"📍Локация: Agios Athanasios Limassol 💶Цена: 2BR - €680.000 - €880.000 3BR - €950.000 (комиссия 0%)"},
    {"id":196,"title":"Вилла на первой линии с видом на закат","city":"Пафос","district":"","type":"вилла","bedrooms":[5],"price_from":3400000,"price_to":3400000,"ready":"Уточняйте","link":"https://t.me/zats_denis/196","desc":"📍Локация: Paphos 💶 Цена: €3.400.000 (комиссия 0%) Основные особенности: 🏠 Площадь 392.60 м² ☂️ Крытая веранда 75.40 м²"},
    {"id":202,"title":"ЖК с панорамным видом на город и море Seaview Heights!","city":"Лимассол","district":"","type":"дом","bedrooms":[1],"price_from":305000,"price_to":305000,"ready":"Уточняйте","link":"https://t.me/zats_denis/202","desc":"📍Локация: Лимассол 💶 Цена: €305,000 (комиссия 0%) Основные особенности: 🏠 Площадь 56 м² 🛋 Гостиная + 1 спальня"},
    {"id":214,"title":"Люкс апартаменты на первой линии в башнях Trilogy","city":"Лимассол","district":"","type":"апартаменты","bedrooms":[1, 2, 3],"price_from":710000,"price_to":2200000,"ready":"Готово","link":"https://t.me/zats_denis/214","desc":"📍Локация: в самом сердце Лимасола 💶Цена: 1BR - €710.000 - €840.000 2BR - €1.250.000 - €2.350.000 3BR - €1.300.000 - €2.200.000"},
    {"id":222,"title":"Апартаменты с видом на гольф поле в комплексе Golfside","city":"Лимассол","district":"Центр","type":"апартаменты","bedrooms":[1, 2],"price_from":230000,"price_to":380000,"ready":"Уточняйте","link":"https://t.me/zats_denis/222","desc":"📍Локация: в 2 минутах от торгового центра 💶Цена: 1BR - €230.000 - €270.000 2BR - €370.000 - €380.000 (комиссия 0%)"},
    {"id":226,"title":"Комплекс над городом с видом  на море Germasogeia View 2","city":"Лимассол","district":"Гермасоя","type":"дом","bedrooms":[1, 2],"price_from":265000,"price_to":460000,"ready":"Уточняйте","link":"https://t.me/zats_denis/226","desc":"📍Локация: в 10 минутах от всей инфраструктуры 💶Цена: 1BR - €265.000 - €285.000 2BR - €375.000 - €460.000 (комиссия 0%)"},
    {"id":235,"title":"Комплекс с мед пунктом 247 Cypress Park","city":"Пафос","district":"","type":"апартаменты","bedrooms":[1, 2, 3],"price_from":210000,"price_to":450000,"ready":"2026 г","link":"https://t.me/zats_denis/235","desc":"📍Локация: в тихом пригороде Пафоса 💶 Цена: ST - €170.000 1BR - €210.000 - €230.000 2BR - €295.000 - €395.000"},
    {"id":251,"title":"Горячий пресейл комплекса вилл Amber Homes","city":"Пафос","district":"","type":"апартаменты","bedrooms":[3],"price_from":480000,"price_to":520000,"ready":"Уточняйте","link":"https://t.me/zats_denis/251","desc":"📍Локация: в 15 минутах от центра Пафоса 💶 Цена: 3BR - €480.000 - €520.000 (комиссия 0%) Основные особенности:"},
    {"id":256,"title":"Современные виллы с видом на море в 7 минутах от побережья","city":"Пафос","district":"Пейя","type":"дом","bedrooms":[3],"price_from":480000,"price_to":480000,"ready":"Уточняйте","link":"https://t.me/zats_denis/256","desc":"📍Riza Heights 1, Пейя, Пафос 💶 Цена: 3BR - €480.000 (комиссия 0%) Основные особенности:"},
    {"id":263,"title":"Виллы с видом на море в комплексе Agnades Village 1","city":"Лимассол","district":"Центр","type":"вилла","bedrooms":[3, 4],"price_from":494000,"price_to":583000,"ready":"Уточняйте","link":"https://t.me/zats_denis/263","desc":"📍Локация: рядом с национальным парком Акамас 💶 Цена: 3BR - €494.000 - €680.000 4BR - €539.000 - €583.000 (комиссия 0%)"},
    {"id":268,"title":"Комплекс Almond Villas в горных холмах рядом с гольф курортом","city":"Пафос","district":"","type":"вилла","bedrooms":[3],"price_from":495000,"price_to":520000,"ready":"Уточняйте","link":"https://t.me/zats_denis/268","desc":"📍Локация: 15 минут до центра Пафоса 💶 Цена: 3BR - €495.000-€520.000 (комиссия 0%) Основные особенности:"},
    {"id":273,"title":"Танхаусы с панорамными видами на море в комплексе Zephyros Village 3","city":"Лимассол","district":"Центр","type":"вилла","bedrooms":[2, 3],"price_from":315000,"price_to":380000,"ready":"Уточняйте","link":"https://t.me/zats_denis/273","desc":"📍Локация: в 15 минутах от гольф курорта Aphrodite Hills 💶 Цена: 2BR - €315.000-€335.000 3BR - €340.000-€380.000 (комиссия 0%)"},
    {"id":285,"title":"Апартаменты Paphos Suites с панорамным видом на горы и море","city":"Пафос","district":"","type":"апартаменты","bedrooms":[1],"price_from":250000,"price_to":270000,"ready":"Уточняйте","link":"https://t.me/zats_denis/285","desc":"📍Локация: в 15 минутах от центра Пафоса 💶 Цена: 1BR - €250.000 - €270.000 (комиссия 0%) Основные особенности:"},
    {"id":290,"title":"Роскошная вилла в комплексе Aria Residences с панорамным видом","city":"Лимассол","district":"Центр","type":"вилла","bedrooms":[3],"price_from":1580000,"price_to":1580000,"ready":"Готово","link":"https://t.me/zats_denis/290","desc":"📍Локация: в прибрежном районе Agios Tychonas, всего в нескольких минутах от центра Лимассола 💶 Цена: 3BR - €1.580.000 (комиссия 0%) Основные особенности:"},
    {"id":296,"title":"Новинка на рынке: вилла в комплексе Lana Villas","city":"Лимассол","district":"Центр","type":"вилла","bedrooms":[3],"price_from":900000,"price_to":960000,"ready":"Уточняйте","link":"https://t.me/zats_denis/296","desc":"📍 Локация: среди живописных холмов Лимассола, в 10 минутах от пляжа 💶 Цена: 3BR — €900.000 - €960.000 (комиссия 0%) Основные особенности:"},
    {"id":303,"title":"Ультра-люксовый дуплекс в башне Limassol ONE","city":"Лимассол","district":"Центр","type":"апартаменты","bedrooms":[3],"price_from":5400000,"price_to":5400000,"ready":"Готово","link":"https://t.me/zats_denis/303","desc":"📍 Локация: на первой линии моря в самом сердце города 💶 Цена: 3BR Duplex — €5.400.000 (комиссия 0%) Основные особенности:"},
    {"id":339,"title":"Бутиковая жемчужина на 8 юнитов от известного архитектора Романа Власова","city":"Лимассол","district":"","type":"апартаменты","bedrooms":[3],"price_from":660000,"price_to":660000,"ready":"Готово","link":"https://t.me/zats_denis/339","desc":"📍Лимассол, инфраструктурный район Мутаяка, 350 метров от моря 💶 Цена: от €660,000 (комиссии нет) Основные особенности: 🏠 Внутренняя площадь — 121 м² ☂️ Крытая веранда — 24 м²"},
    {"id":359,"title":"Виллы в рассрочку на 2 года после сдачи объекта","city":"Лимассол","district":"","type":"дом","bedrooms":[3],"price_from":700000,"price_to":700000,"ready":"2026 г","link":"https://t.me/zats_denis/359","desc":"📍Киссонерга в 350 метрах от моря, рядом с банановой рощей 💶 На текущем этапе цена от €700,000 (комиссия 0%) ✅ Район с высокой инвестиционной привлекательностью! Власти Кипра планируют строить марину в Киссонерга, что приведет к росту цен на недвижимо"},
    {"id":369,"title":"Резиденция с великолепным видом на природу и гольф-поле","city":"Пафос","district":"","type":"дом","bedrooms":[1],"price_from":1200000,"price_to":1200000,"ready":"Готово","link":"https://t.me/zats_denis/369","desc":"📍 Расположена на тихом холме в заповеднике 💶 Цена: от €1,200,000 Основные характеристики: 🏠 Общая площадь: 241 м² 🛏 Спальни: от 4"},
    {"id":418,"title":"Коммерческая недвижимость в центре Пафоса","city":"Пафос","district":"","type":"дом","bedrooms":[1],"price_from":2200000,"price_to":2200000,"ready":"Уточняйте","link":"https://t.me/zats_denis/418","desc":"Современное здание с морским видом. На нулевом этаже — магазины и супермаркеты, на первом — ресторан с верандой и панорамой моря. 📍 Локация: центр Пафоса 🏢 Общая площадь: 374 м² 💼 Офис: 364 м² + кладовая 16,5 м² + веранда 10 м² 🌊 Вид на море со всех "},
    {"id":431,"title":"ТОП 3 квартира 11 на котловане","city":"Пафос","district":"","type":"апартаменты","bedrooms":[1],"price_from":190000,"price_to":380000,"ready":"Q4/2027","link":"https://t.me/zats_denis/431","desc":"Пресейл в комплекса в центре Пафоса с шаговой доступностью от университетов, магазинов и всей инфраструктуры 📍Пафос, старый город ✅ Входит в цену: • Двойные стеклопакеты • Солнечн нагрева воды"},
    {"id":481,"title":"Горячий пресейл с рассрочкой до 5 лет","city":"Пафос","district":"","type":"апартаменты","bedrooms":[2, 3],"price_from":94000,"price_to":94000,"ready":"2027 г","link":"https://t.me/zats_denis/481","desc":"📍 Пафос, Старый город С первым взносом от €94000 — Площадь квартир от 88м² — Крытая веранда 7м² — 2 спальни"},
    {"id":538,"title":"Горячий пресейл в инфраструктурном комплексе с видом на море и горы","city":"Пафос","district":"Хлорака","type":"апартаменты","bedrooms":[1],"price_from":250000,"price_to":500000,"ready":"Q1/2027","link":"https://t.me/zats_denis/538","desc":"📍Пафос, Хлорака Бутик-комплекс с премиальной инфраструктурой (спа, хаммам, зал 300 м², терраса 456 м², бассейн без хлора), панорамными видами на море и прогнозируемым ростом стоимости на 20% при чистой доходности около 6% годовых ✅ Входит в цену: • V"},
    {"id":550,"title":"Пресейл комплекса сочетающего коммерческие и жилые юниты с полной инфраструктуро","city":"Лимассол","district":"","type":"апартаменты","bedrooms":[1],"price_from":64000,"price_to":64000,"ready":"Q2/2028","link":"https://t.me/zats_denis/550","desc":"📍Лимассол, Агиос Афанасиос Комплекс объединяет ресторан, SPA, бассейны, сауны, офисные пространства и жилую недвижимость, создавая редкую модель, где работники офисов формируют стабильный спрос на апартаменты ✅ Входит в цену: • VRV климат • Двойные с"},
    {"id":557,"title":"Пресейл в проекте где каждая квартира имеет прямой вид на море и Лимассол","city":"Лимассол","district":"Гермасоя","type":"апартаменты","bedrooms":[1],"price_from":106000,"price_to":106000,"ready":"Q1/2027","link":"https://t.me/zats_denis/557","desc":"📍Лимассол, Гермасоя Современный бутик-дом на 3 этажа в престижной Гермасойе с большими террасами, энергоклассом А, мраморной отделкой, паркетом. ✅ Входит в цену: • VRV климат • Двойные стеклопакеты"},
    {"id":591,"title":"Пентхаус с личным бассейном и прямым видом на море в 350м от пляжа","city":"Лимассол","district":"","type":"апартаменты","bedrooms":[1],"price_from":1488000,"price_to":1661000,"ready":"Q3/2026","link":"https://t.me/zats_denis/591","desc":"📍Лимассол, Мутояка Элитный объект с футуристичным дизайном от орхитектора Романа Власова. Энергоэффективность А - система отопления на солнечных панелях с тепловым насосом. ✅ Входит в цену: • Личный бассейн • Общий бассейн"},
    {"id":609,"title":"Почти готовый пентхаус с прямым видом на море в 180м от пляжа","city":"Лимассол","district":"","type":"апартаменты","bedrooms":[1],"price_from":2185000,"price_to":2185000,"ready":"Q1/2026","link":"https://t.me/zats_denis/609","desc":"📍Лимассол, Мутаяка Объект в инфраструктурном районе, рядом с супермаркетами Лидл и Метро, автобусные остановки, школы - всё рядом ✅ Входит в цену: • Личный бассейн • Общий бассейн"},
    {"id":633,"title":"Готовая двухуровневая вилла с собственным лифтом и пятизвездочным сервисом 247","city":"Пафос","district":"Пейя","type":"вилла","bedrooms":[1],"price_from":2000000,"price_to":2000000,"ready":"Готово","link":"https://t.me/zats_denis/633","desc":"📍Пафос, Пейя Вилла с премиальной отделкой из натурального мрамора, системой отопления от солнечных панелей и теплового насоса, с дорогой сантехникой и полностью укомплектованная мебелью, техникой и декором — готова к заселению «под ключ». Панорамный "},
    {"id":640,"title":"Трехуровневая вилла с возможностью рассрочки и заселением через год","city":"Пафос","district":"Пейя","type":"вилла","bedrooms":[1],"price_from":2200000,"price_to":2200000,"ready":"Q4/2027","link":"https://t.me/zats_denis/640","desc":"📍Пафос, Пейя Вилла с премиальной отделкой из натурального мрамора и дерева, системой отопления от солнечных панелей и теплового насоса, с дорогой сантехникой и полностью укомплектованная мебелью, техникой и декором «под ключ». Панорамный инфинити-бас"},
    {"id":653,"title":"Трёхуровневая вилла с прямым видом на закатное море и огромным участком","city":"Пафос","district":"Пейя","type":"вилла","bedrooms":[1],"price_from":4200000,"price_to":4200000,"ready":"Q4/2028","link":"https://t.me/zats_denis/653","desc":"📍Пафос, Пейя Вилла на котловане с премиальной отделкой из натурального мрамора и дерева, с дорогой сантехникой, полностью укомплектованная мебелью, техникой и декором «под ключ». Панорамный инфинити-бассейн с видом на море, просторный ухоженный участ"},
    {"id":663,"title":"Последняя двухуровневая вилла закрытого поселка в 350 метрах от моря с жирнейшим","city":"Пафос","district":"","type":"вилла","bedrooms":[1],"price_from":799000,"price_to":799000,"ready":"Q1/2026","link":"https://t.me/zats_denis/663","desc":"📍Пафос, Кисонерга Вилла с премиальной отделкой из натурального камня, системой отопления от солнечных панелей и теплового насоса, с дорогой сантехникой и полностью укомплектованная мебелью, техникой и декором «под ключ» ✅ В цену входит всё: • VRV кли"},
    {"id":683,"title":"Приватная трехуровневая вилла на побережье с эксплуатируемой крышей и лифтом","city":"Пафос","district":"Хлорака","type":"вилла","bedrooms":[1],"price_from":3190000,"price_to":3190000,"ready":"Q2/2026","link":"https://t.me/zats_denis/683","desc":"📍Пафос, Хлорака Роскошная вилла с частным инфинити-бассейном, панорамными видами на Средиземное море и безупречной архитектурой в средиземноморском стиле. Трёхуровневая резиденция с лифтом, приватным участком и премиальной отделкой создана для жизни "},
    {"id":695,"title":"Двухуровневая вилла в 400 метрах от пляжа с готовностью меньше чем через год","city":"Пафос","district":"","type":"вилла","bedrooms":[1],"price_from":750000,"price_to":750000,"ready":"Q3/2026","link":"https://t.me/zats_denis/695","desc":"📍Пафос, Героскипу Современная вилла с частным бассейном и эксплуатируемой крышей с продуманной планировкой, большими верандами ✅ В цену входит: • Бассейн • Двойные стеклопакеты"},
    {"id":706,"title":"Приватная квартира с прямым видом на море и выходом к пляжу в полную собственнос","city":"Лимассол","district":"Агиос Тихонас","type":"апартаменты","bedrooms":[1],"price_from":2700000,"price_to":2700000,"ready":"Готово","link":"https://t.me/zats_denis/706","desc":"📍Лимассол, Агиос Тихонас В доме всего 17 квартир, в которых постоянно проживают лишь в половине. КПП с охраной, подземный паркинг, спорт зал и СПА комплекс с саунами и общей кухнейё, где можно душевно отмечать праздники. ✅ В цену входит всё: • VRV кл"},
    {"id":740,"title":"Видовые апартаменты на холмах Лимассола","city":"Лимассол","district":"Марина","type":"апартаменты","bedrooms":[1],"price_from":1134000,"price_to":3231000,"ready":"Уточняйте","link":"https://t.me/zats_denis/740","desc":"📍 Лимассол, Агиос Тихонас Возвышенность над морем, рядом St. Raphael Marina и археологический парк Ancient Amathus Бутиковый жилой комплекс из 4 зданий в одном из самых престижных и тихих районов Лимассола. Панорамные виды на море, закрытая территори"},
    {"id":772,"title":"Бутик-апартаменты в центре Лимассола в 1 км от Лимассол марины и набережной","city":"Лимассол","district":"Центр","type":"апартаменты","bedrooms":[2],"price_from":399000,"price_to":399000,"ready":"Q4/2027","link":"https://t.me/zats_denis/772","desc":"📍 Лимассол, Старый город В комплексе осталась последняя квартира с эксплуатируемой крышей. Фактически - это пентхаус, если подойти к покупке с головой - можно даже установить собственный бассейн и получить огромное конкурентное преимущество для сдачи"},
    {"id":776,"title":"Пресейл инфраструктурного комплекса с большими террасами и быстрым доступом к де","city":"Лимассол","district":"Гермасоя","type":"апартаменты","bedrooms":[1],"price_from":290000,"price_to":580000,"ready":"Q2/2029","link":"https://t.me/zats_denis/776","desc":"📍 Лимассол, Гермасоя Тихий зелёный район, где городская динамика сочетается с ощущением уюта и приватности. Просторные веранды, светлые современные планировки и собственная инфраструктура создают высокий комфорт жизни ✅ Входит в цену: • Склад • Парке"},
    {"id":786,"title":"Закрытое комьюнити с масштабной инфраструктурой, рядом с гольф полями","city":"Лимассол","district":"","type":"дом","bedrooms":[1],"price_from":215700,"price_to":431400,"ready":"Q4/2028","link":"https://t.me/zats_denis/786","desc":"📍 Лимассол, Асоматос Просторное современное сообщество в зелёной части города, где утро начинается у бассейна, день проходит между спортом, природой и работой в коворкинге, а вечер — на собственной веранде в тишине. Формат жизни как в резорте, но в п"},
    {"id":796,"title":"Последняя двухспальная квартира с панорамными окнами и приватными террасами в зе","city":"Лимассол","district":"Гермасоя","type":"апартаменты","bedrooms":[1],"price_from":534150,"price_to":534150,"ready":"Q2/2026","link":"https://t.me/zats_denis/796","desc":"📍 Лимассол, нижняя Гермасоя Тихие улицы в тени деревьев, ощущение уединения и при этом всего несколько минут до марины, пляжей, ресторанов и делового-центра. Камерный формат дома, много света, большие террасы и продуманный дизайн ✅ Входит в цену: • К"},
    {"id":806,"title":"Пентхаус с панорамными окнами по цене квартиры","city":"Лимассол","district":"","type":"апартаменты","bedrooms":[2],"price_from":439000,"price_to":439000,"ready":"Q4/2027","link":"https://t.me/zats_denis/806","desc":"📍 Лимассол, Старый город Современный дом внутри городской инфраструктуры, для тех, кто ценит свет и приватность. Уютная планировка с выходом на веранду и лестницей на крышу ✔️ Входит в цену: • Недвижимая мебель • Паркет"},
    {"id":820,"title":"Квартиры с двумя спальнями от крупнейшего застройщика Кипра со сдачей уже в этом","city":"Лимассол","district":"Центр","type":"апартаменты","bedrooms":[2],"price_from":510000,"price_to":510000,"ready":"Q4/2026","link":"https://t.me/zats_denis/820","desc":"📍 Лимассол, Агиос Афанасиос Камерный жилой дом в развитом городском районе: много света, приватность, просторные веранды и ощущение качественной городской жизни без компромиссов. Формат для тех, кто хочет жить в центре ✅ Входит в цену: • VRV климат •"},
    {"id":954,"title":"Виллы на этапе строительства со сдачей через год в 5 минутах от знаменитого пляж","city":"Пафос","district":"Пейя","type":"вилла","bedrooms":[2, 3],"price_from":2045000,"price_to":2045000,"ready":"Q1/2027","link":"https://t.me/zats_denis/954","desc":"📍 Пафос, Пейя Приватный курортный комплекс из 30 вилл в средиземноморском стиле. Закрытая территория, продуманная архитектура, river-style бассейн 40м и инфраструктура для жизни, отдыха и инвестиций. ✅ Входит в цену: • Частный или общий бассейн • Лан"},
    {"id":962,"title":"Готовая трёхэтажная вилла с лифтом и бассейном на крыше внури городской инфрастр","city":"Пафос","district":"","type":"вилла","bedrooms":[4],"price_from":1350000,"price_to":1350000,"ready":"Готово","link":"https://t.me/zats_denis/962","desc":"📍 Пафос, Старый город Объект расположен в окружении лучших ресторанов города, магазинов, школ и детских садов. Идеально подойдет для комфортной жизни большой семьи. ✅ Входит в цену: • Отделка мрамор • Кухонная мебель"},
    {"id":974,"title":"Продажа последней виллы с прямым видом на море на этапе строительства в Пафосе","city":"Пафос","district":"","type":"вилла","bedrooms":[3],"price_from":1010500,"price_to":1010500,"ready":"Q1/2027","link":"https://t.me/zats_denis/974","desc":"📍 Пафос, Гераскипу Приватный дом в составе закрытого комплекса. Тихое место в близи всей необходимой инфраструктуры и магазинов. Отлично подойдет для семейной жизни ✅ Входит в цену: • Smart Home • Теплый пол"},
    {"id":1005,"title":"Продажа последних вилл в приватном комплексе на холмах с панорамными видами","city":"Лимассол","district":"Гермасоя","type":"вилла","bedrooms":[3],"price_from":1020000,"price_to":1020000,"ready":"Уточняйте","link":"https://t.me/zats_denis/1005","desc":"📍 Лимассол, Гермасоя Комплекс из 6 вилл в тихом зелёном районе на возвышенности. Приватность, вид на море и быстрый доступ к городу — до пляжей, инфраструктуры и центра 10 минут на машине. Формат — низкая плотность застройки и спокойное окружение ✅ В"},
    {"id":1014,"title":"Готовая вилла с панорамным видом на море и город","city":"Лимассол","district":"Агиос Тихонас","type":"вилла","bedrooms":[3],"price_from":1400000,"price_to":1400000,"ready":"Готово","link":"https://t.me/zats_denis/1014","desc":"📍 Лимассол, Агиос Тихонас Современный поселок в престижном районе с видом на море и холмы. Низкая плотность застройки, приватность и быстрый доступ к ключевой инфраструктуре города ✅ Входит в цену: • VRV климат • Теплый пол"}
]

CITY_KEYWORDS = {
    "Лимассол": ["лимассол", "limassol"],
    "Пафос":    ["пафос", "paphos", "полис", "хлорака", "эмпа", "като пафос", "пейя", "coral bay"],
    "Никосия":  ["никосия", "nicosia"],
    "Ларнака":  ["ларнака", "larnaca", "larnaka"],
    "Айя-Напа": ["айя-напа", "ayia napa", "айя напа"],
    "Протарас": ["протарас", "protaras"],
}

TYPE_KEYWORDS = {
    "апартаменты": ["апартамент", "apartment", "студия", "studio", "квартир", "пентхаус", "penthouse"],
    "вилла":       ["вилла", "villa"],
    "таунхаус":    ["таунхаус", "townhouse"],
    "дом":         ["дом", "house"],
    "коммерция":   ["коммерц", "офис", "office", "commercial"],
}

DISTRICT_KEYWORDS = {
    "Лимассол": {
        "Марина":        ["марина", "marina"],
        "Мессагитония":  ["мессагитония", "messagitonia"],
        "Гермасоя":      ["гермасоя", "germasogeia"],
        "Закаки":        ["закаки", "zakaki"],
        "Центр":         ["центр", "centro", "исторический"],
        "Агиос Тихонас": ["агиос тихонас", "agios tychonas"],
        "Полемидия":     ["полемидия", "polemidia"],
    },
    "Пафос": {
        "Като Пафос": ["като пафос", "kato paphos"],
        "Хлорака":    ["хлорака", "chloraka"],
        "Эмпа":       ["эмпа", "emba"],
        "Пейя":       ["пейя", "peyia"],
        "Полис":      ["полис", "polis"],
        "Coral Bay":  ["coral bay", "корал бэй"],
    },
    "Никосия": {"Центр": ["центр"], "Строволос": ["строволос"], "Лакатамия": ["лакатамия"]},
    "Ларнака": {"Финикудес": ["финикудес"], "Арадиппу": ["арадиппу"], "Декелия": ["декелия"]},
}

def clean_price_str(s):
    s = s.strip().replace(" ", "").replace("\xa0", "")
    if re.match(r"^\d{1,3}(\.\d{3})+$", s):
        s = s.replace(".", "")
    else:
        s = re.sub(r"[.,](\d{3})$", r"\1", s)
        s = s.replace(".", "").replace(",", "")
    return s

def parse_price_from(text):
    patterns = [
        r"(?:студи[яю]|0\s*BR)[^\d€\n]*€\s*([\d\s.,]+)",
        r"1\s*(?:BR|сп\.?|спальн)[^\d€\n]*€\s*([\d\s.,]+)",
        r"от\s*€\s*([\d\s.,]+)",
        r"€\s*([\d\s.,]+)",
        r"от\s*([\d\s.,]+)\s*(?:евро|eur)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = clean_price_str(m.group(1))
            try:
                val = int(raw)
                if val < 1000: val *= 1000
                if 50000 < val < 50000000:
                    return val
            except: pass
    return None

def parse_price_to(text):
    prices = []
    for m in re.finditer(r"€\s*([\d\s.,]+)", text):
        raw = clean_price_str(m.group(1))
        try:
            val = int(raw)
            if val < 1000: val *= 1000
            if 50000 < val < 50000000:
                prices.append(val)
        except: pass
    return max(prices) if prices else None

def parse_bedrooms(text):
    beds = set()
    if re.search(r"студи|studio", text, re.IGNORECASE): beds.add(0)
    for m in re.finditer(r"(\d)\s*(?:BR|спальн|сп\.?\b|bedroom)", text, re.IGNORECASE):
        n = int(m.group(1))
        if 0 <= n <= 6: beds.add(n)
    for m in re.finditer(r"(\d)\+(\d)\s*спальн", text, re.IGNORECASE):
        beds.add(int(m.group(1)) + int(m.group(2)))
    return sorted(beds) if beds else [1]

def parse_city(text):
    tl = text.lower()
    for city, kws in CITY_KEYWORDS.items():
        for kw in kws:
            if kw in tl: return city
    return "Лимассол"

def parse_district(text, city):
    tl = text.lower()
    for dist, kws in DISTRICT_KEYWORDS.get(city, {}).items():
        for kw in kws:
            if kw in tl: return dist
    return ""

def parse_type(text):
    tl = text.lower()
    for pt, kws in TYPE_KEYWORDS.items():
        for kw in kws:
            if kw in tl: return pt
    return "апартаменты"

def parse_ready(text):
    m = re.search(r"Q[1-4][\/\s]\d{4}", text, re.IGNORECASE)
    if m: return m.group(0)
    m = re.search(r"\b(202[4-9]|203\d)\s*г", text)
    if m: return m.group(0)
    if re.search(r"готов|сдан|ready|completed|сдача", text, re.IGNORECASE): return "Готово"
    return "Уточняйте"

def parse_post(post_id, text, channel_username):
    if not text or len(text) < 30: return None
    if not re.search(r"евро|€|eur|спальн|вилл|апартамент|студи|таунхаус", text, re.IGNORECASE): return None
    price_from = parse_price_from(text)
    if not price_from: return None
    price_to = parse_price_to(text) or int(price_from * 2)
    if price_to < price_from: price_to = int(price_from * 2)
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    title_raw = lines[0] if lines else text[:60]
    title = re.sub(r"[^\w\s\-,.:!?()€«»]", "", title_raw).strip()
    if len(title) < 5 and len(lines) > 1:
        title = re.sub(r"[^\w\s\-,.:!?()€«»]", "", lines[1]).strip()
    title = title[:80]
    city = parse_city(text)
    district = parse_district(text, city)
    desc = " ".join(lines[1:6])
    desc = re.sub(r"\s+", " ", desc).strip()[:250]
    return {
        "id": post_id, "title": title, "city": city, "district": district,
        "type": parse_type(text), "bedrooms": parse_bedrooms(text),
        "price_from": price_from, "price_to": price_to,
        "ready": parse_ready(text),
        "link": "https://t.me/" + channel_username.lstrip("@") + "/" + str(post_id),
        "desc": desc,
    }

async def fetch_channel_posts(channel, last_id=0):
    new_props = []
    channel_name = channel.lstrip("@")
    urls_to_try = [
        "https://t.me/s/" + channel_name,
        "https://t.me/s/" + channel_name + "?before=1000",
    ]
    seen_ids = set()
    for url in urls_to_try:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            pattern = r'data-post="' + channel_name + r'/(\d+)".*?<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>'
            post_blocks = re.findall(pattern, html, re.DOTALL)
            for post_id_str, raw_html in post_blocks:
                post_id = int(post_id_str)
                if post_id in seen_ids: continue
                seen_ids.add(post_id)
                if post_id <= last_id: continue
                text = re.sub(r"<[^>]+>", " ", raw_html)
                text = re.sub(r"&nbsp;", " ", text)
                text = re.sub(r"&amp;", "&", text)
                text = re.sub(r"&#\d+;", "", text)
                text = re.sub(r"\s+", " ", text).strip()
                prop = parse_post(post_id, text, channel_name)
                if prop:
                    new_props.append(prop)
                    logger.info("Распарсен пост #%d: %s", post_id, prop["title"])
        except Exception as e:
            logger.error("Ошибка при получении %s: %s", url, e)
    return new_props

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
    if f.get("type") and f["type"] != "любой" and prop.get("type") != f["type"]: return False
    if f.get("city") and f["city"] != "любой" and prop.get("city") != f["city"]: return False
    if f.get("district") and f["district"] != "любой" and prop.get("district") != f["district"]: return False
    beds = f.get("bedrooms")
    if beds is not None and beds != -1 and beds not in prop.get("bedrooms", []): return False
    if f.get("price_max") is not None and f["price_max"] != 999999999 and prop.get("price_from", 0) > f["price_max"]: return False
    if f.get("price_min") is not None and f["price_min"] > 0 and prop.get("price_to", 999999999) < f["price_min"]: return False
    return True

def uniq(key):
    return sorted(set(p[key] for p in PROPERTIES if p.get(key)))

async def safe_edit(q, text, reply_markup=None):
    try:
        await q.edit_message_text(text, reply_markup=reply_markup, disable_web_page_preview=True)
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            raise

S_TYPE, S_CITY, S_DISTRICT, S_BEDROOMS, S_PRICE = range(5)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    kb = [
        [InlineKeyboardButton("Подобрать объект",  callback_data="search")],
        [InlineKeyboardButton("Все объекты",        callback_data="all")],
        [InlineKeyboardButton("Обновить из канала", callback_data="sync")],
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
    global PROPERTIES
    q = update.callback_query
    await q.answer()
    await safe_edit(q, "Проверяю канал на новые объекты...")
    existing_ids = {p["id"] for p in PROPERTIES}
    last_id = max(existing_ids) if existing_ids else 0
    new_props = await fetch_channel_posts(CHANNEL, last_id)
    added = 0
    for prop in new_props:
        if prop["id"] not in existing_ids:
            PROPERTIES.append(prop)
            existing_ids.add(prop["id"])
            added += 1
    if added:
        save_properties(PROPERTIES)
    msg = "Готово! Добавлено новых: {}\nВсего в базе: {}".format(added, len(PROPERTIES))
    await safe_edit(q, msg, reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton("Искать", callback_data="search"),
        InlineKeyboardButton("Все",    callback_data="all"),
    ]]))

async def back(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kb = [
        [InlineKeyboardButton("Подобрать объект",  callback_data="search")],
        [InlineKeyboardButton("Все объекты",        callback_data="all")],
        [InlineKeyboardButton("Обновить из канала", callback_data="sync")],
    ]
    await safe_edit(q, "В базе: {} объектов".format(len(PROPERTIES)), reply_markup=InlineKeyboardMarkup(kb))

async def search_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["filters"] = {}
    return await ask_type(q)

async def ask_type(q):
    kb = [[InlineKeyboardButton(t.capitalize(), callback_data="type_" + t)] for t in uniq("type")]
    kb.append([InlineKeyboardButton("Любой тип", callback_data="type_любой")])
    await safe_edit(q, "Тип объекта:", reply_markup=InlineKeyboardMarkup(kb))
    return S_TYPE

async def got_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chosen_type = q.data.replace("type_", "")
    ctx.user_data["filters"]["type"] = chosen_type
    if chosen_type and chosen_type != "любой":
        cities = sorted(set(p["city"] for p in PROPERTIES if p.get("city") and p.get("type") == chosen_type))
    else:
        cities = uniq("city")
    kb = [[InlineKeyboardButton(c, callback_data="city_" + c)] for c in cities]
    kb.append([InlineKeyboardButton("Любой город", callback_data="city_любой")])
    await safe_edit(q, "Город:", reply_markup=InlineKeyboardMarkup(kb))
    return S_CITY

async def got_city(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    val = q.data.replace("city_", "")
    ctx.user_data["filters"]["city"] = val
    chosen_city = val if val != "любой" else None
    chosen_type = ctx.user_data["filters"].get("type")
    chosen_type = chosen_type if chosen_type and chosen_type != "любой" else None
    districts = sorted(set(
        p["district"] for p in PROPERTIES
        if p.get("district")
        and (not chosen_city or p.get("city") == chosen_city)
        and (not chosen_type or p.get("type") == chosen_type)
    ))
    kb = [[InlineKeyboardButton(d, callback_data="dist_" + d)] for d in districts]
    kb.append([InlineKeyboardButton("Любой район", callback_data="dist_любой")])
    await safe_edit(q, "Район:", reply_markup=InlineKeyboardMarkup(kb))
    return S_DISTRICT

async def got_district(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["filters"]["district"] = q.data.replace("dist_", "")
    kb = [
        [InlineKeyboardButton("Студия",    callback_data="bed_0")],
        [InlineKeyboardButton("1 спальня", callback_data="bed_1")],
        [InlineKeyboardButton("2 спальни", callback_data="bed_2")],
        [InlineKeyboardButton("3 спальни", callback_data="bed_3")],
        [InlineKeyboardButton("4+ спален", callback_data="bed_4")],
        [InlineKeyboardButton("Не важно",  callback_data="bed_-1")],
    ]
    await safe_edit(q, "Спальни:", reply_markup=InlineKeyboardMarkup(kb))
    return S_BEDROOMS

async def got_bedrooms(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["filters"]["bedrooms"] = int(q.data.replace("bed_", ""))
    kb = [
        [InlineKeyboardButton("до 200 000 евро",  callback_data="price_0_200000")],
        [InlineKeyboardButton("200k - 400k евро", callback_data="price_200000_400000")],
        [InlineKeyboardButton("400k - 700k евро", callback_data="price_400000_700000")],
        [InlineKeyboardButton("700k - 1.5М евро", callback_data="price_700000_1500000")],
        [InlineKeyboardButton("от 1.5М евро",     callback_data="price_1500000_999999999")],
        [InlineKeyboardButton("Любой бюджет",     callback_data="price_0_999999999")],
    ]
    await safe_edit(q, "Бюджет:", reply_markup=InlineKeyboardMarkup(kb))
    return S_PRICE

async def got_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    parts = q.data.split("_")
    f = ctx.user_data["filters"]
    f["price_min"] = int(parts[1])
    f["price_max"] = int(parts[2])
    results = [p for p in PROPERTIES if match(p, f)]
    await send_results(q, results)
    return ConversationHandler.END

async def send_results(q, results):
    if not results:
        await safe_edit(
            q,
            "Ничего не найдено по этим критериям.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Новый поиск", callback_data="search")]])
        )
        return
    text = "Найдено: {} объект(ов)\n\n".format(len(results))
    kb = []
    for p in results[:15]:
        beds = ", ".join("студия" if b == 0 else str(b) + " сп." for b in p.get("bedrooms", []))
        text += (
            p["title"] + "\n"
            + p.get("city", "") + (", " + p.get("district", "") if p.get("district") else "") + "\n"
            + "Спальни: " + beds + "\n"
            + "Цена: от " + fmt(p["price_from"]) + "\n"
            + "Ключи: " + p.get("ready", "") + "\n\n"
        )
        short = p["title"][:38] + ("..." if len(p["title"]) > 38 else "")
        kb.append([InlineKeyboardButton("Открыть: " + short, url=p["link"])])
    if len(results) > 15:
        text += "...и ещё {} объектов. Уточните фильтры.\n".format(len(results) - 15)
    kb.append([
        InlineKeyboardButton("Новый поиск", callback_data="search"),
        InlineKeyboardButton("Все объекты", callback_data="all"),
    ])
    if len(text) > 4000:
        text = text[:4000] + "\n...(показаны не все)"
    await safe_edit(q, text, reply_markup=InlineKeyboardMarkup(kb))

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
