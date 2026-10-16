#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_frames.py — Pillow frame renderer for the GSP LAW opening-film DEMO.

Renders one full 1920x1080 PNG per scene (per language) into demo/build/frames/.
All typography is drawn here (ffmpeg in this build has no drawtext/libfreetype).

Real assets used: custom logo (logo-full.png) and 15 team photographs.
Everything else (backgrounds, rules, mock UI) is drawn procedurally.

This is a DEMO / CONCEPT PREVIEW. Illustrative graphics are labelled as such.
"""
import os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops, ImageEnhance

# ---------------------------------------------------------------- paths
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # demo/
WEB  = os.path.join(ROOT, "assets", "web")
OUT  = os.path.join(ROOT, "build", "frames")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- brand (real CSS)
DARK   = (14, 45, 62)      # #0e2d3e
DARKER = (8, 27, 38)
NAVY   = (23, 67, 90)      # #17435a
GOLD   = (201, 169, 110)   # #c9a96e
GOLD_L = (232, 201, 138)   # #e8c98a
CREAM  = (248, 246, 241)   # #f8f6f1
TEXT   = (31, 41, 55)

W, H = 1920, 1080

# ---------------------------------------------------------------- fonts
def serif(size, bold=False, italic=False):
    if bold and italic: p = "Georgia Bold Italic.ttf"
    elif bold:          p = "Georgia Bold.ttf"
    elif italic:        p = "Georgia Italic.ttf"
    else:               p = "Georgia.ttf"
    return ImageFont.truetype("/System/Library/Fonts/Supplemental/" + p, size)

def sans(size, bold=False):
    return ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", size, index=1 if bold else 0)

# ---------------------------------------------------------------- helpers
def tracked_size(draw, text, font, tracking):
    w = 0
    for ch in text:
        w += draw.textlength(ch, font=font) + tracking
    return w - tracking if text else 0

def draw_tracked(draw, x, y, text, font, fill, tracking=0.0, anchor="la"):
    """Draw text with letter-spacing. y is the top; anchor 'la' (left) or 'ca' (centred on x)."""
    total = tracked_size(draw, text, font, tracking)
    cx = x - total / 2 if anchor == "ca" else x
    for ch in text:
        draw.text((cx, y), ch, font=font, fill=fill)
        cx += draw.textlength(ch, font=font) + tracking

def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if draw.textlength(t, font=font) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur); cur = wd
    if cur: lines.append(cur)
    return lines

def bg_gradient(c1=DARKER, c2=NAVY, vertical=True):
    """Smooth two-stop gradient with a soft radial gold glow."""
    if vertical:
        g = np.linspace(0, 1, H)[:, None]
        arr = (np.array(c1)[None, None, :] * (1 - g[:, :, None]) +
               np.array(c2)[None, None, :] * g[:, :, None])
        arr = np.repeat(arr, W, axis=1)
    else:
        g = np.linspace(0, 1, W)[None, :, None]
        arr = (np.array(c1)[None, None, :] * (1 - g) + np.array(c2)[None, None, :] * g)
        arr = np.repeat(arr, H, axis=0)
    im = Image.fromarray(arr.astype("uint8"), "RGB")
    # radial gold glow, upper area
    glow = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W*0.18, -H*0.55, W*0.82, H*0.55], fill=42)
    glow = glow.filter(ImageFilter.GaussianBlur(260))
    im = Image.composite(Image.new("RGB", (W, H), GOLD), im, glow.point(lambda v: int(v*0.30)))
    return im

def grain(im, amount=5.0):
    n = Image.effect_noise((W, H), 100).convert("L")
    n = n.point(lambda v: 128 + (v - 128) * (amount / 100.0))
    return Image.blend(im, ImageChops.overlay(im, n.convert("RGB")), 0.30)

def vignette(im, strength=0.45):
    vig = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(vig)
    d.ellipse([-W*0.35, -H*0.55, W*1.35, H*1.55], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(300))
    dark = ImageEnhance.Brightness(im).enhance(1 - strength)
    return Image.composite(im, dark, vig)

def rule(draw, cx, y, w=120, color=GOLD, th=2):
    draw.line([cx - w/2, y, cx + w/2, y], fill=color, width=th)

# ---------------------------------------------------------------- photo handling
def cover(img, size, anchor_y=0.40):
    tw, th = size
    w, h = img.size
    s = max(tw / w, th / h)
    nw, nh = int(math.ceil(w * s)), int(math.ceil(h * s))
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - tw) // 2
    top = int((nh - th) * anchor_y)
    top = max(0, min(top, nh - th))
    return img.crop((left, top, left + tw, top + th))

def grade(img, sat=0.86, contrast=1.06, navy_shadow=0.16, warm=0.06):
    """Unify found photos with a cinematic navy/gold grade."""
    img = ImageEnhance.Color(img).enhance(sat)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    arr = np.asarray(img).astype(np.float32) / 255.0
    lum = arr.mean(axis=2, keepdims=True)
    shadow = (1 - lum) ** 2 * navy_shadow
    arr[:, :, 2] += shadow[:, :, 0] * 0.9          # lift blues in shadows
    arr[:, :, 0] += shadow[:, :, 0] * 0.25
    hi = lum ** 2 * warm
    arr[:, :, 0] += hi[:, :, 0] * 0.10             # warm highlights
    arr[:, :, 1] += hi[:, :, 0] * 0.05
    arr = np.clip(arr, 0, 1)
    return Image.fromarray((arr * 255).astype("uint8"), "RGB")

def load_photo(name):
    return Image.open(os.path.join(WEB, "photos", name + ".jpeg")).convert("RGB")

def scrim(im, side="bottom", frac=0.55, color=DARKER):
    """Dark gradient scrim for text legibility."""
    ov = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(ov)
    if side == "bottom":
        for i in range(int(H*frac)):
            a = int(235 * (i / (H*frac))**1.4)
            d.line([0, H-i, W, H-i], fill=a)
    elif side == "left":
        for i in range(int(W*frac)):
            a = int(225 * (1 - i/(W*frac))**1.15)
            d.line([i, 0, i, H], fill=a)
    elif side == "right":
        for i in range(int(W*frac)):
            a = int(225 * (i/(W*frac))**1.15)
            d.line([W-i, 0, W-i, H], fill=a)
    ov = ov.filter(ImageFilter.GaussianBlur(40))
    return Image.composite(Image.new("RGB", (W, H), color), im, ov)

# ---------------------------------------------------------------- text blocks
def eyebrow(draw, x, y, text, color=GOLD, size=25, anchor="la", center=None):
    f = sans(size, bold=True)
    t = text.upper()
    if anchor == "ca":
        draw_tracked(draw, center, y, t, f, color, tracking=size*0.34, anchor="ca")
    else:
        draw_tracked(draw, x, y, t, f, color, tracking=size*0.34)

def headline(draw, x, y, lines, color=CREAM, size=76, center=None, leading=1.06):
    f = serif(size)
    yy = y
    for ln in lines:
        if center is not None:
            draw_tracked(draw, center, yy, ln, f, color, tracking=size*0.005, anchor="ca")
        else:
            draw.text((x, yy), ln, font=f, fill=color)
        yy += int(size * leading)
    return yy

def caption(draw, x, y, lines, size=31, color=(228, 226, 220), leading=1.42):
    f = sans(size)
    yy = y
    for ln in lines:
        draw.text((x, yy), ln, font=f, fill=color)
        yy += int(size * leading)
    return yy

def nore(draw, x, y, text, size=20, color=(150, 158, 164)):
    draw.text((x, y), text, font=sans(size), fill=color)

# ---------------------------------------------------------------- watermark
def watermark(im):
    d = ImageDraw.Draw(im, "RGBA")
    txt = "DEMO  ·  CONCEPT PREVIEW"
    f = sans(20, bold=True)
    w = d.textlength(txt, font=f)
    d.rectangle([W - w - 74, H - 66, W - 34, H - 30], outline=(201, 169, 110, 130), width=1)
    d.text((W - w - 54, H - 56), txt, font=f, fill=(201, 169, 110, 205))
    return im

# ================================================================ scenes
def scene_slate(lang):
    im = bg_gradient(DARKER, NAVY)
    d = ImageDraw.Draw(im)
    cx = W // 2
    eyebrow(d, 0, 300, "DEMO · " + ("KONSEPT PREVYU" if lang == "uz" else "КОНЦЕПТ-ПРЕВЬЮ"),
            color=GOLD, size=26, anchor="ca", center=cx)
    rule(d, cx, 356, 120)
    h = "YAKUNIY VIDEO EMAS" if lang == "uz" else "ЭТО НЕ ФИНАЛЬНОЕ ВИДЕО"
    headline(d, 0, 404, [h], color=CREAM, size=64, center=cx)
    lines = (["Bu — yakuniy mahsulot emas, konsept namunasi.",
              "Tasviriy materiallar va vaqtinchalik ovoz ishlatilgan.",
              "Ba'zi ma'lumotlar firma veb-saytidan — tasdiqlanishi kerak."]
             if lang == "uz" else
             ["Это образец концепции, а не финальный продукт.",
              "Использованы иллюстративные материалы и временный голос.",
              "Часть сведений — с сайта фирмы и требует подтверждения."])
    caption(d, 0, 560, [])  # no-op to keep pipeline uniform
    f = sans(30)
    yy = 566
    for ln in lines:
        draw_tracked(d, cx, yy, ln, f, (215, 213, 207), tracking=0, anchor="ca")
        yy += 48
    footer = "Gulyamov, Sadikov and Partners  ·  Yangi ofis  ·  20.10.2026" if lang == "uz" \
             else "Gulyamov, Sadikov and Partners  ·  Новый офис  ·  20.10.2026"
    nore(d, 0, 860, "")
    draw_tracked(d, cx, 852, footer, sans(24), GOLD_L, tracking=1.2, anchor="ca")
    return vignette(grain(im), 0.35)

def scene_hook(lang):
    im = bg_gradient(DARKER, (18, 54, 72))
    d = ImageDraw.Draw(im)
    # abstract "distance" motif: two vertical gold ticks with a gap
    for i in range(3):
        x = 300 + i*26
        d.line([x, 470, x, 610], fill=(201, 169, 110, 70), width=1)
    for i in range(3):
        x = W-300 - i*26
        d.line([x, 470, x, 610], fill=(201, 169, 110, 70), width=1)
    eyebrow(d, 0, 300, "TOSHKENT · 2026", color=GOLD, size=26, anchor="ca", center=W//2)
    h = ["Odam va qonun", "o'rtasidagi masofa"] if lang == "uz" else ["Расстояние между", "человеком и законом"]
    headline(d, 0, 380, h, color=CREAM, size=88, center=W//2)
    cap = (["Har kuni minglab odam qonundan javob kutadi.",
            "Ba'zida bu javob juda kech keladi."]
           if lang == "uz" else
           ["Каждый день тысячи людей ждут ответа от закона.",
            "Порой этот ответ приходит слишком поздно."])
    f = sans(31)
    yy = 660
    for ln in cap:
        draw_tracked(d, W//2, yy, ln, f, (222, 220, 214), tracking=0, anchor="ca")
        yy += 46
    return vignette(grain(im), 0.45)

def scene_founder(lang):
    im = bg_gradient(DARKER, NAVY, vertical=False)
    ph = grade(load_photo("abdulloh-sodiq"))
    ph = cover(ph, (760, 1080), anchor_y=0.22)
    im.paste(ph, (W-760, 0))
    im = scrim(im, "left", 0.62)
    im = scrim(im, "right", 0.30)
    d = ImageDraw.Draw(im)
    x = 150
    eyebrow(d, x, 250, "2010 · TOSHKENT", color=GOLD, size=26)
    rule(d, x+58, 306, 116)
    headline(d, x, 350, ["Boshlanish"] if lang == "uz" else ["Начало"], color=CREAM, size=96)
    cap = (["Advokat Abdulloh Sodiq o'z hamkorlari",
            "bilan firma asos soladi."]
           if lang == "uz" else
           ["Адвокат Абдуллох Содик вместе",
            "с партнёрами основывает фирму."])
    caption(d, x, 500, cap, size=32)
    # milestone chips
    miles = (["2011 — amaliyot boshlanadi", "2012 — o'z yo'nalishida tan olinadi"]
             if lang == "uz" else
             ["2011 — начинается практика", "2012 — признание в своей сфере"])
    yy = 640
    for m in miles:
        d.ellipse([x, yy+11, x+8, yy+19], fill=GOLD)
        draw_tracked(d, x+26, yy, m, sans(27), (232, 200, 138), tracking=0.6)
        yy += 46
    # name plate
    d.line([x, 830, x+520, 830], fill=(201, 169, 110, 150), width=1)
    draw_tracked(d, x, 856, "ABDULLOH SODIQ", sans(30, bold=True), CREAM, tracking=3.0)
    draw_tracked(d, x, 902, ("ASOSCHI · BOSHQARUVCHI SHERIK" if lang == "uz" else "ОСНОВАТЕЛЬ · УПРАВЛЯЮЩИЙ ПАРТНЁР"),
                 sans(21), GOLD, tracking=2.2)
    nore(d, x, 944, "portret: firma sayti (haqiqiy)" if lang == "uz" else "портрет: с сайта фирмы (реальный)", 18)
    return vignette(grain(im), 0.50)

def scene_practice(lang):
    im = bg_gradient(DARKER, (21, 63, 84))
    d = ImageDraw.Draw(im)
    eyebrow(d, 0, 214, "AMALIYOT" if lang == "uz" else "ПРАКТИКА", color=GOLD, size=26, anchor="ca", center=W//2)
    h = ["Tor, ammo qiyin yo'nalish"] if lang == "uz" else ["Узкое, но непростое направление"]
    headline(d, 0, 262, h, color=CREAM, size=70, center=W//2)
    items = (["Iqtisodiy nizolar", "Korporativ huquq", "IT va kiberhuquq"]
             if lang == "uz" else ["Экономические споры", "Корпоративное право", "IT и киберправо"])
    cols = 3
    colw = 460
    gap = 70
    total = cols*colw + (cols-1)*gap
    x0 = (W - total)//2
    for i, it in enumerate(items):
        cx = x0 + i*(colw+gap) + colw//2
        # card
        d.rectangle([x0 + i*(colw+gap), 430, x0 + i*(colw+gap)+colw, 690],
                    fill=(255, 255, 255, 0), outline=(201, 169, 110, 120), width=1)
        d.line([cx-40, 500, cx+40, 500], fill=GOLD, width=2)
        f = serif(40)
        draw_tracked(d, cx, 540, it, f, CREAM, tracking=0, anchor="ca")
    cap = (["O'zbekistonda birinchilardan bo'lib —",
            "Islom huquqi va kiberhuquq xizmatlari."]
           if lang == "uz" else
           ["Одной из первых в Узбекистане —",
            "исламское право и киберправо."])
    f = sans(30)
    yy = 770
    for ln in cap:
        draw_tracked(d, W//2, yy, ln, f, (222, 220, 214), tracking=0, anchor="ca")
        yy += 44
    nore(d, 0, 890, ""); 
    draw_tracked(d, W//2, 892, ("firmaning o'z bayonoti — mustaqil tasdiqlanmagan" if lang=="uz"
                               else "собственное утверждение фирмы — независимо не подтверждено"),
                 sans(19), (150, 158, 164), tracking=0.6, anchor="ca")
    return vignette(grain(im), 0.42)

def scene_intl(lang):
    im = bg_gradient(DARKER, (16, 48, 66))
    d = ImageDraw.Draw(im)
    # procedural globe motif (arcs) — illustrative
    cx, cy, r = 1480, 540, 300
    for rr, alpha in [(300, 70), (220, 55), (140, 45)]:
        d.ellipse([cx-rr, cy-rr, cx+rr, cy+rr], outline=(201,169,110, alpha), width=1)
    d.line([cx-360, cy, cx+360, cy], fill=(201,169,110,60), width=1)
    eyebrow(d, 150, 300, "2024 · XITOY" if lang == "uz" else "2024 · КИТАЙ", color=GOLD, size=26)
    rule(d, 208, 356, 116)
    h = ["Ishonch chegaradan", "tashqariga chiqadi"] if lang == "uz" else ["Доверие выходит", "за пределы страны"]
    headline(d, 150, 400, h, color=CREAM, size=80)
    cap = (["Xitoyning Tahota firmasi bilan hamkorlik va",
            "xalqaro islom moliyasi sammitida qatnashuv."]
           if lang == "uz" else
           ["Партнёрство с китайской фирмой Tahota и участие",
            "в международном саммите по исламским финансам."])
    caption(d, 150, 620, cap, size=31)
    d.rectangle([150, 740, 470, 792], outline=(201,169,110,150), width=1)
    draw_tracked(d, 174, 752, "2024 · TAHOTA", sans(24, bold=True), GOLD_L, tracking=2.0)
    nore(d, 150, 828, ("manba: firmaning o'zi (LinkedIn) — tasdiqlanmagan" if lang=="uz"
                       else "источник: сама фирма (LinkedIn) — не подтверждено"), 19)
    nore(d, 150, 858, ("grafik: illyustrativ" if lang=="uz" else "графика: иллюстративная"), 19)
    return vignette(grain(im), 0.45)

def scene_wakil(lang):
    im = bg_gradient(DARKER, (12, 40, 56))
    d = ImageDraw.Draw(im)
    eyebrow(d, 150, 210, "2026 · WAKIL AI", color=GOLD, size=26)
    rule(d, 208, 266, 116)
    h = ["Advokat o'zi javob quradi"] if lang == "uz" else ["Адвокат строит ответ сам"]
    headline(d, 150, 304, h, color=CREAM, size=74)
    cap = (["Abdulloh Sodiq o'zbek tilidagi huquqiy",
            "sun'iy intellektni yaratishda qatnashadi."]
           if lang == "uz" else
           ["Абдуллох Содик участвует в создании",
            "правового ИИ на узбекском языке."])
    caption(d, 150, 420, cap, size=30)

    # --- illustrative product mock window
    mx, my, mw, mh = 150, 560, 780, 380
    d.rectangle([mx, my, mx+mw, my+mh], fill=(10, 32, 44), outline=(201,169,110,140), width=1)
    d.rectangle([mx, my, mx+mw, my+44], fill=(16, 46, 62))
    for i, c in enumerate([(255,95,86),(255,189,46),(39,201,63)]):
        d.ellipse([mx+20+i*26, my+15, mx+34+i*26, my+29], fill=c)
    draw_tracked(d, mx+120, my+12, "Wakil AI", sans(20, bold=True), GOLD_L, tracking=1.5)
    q = ("Savol:  Mehnat shartnomasini bekor qilish tartibi?"
         if lang == "uz" else
         "Запрос:  Порядок расторжения трудового договора?")
    draw_tracked(d, mx+28, my+78, q, sans(22), (200, 208, 214), tracking=0.2)
    d.line([mx+28, my+120, mx+mw-28, my+120], fill=(255,255,255,26), width=1)
    a = (["Javob:  Mehnat kodeksining 97-moddasiga ko'ra...",
          "[Manba: lex.uz · MK 97-modda]"]
         if lang == "uz" else
         ["Ответ:  Согласно ст. 97 Трудового кодекса...",
          "[Источник: lex.uz · ст. 97 ТК]"])
    for i, ln in enumerate(a):
        col = (188, 226, 190) if i == 0 else GOLD_L
        draw_tracked(d, mx+28, my+150+i*42, ln, sans(21), col, tracking=0.2)
    draw_tracked(d, mx+28, my+250, ("◆ har bir javob manbaga bog'lanadi" if lang=="uz"
                                    else "◆ каждый ответ привязан к источнику"),
                 sans(19), (150, 200, 170), tracking=0.4)
    draw_tracked(d, mx+28, my+300, ("illyustrativ maket — haqiqiy mahsulot emas" if lang=="uz"
                                    else "иллюстративный макет — не реальный продукт"),
                 sans(17), (150, 158, 164), tracking=0.4)

    # --- verification badges (right column)
    bx = 1010
    badges = [("lex.uz", "huquqiy manba bazasi" if lang=="uz" else "база правовых источников"),
              ("Stanford CodeX", "TexIndex reyestri" if lang=="uz" else "реестр TechIndex"),
              ("Adliya akademiyasi" if lang=="uz" else "Академия правосудия",
               "taqdimot" if lang=="uz" else "презентация")]
    by = 590
    for title, sub in badges:
        d.rectangle([bx, by, bx+760, by+104], fill=(255,255,255,0), outline=(201,169,110,120), width=1)
        d.ellipse([bx+30, by+42, bx+50, by+62], fill=GOLD)
        draw_tracked(d, bx+72, by+26, title, sans(29, bold=True), CREAM, tracking=0.8)
        draw_tracked(d, bx+72, by+64, sub, sans(19), (176, 182, 188), tracking=0.4)
        by += 122
    return vignette(grain(im), 0.42)

def scene_people(lang):
    im = bg_gradient(DARKER, (19, 58, 78))
    d = ImageDraw.Draw(im)
    eyebrow(d, 0, 116, "JAMOA" if lang == "uz" else "КОМАНДА", color=GOLD, size=24, anchor="ca", center=W//2)
    h = ["Ishonchni inson quradi"] if lang == "uz" else ["Доверие строит человек"]
    headline(d, 0, 156, [h], color=CREAM, size=58, center=W//2)

    people = [
        ("abdulloh-sodiq",         "Abdulloh Sodiq",       "Asoschi, boshqaruvchi sherik" if lang=="uz" else "Основатель, управляющий партнёр"),
        ("gulyamov-said",          "Said Gulyamov",        "Sherik, professor" if lang=="uz" else "Партнёр, профессор"),
        ("abraev-firuz",           "Firuz Abrayev",        "Sherik" if lang=="uz" else "Партнёр"),
        ("xaytmurodov-ulugbek",    "Ulug'bek Xayitmurodov","Sherik" if lang=="uz" else "Партнёр"),
        ("mikhilyev-saidulla",     "Saidulla Mixliyev",    "Advokat" if lang=="uz" else "Адвокат"),
        ("isamutdinov-ulugbek",    "Ulug'bek Isamutdinov", "Moliyaviy yurist" if lang=="uz" else "Финансовый юрист"),
        ("alijonova-daria",        "Darya Alijonova",      "Advokat, xalqaro yurist" if lang=="uz" else "Адвокат, междунар. юрист"),
        ("ergasheva-sevinch",      "Sevinch Ergasheva",    "Advokat" if lang=="uz" else "Адвокат"),
    ]
    cols, rows = 4, 2
    cw, ch = 300, 330
    gapx, gapy = 60, 54
    total_w = cols*cw + (cols-1)*gapx
    x0 = (W - total_w)//2
    y0 = 250
    for idx, (name, disp, role) in enumerate(people):
        c = idx % cols; r = idx // cols
        x = x0 + c*(cw+gapx); y = y0 + r*(ch+gapy)
        try:
            ph = grade(load_photo(name))
            ph = cover(ph, (cw-40, 240), anchor_y=0.20)
        except Exception:
            ph = Image.new("RGB", (cw-40, 240), (40, 40, 40))
        im.paste(ph, (x+20, y))
        d.rectangle([x, y, x+cw, y+ch], outline=(201,169,110,90), width=1)
        draw_tracked(d, x+20, y+252, disp, sans(24, bold=True), CREAM, tracking=0.4)
        draw_tracked(d, x+20, y+286, role, sans(18), (176, 182, 188), tracking=0.3)
    cap = (["Advokatlar jamoasi — har bir mijoz uchun mas'uliyat."]
           if lang == "uz" else ["Команда адвокатов — ответственность за каждого клиента."])
    draw_tracked(d, W//2, 1010, cap[0], sans(24), (215, 213, 207), tracking=0.4, anchor="ca")
    return vignette(grain(im), 0.40)

def scene_office(lang):
    im = bg_gradient(DARKER, (24, 70, 92))
    d = ImageDraw.Draw(im)
    # threshold motif: an open door of light
    dx, dy, dw, dh = 1210, 200, 470, 700
    d.rectangle([dx, dy, dx+dw, dy+dh], fill=(232, 201, 138), outline=(201,169,110,180), width=2)
    for i in range(10):
        a = 200 - i*18
        d.rectangle([dx+16+i*6, dy+16+i*8, dx+dw-16-i*6, dy+dh-16-i*8],
                    outline=(255, 244, 220, max(a, 30)), width=1)
    eyebrow(d, 150, 300, "20.10.2026", color=GOLD, size=28)
    rule(d, 220, 360, 140)
    h = ["Yangi bosqich"] if lang == "uz" else ["Новый этап"]
    headline(d, 150, 410, h, color=CREAM, size=92)
    cap = (["Firma yangi manzilga ko'chadi."] if lang == "uz" else ["Фирма переезжает на новый адрес."])
    caption(d, 150, 560, cap, size=32)
    addr = ("Toshkent, Mirobod tumani," if lang == "uz" else "г. Ташкент, Мирабадский район,")
    addr2 = ("Mirobod ko'chasi, 46a-uy" if lang == "uz" else "ул. Мирабад, дом 46а")
    draw_tracked(d, 150, 640, addr,  sans(30), GOLD_L, tracking=0.6)
    draw_tracked(d, 150, 686, addr2, sans(30), GOLD_L, tracking=0.6)
    nore(d, 150, 790, ("yangi ofis fotosuratlari kutilmoqda (illyustrativ)" if lang=="uz"
                       else "фотографии нового офиса ожидаются (иллюстративно)"), 19)
    return vignette(grain(im), 0.45)

def scene_closing(lang):
    # authentic dark logo on a CREAM card
    im = Image.new("RGB", (W, H), CREAM)
    # soft cream→white gradient + gold edges
    arr = np.linspace(0, 1, H)[:, None, None]
    base = np.array(CREAM, dtype=np.float32)[None, None, :]*(1-arr) + np.array((255,255,255))[None,None,:]*arr
    im = Image.fromarray(np.repeat(base, W, axis=1).astype("uint8"), "RGB")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 10], fill=GOLD)
    logo = Image.open(os.path.join(WEB, "logo-full.png")).convert("RGBA")
    lw = 620; lh = int(logo.height * lw / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    im.paste(logo, ((W-lw)//2, 300), logo)
    rule(d, W//2, 300+lh+56, 140, color=GOLD, th=2)
    a = ("2010-yildan buyon — tajriba.  Bugun — texnologiya." if lang == "uz"
         else "С 2010 года — опыт.  Сегодня — технологии.")
    draw_tracked(d, W//2, 300+lh+106, a, sans(30), (90, 96, 104), tracking=0.4, anchor="ca")
    b = "ISH DAVOM ETADI" if lang == "uz" else "РАБОТА ПРОДОЛЖАЕТСЯ"
    draw_tracked(d, W//2, 300+lh+186, b, serif(52, bold=True), (23, 67, 90), tracking=6.0, anchor="ca")
    draw_tracked(d, W//2, 300+lh+296, "TOSHKENT · 2026", sans(24, bold=True), GOLD, tracking=4.0, anchor="ca")
    im = grain(im, 3.0)
    im = vignette(im, 0.12)
    return im

# ---------------------------------------------------------------- driver
import json, sys

SCENES = {
    "slate":   scene_slate,
    "hook":    scene_hook,
    "founder": scene_founder,
    "practice":scene_practice,
    "intl":    scene_intl,
    "wakil":   scene_wakil,
    "people":  scene_people,
    "office":  scene_office,
    "closing": scene_closing,
}

def render(lang):
    for key, fn in SCENES.items():
        im = fn(lang)
        if key != "closing":
            im = watermark(im)
        path = os.path.join(OUT, f"{lang}_{key}.png")
        im.save(path)
        print("wrote", path, im.size)

if __name__ == "__main__":
    langs = sys.argv[1:] or ["uz", "ru"]
    for lg in langs:
        render(lg)
