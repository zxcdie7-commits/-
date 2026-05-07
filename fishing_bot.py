import asyncio
import aiohttp
import json
from datetime import datetime

BOT_TOKEN = "8742673176:AAE923OkIarbF_obz8y5gXYnZaERNGiVe1o"
CHAT_ID = "-1001303633358"
CITY = "Pervomaysk,UA"
LAT = "47.9967"
LON = "30.8539"

async def get_weather():
    url = f"https://wttr.in/{LAT},{LON}?format=j1"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            current = data["current_condition"][0]
            weather = {
                "temp": current["temp_C"],
                "feels": current["FeelsLikeC"],
                "humidity": current["humidity"],
                "pressure": current["pressure"],
                "wind": current["windspeedKmph"],
                "desc": current["lang_ru"][0]["value"],
                "cloud": current["cloudcover"],
            }
            # tomorrow forecast
            tomorrow = data["weather"][1]
            weather["temp_min"] = tomorrow["mintempC"]
            weather["temp_max"] = tomorrow["maxtempC"]
            return weather

def analyze_fishing(weather):
    pressure = int(weather["pressure"])
    wind = int(weather["wind"])
    cloud = int(weather["cloud"])
    temp = int(weather["temp"])

    # Pressure analysis (normal ~760 mmHg, wttr gives hPa, 1 hPa ≈ 0.75 mmHg)
    pressure_mmhg = round(pressure * 0.75)

    # Peaceful fish score
    peaceful_score = 0
    if 745 <= pressure_mmhg <= 765:
        peaceful_score += 3
    elif pressure_mmhg < 740 or pressure_mmhg > 770:
        peaceful_score -= 2
    if wind < 15:
        peaceful_score += 2
    if 10 <= temp <= 25:
        peaceful_score += 2
    if cloud < 50:
        peaceful_score += 1

    # Predator fish score
    predator_score = 0
    if pressure_mmhg < 750:
        predator_score += 3  # falling pressure = predator active
    elif pressure_mmhg > 765:
        predator_score += 1
    if wind < 20:
        predator_score += 2
    if temp > 15:
        predator_score += 2
    if cloud > 30:
        predator_score += 1

    def score_to_emoji(score):
        if score >= 5:
            return "🟢 Отлично клюёт"
        elif score >= 3:
            return "🟡 Удовлетворительно"
        else:
            return "🔴 Плохо клюёт"

    overall = (peaceful_score + predator_score) / 2
    if overall >= 5:
        verdict = "ЕДЕМ ✅"
    elif overall >= 3:
        verdict = "МОЖНО ПОПРОБОВАТЬ 🟡"
    else:
        verdict = "ЛУЧШЕ ОСТАТЬСЯ ДОМА 🔴"

    # Pressure trend text
    if pressure_mmhg < 748:
        pressure_trend = "↘ низкое"
        comment = "Давление низкое — хищник активен, мирная рыба вялая. Берите спиннинг!"
    elif pressure_mmhg > 765:
        pressure_trend = "↗ высокое"
        comment = "Давление высокое — мирная рыба у дна. Попробуйте донку или фидер."
    else:
        pressure_trend = "→ норма"
        comment = "Давление в норме — хороший клёв у мирной рыбы. Поплавок или фидер."

    return {
        "pressure_mmhg": pressure_mmhg,
        "pressure_trend": pressure_trend,
        "peaceful": score_to_emoji(peaceful_score),
        "predator": score_to_emoji(predator_score),
        "verdict": verdict,
        "comment": comment,
    }

async def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
        async with session.post(url, json=payload) as resp:
            return await resp.json()

async def send_fishing_report():
    try:
        weather = await get_weather()
        analysis = analyze_fishing(weather)

        days_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        months_ru = ["января", "февраля", "марта", "апреля", "мая", "июня",
                     "июля", "августа", "сентября", "октября", "ноября", "декабря"]
        now = datetime.now()
        day_name = days_ru[now.weekday()]
        date_str = f"{now.day} {months_ru[now.month - 1]}"

        message = f"""🎣 *Рыбалка сегодня — Первомайск*

📅 {day_name}, {date_str}
🌡 {weather['temp']}°C (ощущается {weather['feels']}°C)
🌤 {weather['desc']}
💨 Ветер: {weather['wind']} км/ч
💧 Влажность: {weather['humidity']}%

🔵 Давление: {analysis['pressure_mmhg']} мм рт.ст. {analysis['pressure_trend']}

🐟 Мирная рыба: {analysis['peaceful']}
🦈 Хищник: {analysis['predator']}

📊 Общая оценка: *{analysis['verdict']}*

💬 _{analysis['comment']}_"""

        result = await send_message(message)
        print(f"Sent: {result}")
    except Exception as e:
        print(f"Error: {e}")

async def scheduler():
    while True:
        now = datetime.now()
        # Run at 8:00 every day
        if now.hour == 8 and now.minute == 0:
            await send_fishing_report()
            await asyncio.sleep(60)  # wait 1 min to avoid double send
        await asyncio.sleep(30)  # check every 30 seconds

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(send_fishing_report())
    else:
        asyncio.run(scheduler())
