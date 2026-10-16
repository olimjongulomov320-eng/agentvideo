# -*- coding: utf-8 -*-
"""Shared timeline for the GSP LAW demo film (single source of truth for AV)."""

# key, duration (s), RU voice-over text (temporary TTS), UZ narration (for reference/subtitles)
SCENES = [
    ("slate",   3.0,  None, None),
    ("hook",   12.0,
     "Каждый день тысячи людей ждут ответа от закона. Порой этот ответ приходит слишком поздно.",
     "Har kuni minglab odam qonundan javob kutadi. Ba'zida bu javob juda kech keladi."),
    ("founder",24.0,
     "2010 год, Ташкент. Адвокат Абдуллох Содик вместе с партнёрами основывает фирму. "
     "Она получает имя «Gulyamov, Sadikov and Partners». В 2011 году начинается практика, "
     "а в 2012-м фирма получает признание в своей сфере.",
     "2010-yil, Toshkent. Advokat Abdulloh Sodiq o'z hamkorlari bilan firma asos soladi. "
     "Firma «Gulyamov, Sadikov and Partners» deb ataladi. 2011-yilda amaliyot boshlanadi, "
     "2012-yilda esa u o'z yo'nalishida tan olinadi."),
    ("practice",18.0,
     "Они выбирают узкое, но непростое направление: экономические споры, корпоративное право, "
     "IT и киберправо. Одной из первых в Узбекистане фирма открывает услуги по исламскому праву и киберправу.",
     "Ular tor, ammo qiyin yo'nalishni tanlaydi: iqtisodiy nizolar, korporativ huquq, IT va kiberhuquq. "
     "O'zbekistonda birinchilardan bo'lib firma Islom huquqi va kiberhuquq xizmatlarini yo'lga qo'yadi."),
    ("intl",    18.0,
     "Идут годы. В 2024 году фирма начинает партнёрство с китайской юридической фирмой Tahota "
     "и участвует в международном саммите по исламским финансам. Доверие выходит за пределы Узбекистана.",
     "Yillar o'tadi. 2024-yilda firma Xitoyning Tahota yuridik firmasi bilan hamkorlikni boshlaydi "
     "va xalqaro islom moliyasi sammitida qatnashadi. Ishonch O'zbekiston chegarasidan tashqariga chiqadi."),
    ("wakil",   28.0,
     "Но остаётся один вопрос: почему правовые знания доходят так медленно? "
     "В 2026 году лидер фирмы Абдуллох Содик решает построить ответ сам. "
     "Он участвует в создании «Wakil AI» — правового ИИ на узбекском языке, "
     "который привязывает каждый ответ к источнику lex.uz. "
     "Система входит в реестр Stanford CodeX и представлена в Академии правосудия.",
     "Ammo bitta savol qoladi: nega huquqiy bilim shunchalik sekin yetib boradi? "
     "2026-yilda firma rahbari Abdulloh Sodiq o'zi javob qurishga kirishadi. "
     "U «Wakil AI» — o'zbek tilida ishlaydigan va har bir javobni lex.uz manbasiga bog'laydigan "
     "huquqiy sun'iy intellektni yaratishda qatnashadi. Tizim Stanford CodeX reyestriga kiradi "
     "va Adliya akademiyasida taqdim etiladi."),
    ("people",  16.0,
     "Технология ускоряет работу. Но доверие строит человек — "
     "команда адвокатов, для которой важен каждый клиент.",
     "Texnologiya ishni tezlashtiradi. Lekin ishonchni odam quradi — "
     "har bir mijoz uchun mas'uliyatni his qiladigan advokatlar jamoasi."),
    ("office",  18.0,
     "20 октября 2026 года. Фирма переезжает на новый адрес. "
     "Это не просто стены — это пространство для следующего этапа.",
     "2026-yil 20-oktyabr. Firma yangi manzilga ko'chadi. "
     "Bu shunchaki yangi devorlar emas — bu keyingi bosqich uchun maydon."),
    ("closing", 12.0,
     "С 2010 года — опыт. Сегодня — технологии. Завтра — будущее права Узбекистана. "
     "Gulyamov, Sadikov and Partners. Работа продолжается.",
     "2010-yildan buyon — tajriba. Bugun — texnologiya. Ertaga — O'zbekiston huquqining kelajasi. "
     "Gulyamov, Sadikov and Partners. Ish davom etadi."),
]

TRANSITION = 0.7           # crossfade seconds
FPS = 30

def total_duration():
    return sum(s[1] for s in SCENES) - (len(SCENES) - 1) * TRANSITION

def scene_starts():
    """Approximate start time of each scene in the final crossfaded timeline."""
    starts, acc = [], 0.0
    for i, (k, d, _, _) in enumerate(SCENES):
        starts.append(acc)
        acc += d - TRANSITION
    return starts

if __name__ == "__main__":
    print("total:", round(total_duration(), 2), "s")
    for (k, d, _, _), s in zip(SCENES, scene_starts()):
        print(f"  {k:9s} dur={d:4.1f} start={s:6.2f} end={s+d:6.2f}")
