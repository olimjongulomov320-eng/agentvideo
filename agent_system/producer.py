# -*- coding: utf-8 -*-
"""producer.py — the documents a videographer and editor need (ТЗ §5, §7, §10).

Three operator-facing files, written in Russian because that is the working
language of the brief:

* ``source_access_plan.md`` — which sources were read, which are blocked and
  exactly how the owner can hand each one over (ТЗ §3, step 1);
* ``archive_register.md`` / ``.csv`` — achievements and events, story
  candidates, media, quotes, key people, and everything that needs confirmation
  or permission, each rated for historical / emotional / professional / visual
  value (ТЗ §5);
* ``production_brief.md`` — scene-by-scene visuals, archive material, shoot list
  for the new office, music and montage notes, the closing line, a spoken-time
  check against 2–2.5 minutes and an automatic final verification (ТЗ §7, §10).

Nothing here invents a fact: every row is taken from the evidence ledger, the
extracted facts or a file that was actually supplied.
"""
import csv
import io
import json
import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

TARGET_MIN_SEC, TARGET_MAX_SEC = 120, 150
# Spoken words per second, a comfortable documentary pace per language.
SPEECH_RATE = {"uz": 2.0, "ru": 2.4, "en": 2.5}

VALUE_LABEL = {"historical": "историческая", "emotional": "эмоциональная",
               "professional": "профессиональная", "visual": "визуальная"}
MEDIA_EXT = {".jpg": "фото", ".jpeg": "фото", ".png": "фото", ".heic": "фото",
             ".mp4": "видео", ".mov": "видео", ".mp3": "аудио", ".m4a": "аудио",
             ".wav": "аудио", ".pdf": "документ", ".docx": "документ", ".txt": "текст",
             ".json": "экспорт переписки", ".html": "экспорт переписки",
             ".srt": "расшифровка", ".vtt": "расшифровка"}


def archive_dir() -> str:
    return os.environ.get("AGENT_ARCHIVE_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "archive-input")


def _write(path: str, text: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def _cell(text: Any, n: int = 160) -> str:
    return " ".join(str(text or "").split()).replace("|", "/")[:n]


# ============================================================ access plan
_HOW_TO = {
    "facebook": ("Страница/личный профиль основателя закрыты входом.",
                 "Владелец аккаунта: Настройки → «Ваша информация в Facebook» → "
                 "«Скачать информацию» (формат JSON, период «За всё время», включить "
                 "публикации, фото, видео). Архив передать ботом как файл или положить в "
                 "`archive-input/`. Допустимы и скриншоты отдельных публикаций с датами."),
    "instagram": ("Публикации и Reels не читаются без входа.",
                  "Владелец аккаунта: Настройки → «Центр аккаунтов» → «Ваша информация и "
                  "разрешения» → «Скачать вашу информацию» (JSON). Либо передать вручную "
                  "лучшие фото/видео с датами и подписями."),
    "telegram": ("Публичный канал читается (последние публикации); закрытые чаты и группы — нет.",
                 "Telegram Desktop → открыть чат/канал → меню ⋮ → «Экспорт истории чата» "
                 "(формат JSON, с фото и файлами). Личные переписки использовать только с "
                 "согласия всех участников и только те, что владелец выберет сам."),
    "youtube": ("Видео канала не просматриваются автоматически.",
                "Передать ссылки на 3–5 важных видео (выступления, интервью, мероприятия) "
                "или скачанные файлы с указанием даты и сюжета."),
}


def source_access_plan(firm: str, research: Any) -> str:
    social: Dict[str, str] = {}
    for c in research.claims:
        m = re.match(r"Social: (\w+) \| (\S+)", c.text or "")
        if m:
            social[m.group(1)] = m.group(2)
    state_ru = {"INSPECTED": "✅ прочитан", "INACCESSIBLE": "🔒 закрыт (вход/ограничение)",
                "ERROR": "⚠️ ошибка доступа", "SKIPPED": "— пропущен"}
    L: List[str] = ["# План доступа к источникам — %s" % firm, "",
                    "Что система уже прочитала сама, что недоступно и **как именно "
                    "передать недостающие материалы**. Система не предполагает доступа "
                    "к личным аккаунтам и перепискам: только то, что владелец передаст.", "",
                    "## 1. Уже прочитано / проверено", "",
                    "| № | Источник | Тип | Статус | Примечание |", "|---|---|---|---|---|"]
    for s in research.sources:
        L.append("| %s | %s | %s | %s | %s |" % (
            s.id, _cell(s.url, 70), s.kind, state_ru.get(s.state, s.state), _cell(s.note, 80)))
    L += ["", "## 2. Что нужно передать и как", "",
          "| Источник | Ссылка (найдена автоматически) | Что с доступом | Как передать |",
          "|---|---|---|---|"]
    for net in ("facebook", "instagram", "telegram", "youtube"):
        status, how = _HOW_TO[net]
        L.append("| %s | %s | %s | %s |" % (net.capitalize(), social.get(net, "— не найдена, укажите"),
                                            status, how))
    L += ["| Личный архив основателя | — | Не подключён | Положить файлы в папку `archive-input/` "
          "(подпапки приветствуются: `photos-early/`, `documents/`) или отправить боту как "
          "документ. К каждому файлу — год и что/кто изображён, и разрешение на публичное "
          "использование (разрешено / нужно согласие / закрыто). |",
          "| СМИ и публикации о фирме | — | Независимый поиск не выполнялся (поисковый "
          "сервис не подключён) | Прислать ссылки на интервью, статьи, упоминания; система "
          "включит их как отдельные источники и сможет *подтвердить* факты с сайта. |",
          "| Интервью с управляющим партнёром и партнёрами | см. `interviews/` | Вопросники "
          "готовы | Провести разговор, записать (аудио/видео) или конспектировать; "
          "прислать расшифровку (SRT/VTT/TXT) или запись. Расшифровка считается словами "
          "человека, а не доказательством факта. |", ""]
    inaccessible = [s for s in research.sources if s.state in ("INACCESSIBLE", "ERROR")]
    L += ["## 3. Итог", "",
          "Заблокировано источников: **%d**. Пока они не переданы, события из них не попадут "
          "в хронологию, а соответствующие сцены ролика будут исключены, а не придуманы."
          % len(inaccessible), ""]
    return "\n".join(L)


# ============================================================ archive register
def _media_inventory() -> List[Dict[str, str]]:
    base = archive_dir()
    rows: List[Dict[str, str]] = []
    if not os.path.isdir(base):
        return rows
    for root, _dirs, files in os.walk(base):
        for name in sorted(files):
            ext = os.path.splitext(name)[1].lower()
            if name.startswith(".") or name.lower() == "readme.md":
                continue
            rows.append({"file": os.path.relpath(os.path.join(root, name), base),
                         "kind": MEDIA_EXT.get(ext, "файл")})
    return rows[:60]


def build_register(research: Any, facts: Any = None) -> Dict[str, List[Dict[str, Any]]]:
    """Group everything the ledger and facts hold into the ТЗ §5 sections."""
    reg: Dict[str, List[Dict[str, Any]]] = {
        "achievements": [], "stories": [], "media": [], "quotes": [], "people": [],
        "permissions": []}
    seen_people = set()
    for c in research.claims:
        t = c.text or ""
        base = {"id": c.id, "source": c.source_url, "evidence": c.evidence_class,
                "date": c.source_date or c.event_date or ""}
        if t.startswith("Team profile: "):
            bits = [b.strip() for b in t[14:].split(" | ")]
            if bits[0] not in seen_people and len(bits) >= 4:
                seen_people.add(bits[0])
                reg["people"].append(dict(base, name=bits[0], role=bits[1], specialties=bits[2],
                                          experience=bits[3], value=["professional"]))
                reg["permissions"].append(dict(base, item="Имя и портрет: %s" % bits[0],
                                               need="согласие человека на использование имени и фото"))
        elif t.startswith("Team photo: ") and " | " in t:
            name, _s, url = t[12:].partition(" | ")
            reg["media"].append(dict(base, title="Портрет: %s" % name, where=url,
                                     kind="фото", value=["visual", "professional"],
                                     permission="опубликовано на сайте фирмы; подтвердить"))
        elif t.startswith("Quote: ") and " | " in t:
            who, _s, text = t[7:].partition(" | ")
            reg["quotes"].append(dict(base, who=who, text=text, value=["emotional", "professional"],
                                      permission="опубликована на сайте от первого лица; "
                                                 "согласовать с автором"))
        elif t.startswith("Social: "):
            net, _s, url = t[8:].partition(" | ")
            reg["media"].append(dict(base, title="Канал %s" % net, where=url, kind="архив соцсети",
                                     value=["historical", "emotional", "visual"],
                                     permission="содержимое не прочитано — нужен экспорт"))
        elif c.relevance == "case_figure" or t.startswith("Case: "):
            reg["achievements"].append(dict(base, title=_cell(t, 200), kind="дело (клиентская тайна)",
                                            value=["professional"]))
            reg["permissions"].append(dict(base, item=_cell(t, 120),
                                           need="адвокатская тайна: согласие клиента и проверка "
                                                "правомерности до любого использования"))
        elif c.relevance == "statistic_or_superlative":
            reg["achievements"].append(dict(base, title=_cell(t, 200), kind="показатель фирмы",
                                            value=["professional"]))
        elif t.startswith("News: "):
            reg["stories"].append(dict(base, title=_cell(t[6:], 200), kind="публикация/упоминание",
                                       value=["professional", "historical"]))
        elif "t.me/s/" in (c.source_url or "") and c.relevance == "statement":
            reg["stories"].append(dict(base, title=_cell(t, 200), kind="событие (Telegram)",
                                       value=["historical", "emotional", "visual"]))
            if re.search(r"(?i)lavha|видео|video|foto|фото", t):
                reg["media"].append(dict(base, title="Материалы события: " + _cell(t, 80),
                                         where=c.source_url, kind="фото/видео мероприятия",
                                         value=["emotional", "visual", "historical"],
                                         permission="запросить оригиналы у организатора"))
    for item in _media_inventory():
        reg["media"].append({"id": "—", "title": item["file"], "where": "archive-input/",
                             "kind": item["kind"], "value": ["historical", "visual"],
                             "evidence": "UNVERIFIED", "date": "",
                             "permission": "не указано — владельцу отметить: разрешено / "
                                           "нужно согласие / закрыто"})
    return reg


def _vals(v: Sequence[str]) -> str:
    return ", ".join(VALUE_LABEL.get(x, x) for x in v)


def archive_register_md(firm: str, reg: Dict[str, List[Dict[str, Any]]]) -> str:
    L = ["# Реестр исторических материалов — %s" % firm, "",
         "Каждая строка взята из реестра доказательств или переданного файла. "
         "«Ценность» — предложение для ролика (историческая / эмоциональная / "
         "профессиональная / визуальная), не факт.", ""]

    def table(title, rows, head, cols):
        L.extend(["## " + title, ""])
        if not rows:
            L.extend(["_Пока ничего не найдено — см. `source_access_plan.md`._", ""])
            return
        L.append("| " + " | ".join(head) + " |")
        L.append("|" + "---|" * len(head))
        for r in rows:
            L.append("| " + " | ".join(_cell(f(r), 110) for f in cols) + " |")
        L.append("")

    table("1. Достижения и показатели фирмы", reg["achievements"],
          ["ID", "Что", "Тип", "Достоверность", "Ценность"],
          [lambda r: r["id"], lambda r: r["title"], lambda r: r["kind"],
           lambda r: r["evidence"], lambda r: _vals(r["value"])])
    table("2. Кандидаты в истории и события", reg["stories"],
          ["ID", "Что", "Дата", "Тип", "Достоверность", "Ценность"],
          [lambda r: r["id"], lambda r: r["title"], lambda r: r["date"], lambda r: r["kind"],
           lambda r: r["evidence"], lambda r: _vals(r["value"])])
    table("3. Фото, видео и архивные материалы", reg["media"],
          ["Материал", "Где", "Тип", "Ценность", "Разрешение"],
          [lambda r: r["title"], lambda r: r["where"], lambda r: r["kind"],
           lambda r: _vals(r["value"]), lambda r: r["permission"]])
    table("4. Цитаты и выступления", reg["quotes"], ["Кто", "Текст", "Ценность", "Разрешение"],
          [lambda r: r["who"], lambda r: r["text"], lambda r: _vals(r["value"]),
           lambda r: r["permission"]])
    table("5. Ключевые участники истории", reg["people"],
          ["Имя", "Роль", "Специализация", "Опыт (по данным фирмы)"],
          [lambda r: r["name"], lambda r: r["role"], lambda r: r["specialties"],
           lambda r: r["experience"]])
    table("6. Требуется подтверждение или разрешение", reg["permissions"],
          ["Что", "Что нужно сделать"], [lambda r: r["item"], lambda r: r["need"]])
    return "\n".join(L)


def archive_register_csv(reg: Dict[str, List[Dict[str, Any]]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["section", "id", "title", "date", "kind", "source", "evidence", "value",
                "permission"])
    for section, rows in reg.items():
        for r in rows:
            w.writerow([section, r.get("id", ""),
                        r.get("title") or r.get("name") or r.get("who") or r.get("item", ""),
                        r.get("date", ""), r.get("kind", r.get("role", "")), r.get("source", ""),
                        r.get("evidence", ""), _vals(r.get("value", [])),
                        r.get("permission", r.get("need", ""))])
    return buf.getvalue()


def write_research_package(job_dir: str, firm: str, research: Any, facts: Any = None
                           ) -> List[str]:
    reg = build_register(research, facts)
    return [
        _write(os.path.join(job_dir, "source_access_plan.md"), source_access_plan(firm, research)),
        _write(os.path.join(job_dir, "archive_register.md"), archive_register_md(firm, reg)),
        _write(os.path.join(job_dir, "archive_register.csv"), archive_register_csv(reg)),
    ]


# ============================================================ production brief
def speech_seconds(text: str, lang: str) -> float:
    words = len(re.findall(r"\w+", text or "", re.UNICODE))
    return words / SPEECH_RATE.get((lang or "en")[:2], 2.4)


def timing_check(scenes: List[Dict[str, Any]], lang: str, total_sec: float
                 ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    rows = []
    for s in scenes:
        need = speech_seconds(s.get("narration", ""), lang)
        room = float(s["dur"]) - 1.0
        status = "перегрузка" if need > room else ("пауза" if need < 0.35 * float(s["dur"]) else "ок")
        rows.append({"id": s["id"], "key": s["key"], "dur": float(s["dur"]), "speech": need,
                     "status": status})
    runtime = sum(float(s["dur"]) for s in scenes)
    summary = {"runtime": runtime, "speech": sum(r["speech"] for r in rows),
               "in_range": TARGET_MIN_SEC <= runtime <= TARGET_MAX_SEC,
               "requested": total_sec}
    return rows, summary


_SCENE_PLAN = {
    "hook": ("Тёмный город, окна зажигаются одно за другим; медленный наезд на здание суда/"
             "центр города. Первая фраза — человеческая потребность, не реклама.",
             "Архивный кадр первого офиса или первой публикации фирмы, если найдётся.",
             "Пустая улица Ташкента на рассвете; руки закрывают папку с делом.",
             "тихо, одиночная нота фортепиано; монтаж медленный (6–8 с на кадр)"),
    "origin": ("Таймлайн: число лет растёт и приводит к сегодняшнему дню.",
               "Самая ранняя публикация/фото фирмы; документ о регистрации — только с разрешения.",
               "—", "добавляются струнные, ритм 70→85 bpm"),
    "practice": ("Направления практики как последовательность иллюстраций/иконок.",
                 "Фото из реальных мероприятий по этим направлениям (конференции, выступления).",
                 "Руки за клавиатурой (IT-право), подписание договора, папки дел.",
                 "ритм ускоряется, смена кадров каждые 3–4 с"),
    "achievements": ("Крупный показатель и поясняющая строка; подача «по данным фирмы».",
                     "Фото клиентов/дел **не использовать** без письменного согласия.",
                     "Командный план в рабочей обстановке.", "музыка достигает первой кульминации"),
    "people": ("Портреты партнёров и команды.",
               "Утверждённые портреты (проверить разрешения), групповое фото.",
               "Групповой кадр команды в новом офисе; индивидуальные портреты в едином свете.",
               "тёплый, человеческий момент; музыка мягче"),
    "partner": ("Портрет партнёра, имя, роль, специализация; закадровый текст — только то, что "
                "подтверждено профилем/интервью.",
                "Личные архивные фото партнёра (первые дела, выступления), цитата из интервью — "
                "после согласования.", "Партнёр за рабочим столом, у окна, за разговором с коллегой.",
                "спокойный ритм, 5–6 с на кадр"),
    "office": ("Адрес/карта и кадры нового офиса — как символ достигнутого уровня.",
               "—", "См. список съёмки ниже: фасад, ресепшн, переговорная, кабинеты, детали.",
               "кульминация и разрешение, музыка раскрывается"),
    "closing": ("Название фирмы и финальная фраза на светлом рассвете.", "Логотип (оригинал из "
                "фирменного стиля).", "Финальный кадр: вход в новый офис, открывается дверь.",
                "музыка затихает на последней фразе, 2 с тишины"),
}

_SHOOT_LIST = [
    ("Фасад и вход", "вывеска с названием, дверь, утренний свет", "closing, office"),
    ("Ресепшн", "приветствие гостя, детали отделки, логотип на стене", "office"),
    ("Переговорная", "стол, кресла, свет из окна, руки с документами", "office, practice"),
    ("Кабинеты партнёров", "рабочее место, кодексы, перо, ноутбук; партнёр в кадре", "partner"),
    ("Команда", "групповой план и индивидуальные портреты, один свет и фон, 4K", "people, partner"),
    ("Окно/вид на город", "Ташкент из окна офиса, смена света", "hook, office"),
    ("Символические детали", "рукопожатие, подпись, закрывается папка, открывается дверь", "closing"),
    ("Церемония открытия", "разрезание ленты, гости, выступление управляющего партнёра, "
                           "реакции зала", "office, closing"),
    ("Интервью", "управляющий партнёр и партнёры на фоне офиса, 2 камеры, "
                 "петличный микрофон — 5–7 минут на человека", "partner, origin"),
]

_CLOSERS = {
    "uz": ["{n} yillik yo'l. Yangi ofis — yangi bosqich.",
           "Ishonch yillar bilan quriladi. Bugun u yangi manzilda."],
    "ru": ["{n} лет пути. Новый офис — новый этап.",
           "Доверие строится годами. Сегодня оно — по новому адресу."],
    "en": ["{n} years on the road. A new office — a new chapter.",
           "Trust is built over years. Today it has a new address."],
}


def production_brief(firm: str, facts: Any, scenes: List[Dict[str, Any]], lang: str,
                     total_sec: float, omitted: List[Dict[str, Any]],
                     concept: Optional[Dict[str, Any]] = None) -> str:
    lang = (lang or "en")[:2]
    rows, tsum = timing_check(scenes, lang, total_sec)
    L = ["# Производственное задание — %s" % firm, "",
         "Основа для видеографа и монтажёра. Язык ролика: **%s**. Длительность по сценарию: "
         "**%.0f с**, целевая — 120–150 с." % (lang.upper(), tsum["runtime"]), ""]
    if concept:
        L += ["**Концепция:** %s — %s" % (concept.get("title", ""), concept.get("central_idea", "")), ""]
    L += ["## 1. Посценовой план", "",
          "| Сцена | Время | Текст диктора | Визуал | Архивные материалы | Съёмка |",
          "|---|---|---|---|---|---|"]
    for s in scenes:
        base = re.sub(r"\d+$", "", s["key"])
        vis, arch, shoot, _music = _SCENE_PLAN.get(base, ("Фон и заголовок сцены.", "—", "—", ""))
        if s.get("portraits"):
            arch = "Портреты: %s. %s" % (", ".join(p["name"] for p in s["portraits"]), arch)
        L.append("| %s %s | %.0f–%.0f с | %s | %s | %s | %s |" % (
            s["id"], base, s["start"], s["start"] + s["dur"], _cell(s["narration"], 140),
            _cell(vis, 120), _cell(arch, 120), _cell(shoot, 100)))
    if omitted:
        L += ["", "**Сцены, исключённые из-за отсутствия подтверждённых данных:** " +
              ", ".join("%s (%s)" % (o["key"], ", ".join(o["needs"])) for o in omitted), ""]
    L += ["", "## 2. Что снять в новом офисе", "",
          "| Что | Детали | Сцены |", "|---|---|---|"]
    for what, det, where in _SHOOT_LIST:
        L.append("| %s | %s | %s |" % (what, det, where))
    L += ["", "## 3. Музыка, монтаж, атмосфера", "",
          "- **Атмосфера:** солидно и тепло, без пафоса; уверенность в будущем, ощущение нового этапа.",
          "- **Музыка:** сдержанная кинематографичная — фортепиано и струнные, без вокала; "
          "динамика растёт от тишины к кульминации в сцене офиса и затихает на финальной фразе. "
          "Использовать только лицензированную музыку (синтезированная дорожка в демо — временная).",
          "- **Ритм монтажа:** вступление медленное (6–8 с на кадр), середина 3–5 с, кульминация "
          "быстрее, финал снова медленный.",
          "- **Переходы:** мягкие наплывы и затемнения; без эффектов, подчёркивающих «рекламность».",
          "- **Звук:** диктор спокойный, без пафоса; музыка приглушается под речью (ducking).",
          "- **Цвет:** тёмно-синий и золото фирменной палитры; единая цветокоррекция для интервью и офиса.",
          ""]
    n = (facts.get("years_experience") if facts else "") or ""
    n = n.rstrip("+")
    L += ["## 4. Финальная фраза", ""]
    closer = list(_CLOSERS.get(lang, _CLOSERS["en"]))
    for i, ph in enumerate(closer):
        if "{n}" in ph and not n:
            continue
        L.append("- %s" % ph.format(n=n))
    L += ["", "Выбрать одну; она связывает историю фирмы с открытием нового офиса.", ""]
    L += ["## 5. Проверка хронометража (реальная, а не формальная)", "",
          "Темп речи: %.1f слова/с. Сумма речи **%.0f с** из %.0f с ролика." % (
              SPEECH_RATE.get(lang, 2.4), tsum["speech"], tsum["runtime"]), "",
          "| Сцена | Длина | Речь | Статус |", "|---|---|---|---|"]
    for r in rows:
        L.append("| %s %s | %.0f с | %.0f с | %s |" % (r["id"], r["key"], r["dur"], r["speech"], r["status"]))
    L.append("")
    if not tsum["in_range"]:
        L.append("⚠️ Длительность %.0f с вне диапазона 120–150 с." % tsum["runtime"])
    if tsum["speech"] < 0.5 * tsum["runtime"]:
        L.append("ℹ️ Речь занимает меньше половины ролика: оставшееся время закрывают музыка, "
                 "интервью и живые кадры — их нужно снять/получить (см. п. 2) или записать "
                 "интервью партнёров, чтобы расширить текст.")
    L += ["", "## 6. Автоматическая финальная проверка", ""]
    L += final_verification(scenes, facts, tsum, omitted)
    return "\n".join(L) + "\n"


def final_verification(scenes: List[Dict[str, Any]], facts: Any, tsum: Dict[str, Any],
                       omitted: List[Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    ok, warn = "✅", "⚠️"
    unsourced = [s["id"] for s in scenes if s["key"] in ("origin", "practice", "achievements",
                                                         "office") and not s.get("source")
                 and not s.get("source_id")]
    single = [s["id"] for s in scenes if s.get("evidence") == "SINGLE-SOURCE"]
    out.append("%s **Фактическая точность.** %s" % (
        warn if unsourced or single else ok,
        "Сцены без ссылки на источник: %s. " % ", ".join(unsourced) if unsourced else
        "Каждая фактическая сцена опирается на источник. ") +
        ("Сцены на данных самой фирмы (SINGLE-SOURCE): %s — формулировка «по данным фирмы», "
         "подтвердить интервью/документами." % ", ".join(single) if single else ""))
    names = [p["name"] for s in scenes for p in (s.get("portraits") or [])]
    out.append("%s **Конфиденциальность.** Клиентские дела, имена клиентов и закрытая переписка "
               "в ролик не включены. Портреты (%s) — получить согласие." % (
                   warn if names else ok, ", ".join(dict.fromkeys(names)) or "не используются"))
    arc = [s["key"] for s in scenes]
    need = ["hook", "closing"]
    out.append("%s **Драматургия.** Начало (hook) %s, развитие %d сцен, финал (closing) %s." % (
        ok if all(k in arc for k in need) else warn, "есть" if "hook" in arc else "нет",
        max(0, len(arc) - 2), "есть" if "closing" in arc else "нет"))
    out.append("%s **Длительность.** %.0f с (цель 120–150 с); речь %.0f с." % (
        ok if tsum["in_range"] else warn, tsum["runtime"], tsum["speech"]))
    if omitted:
        out.append("%s **Пробелы.** Исключены сцены: %s." % (
            warn, ", ".join(o["key"] for o in omitted)))
    return ["- " + x for x in out]


# ------------------------------------------------------------ concept document
def write_concepts_docx(path: str, firm: str, concepts: Sequence[Dict[str, Any]]) -> str:
    """Write the one Word file the operator reads: the concepts, nothing else."""
    from docx import Document

    doc = Document()
    doc.add_heading("Концепции презентационного фильма — %s" % firm, level=0)
    for c in concepts:
        title = "%s — %s%s" % (c.get("id", ""), c.get("title", ""),
                               " (рекомендуется)" if c.get("recommended") else "")
        doc.add_heading(title, level=1)
        if c.get("central_idea"):
            doc.add_paragraph(str(c["central_idea"]))
        for label, key in (("Сильные стороны", "strengths"), ("Слабые стороны", "weaknesses")):
            vals = c.get(key) or []
            if vals:
                doc.add_paragraph().add_run(label).bold = True
                for v in vals:
                    doc.add_paragraph(str(v), style="List Bullet")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    doc.save(path)
    return path
