# -*- coding: utf-8 -*-
"""카드뉴스 v3 견본 — 후보 A '문제 → 정답 번갈아 보기' (8장) + 계절 테마 + 가운데 정렬.
기존 첫 주 카드(render_post.py)는 건드리지 않는다.

1 표지 Q1 → 2 정답① → 3 Q2(빈칸) → 4 정답② → 5 Q3(빈칸) → 6 정답③ → 7 보너스 → 8 정리
계절: 12~2월 겨울(눈) · 3~5월 봄(벚꽃) · 6~8월 여름(물결·물방울) · 9~11월 가을(낙엽)
실행: python -X utf8 render_quiz.py 2027-01-05 [2027-04-06 ...] [--cover-only] [--handle @아이디]
결과: samples/quizA_<날짜>/card_01..08.jpg  (--cover-only 면 card_01 만)
보너스 표현: ../plan/data/bonus.txt (날짜|English|한국어|한 줄 설명)
"""
import argparse, json, math, os, random, re, shutil, sys
from pathlib import Path
from PIL import Image
import make_assets as MA

HERE = Path(__file__).resolve().parent
BONUS = HERE / "data" / "bonus.txt"
TOTAL = 8
CORRECT = "#1f9d63"

SEASONS = {
    "winter": {"name": "겨울", "icon": "❄️", "bg": "linear-gradient(170deg,#d9e7f8 0%,#eef4fc 55%,#f8fbff 100%)",
               "accent": "#2f62c9", "soft": "#e3edfb", "mark": "#cfe0fa", "deco": "#ffffff"},
    "spring": {"name": "봄", "icon": "🌸", "bg": "linear-gradient(170deg,#fbdde7 0%,#fff0f4 55%,#fffafb 100%)",
               "accent": "#d24f7e", "soft": "#fde6ee", "mark": "#fbd3e1", "deco": "#f6a9c2"},
    "summer": {"name": "여름", "icon": "🌊", "bg": "linear-gradient(170deg,#cdeff0 0%,#eaf9f8 55%,#f7fdfc 100%)",
               "accent": "#0f8f8a", "soft": "#dcf4f2", "mark": "#bfece8", "deco": "#8fd9d4"},
    "autumn": {"name": "가을", "icon": "🍁", "bg": "linear-gradient(170deg,#f9dfc8 0%,#fdf0e4 55%,#fffaf5 100%)",
               "accent": "#c75a22", "soft": "#fbe7d6", "mark": "#f7d4b8", "deco": "#e8935a"},
}


FONTS = (HERE / "fonts").as_uri()
# 영어는 영어 전용 폰트(Inter)로, 자간·행간을 넓혀 읽기 쉽게
EN_CSS = f"""@font-face {{ font-family: EN; src: url("{FONTS}/Inter-VF.ttf"); font-weight: 100 900; }}
.en {{ font-family: EN, KR, EMO, sans-serif; letter-spacing: -0.005em; text-wrap: balance; word-break: normal; overflow-wrap: break-word; }}"""


def en_size(text, big, small):
    """긴 문장은 조금 작게 (줄 수가 너무 많아지지 않게)."""
    n = len(text)
    return big if n <= 42 else (big + small) // 2 if n <= 58 else small


def season_of(date):
    m = int(date[5:7])
    return "winter" if m in (12, 1, 2) else "spring" if m <= 5 else "summer" if m <= 8 else "autumn"


def deco_svg(season, seed):
    """배경 장식 (같은 날짜면 항상 같은 배치). 가운데 카드 뒤로 깔린다."""
    t = SEASONS[season]; rnd = random.Random(seed); items = []
    for _ in range(26):
        x, y, s, r = rnd.uniform(0, 1080), rnd.uniform(0, 1350), rnd.uniform(0.6, 1.6), rnd.uniform(0, 360)
        if season == "winter":  # 눈송이
            arms = "".join(f'<line x1="0" y1="0" x2="{18 * math.cos(math.radians(a)):.1f}" y2="{18 * math.sin(math.radians(a)):.1f}"/>' for a in range(0, 360, 60))
            items.append(f'<g transform="translate({x:.0f},{y:.0f}) scale({s:.2f}) rotate({r:.0f})" stroke="{t["deco"]}" stroke-width="4" stroke-linecap="round" opacity=".9">{arms}</g>')
        elif season == "spring":  # 꽃잎
            items.append(f'<path transform="translate({x:.0f},{y:.0f}) scale({s:.2f}) rotate({r:.0f})" d="M0 -16 C12 -16 16 -2 0 16 C-16 -2 -12 -16 0 -16 Z" fill="{t["deco"]}" opacity=".55"/>')
        elif season == "summer":  # 물방울
            items.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{9 * s:.1f}" fill="none" stroke="{t["deco"]}" stroke-width="4" opacity=".6"/>')
        else:  # 낙엽
            items.append(f'<path transform="translate({x:.0f},{y:.0f}) scale({s:.2f}) rotate({r:.0f})" d="M0 -20 C14 -10 14 10 0 20 C-14 10 -14 -10 0 -20 Z M0 -20 L0 20" fill="{t["deco"]}" stroke="{t["deco"]}" stroke-width="2" opacity=".45"/>')
    if season == "summer":
        items.append(f'<path d="M0 1250 Q135 1210 270 1250 T540 1250 T810 1250 T1080 1250 V1350 H0 Z" fill="{t["deco"]}" opacity=".35"/>')
    return f'<svg width="1080" height="1350" style="position:absolute;inset:0" xmlns="http://www.w3.org/2000/svg">{"".join(items)}</svg>'


def load_bonus():
    out = {}
    if BONUS.exists():
        for line in BONUS.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                d, en, ko, note = [x.strip() for x in line.split("|")]
                out[d] = (en, ko, note)
    return out


def blank_target(en, gl):
    """빈칸으로 가릴 부분: 사전에 있는 가장 긴 표현(22자 이하), 없으면 가장 긴 단어."""
    sp = [x for x in MA.gloss_spans(en, gl) if x[1] - x[0] <= 22]
    if sp:
        return max(sp, key=lambda x: x[1] - x[0])
    m = max(re.finditer(r"[A-Za-z][A-Za-z'-]*", en), key=lambda m: len(m.group()))
    return m.start(), m.end(), ""


def highlight(en, spans, t):
    """핵심 표현은 형광펜처럼 칠한다."""
    h, p = "", 0
    for a, b, _ in spans:
        h += MA.esc(en[p:a]) + f'<span style="background:linear-gradient(transparent 55%,{t["mark"]} 55%);padding:0 4px">{MA.esc(en[a:b])}</span>'; p = b
    return h + MA.esc(en[p:])


def frame(sc, body, teaser, handle, k, total=TOTAL):
    t = SEASONS[season_of(sc["date"])]
    d, col, cname = MA.LINE[sc["cat"]]
    m, dd = int(sc["date"][5:7]), int(sc["date"][8:10])
    dots = "".join(f'<i style="display:inline-block;width:{26 if j == k else 12}px;height:12px;border-radius:6px;background:{t["accent"] if j == k else "#c9cfd9"}"></i>' for j in range(1, total + 1))
    arrow = (f'<div style="position:absolute;right:0;top:50%;transform:translateY(-50%);width:54px;height:112px;background:{t["accent"]};'
             'border-radius:56px 0 0 56px;display:grid;place-items:center;color:#fff;font-size:50px;font-weight:800">›</div>') if k < total else ""
    tz = f'<div style="font-size:36px;font-weight:800;color:{t["accent"]};text-align:center">👉 {teaser}</div>' if teaser else ""
    return f"""<div style="width:1080px;height:1350px;background:{t['bg']};position:relative;overflow:hidden;font-feature-settings:'palt'">
{deco_svg(season_of(sc['date']), sc['date'])}
<div style="position:absolute;top:70px;left:0;right:0;display:flex;justify-content:center">
  <div style="display:flex;align-items:center;gap:14px;background:#ffffffcc;border-radius:99px;padding:12px 30px 12px 14px;font-size:30px;font-weight:700;color:{MA.INK}">
    {MA.badge(sc["cat"], 50)}<span>{t["icon"]} {m}월 {dd}일 {d}요일 · {cname}</span></div></div>
<div style="position:absolute;left:70px;right:70px;top:170px;bottom:{250 if teaser else 170}px;background:#ffffff;border-radius:48px;box-shadow:0 18px 40px rgba(40,60,90,.10);
  padding:56px 64px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:34px;text-align:center">{body}</div>
<div style="position:absolute;left:70px;right:70px;bottom:165px">{tz}</div>
<div style="position:absolute;left:0;right:0;bottom:70px;display:flex;flex-direction:column;align-items:center;gap:16px">
  <div style="display:flex;gap:10px">{dots}</div>
  <div style="font-size:28px;color:{MA.MUTED};font-weight:600">🚇 {MA.esc(handle)} · 출근길 영어</div></div>
{arrow}</div>"""


def slides(sc, gl, bonus, plan_date=None):
    t = SEASONS[season_of(sc["date"])]
    s = sc["steps"]
    label = lambda txt, c=None: f'<div style="display:inline-block;background:{c or t["soft"]};color:{"#fff" if c else t["accent"]};border-radius:99px;padding:10px 30px;font-size:34px;font-weight:800;white-space:nowrap">{txt}</div>'
    out = []
    out.append((f"""{label("Q1 · " + MA.esc(sc["title"]))}
<div style="font-size:84px;font-weight:900;line-height:1.3;letter-spacing:-2px;color:{MA.INK}">“{MA.esc(s[0]["ko"])}”</div>
<div style="font-size:96px;font-weight:900;color:{t["accent"]};letter-spacing:-2px">영어로?</div>
<div style="font-size:38px;color:{MA.MUTED}">3초 안에 떠오르면 저장 안 해도 돼요 😎</div>""", "정답은 다음 장"))

    def answer(i):
        sp = MA.gloss_spans(s[i]["en"], gl)
        chips = "".join(f'<span style="background:{t["soft"]};border-radius:18px;padding:12px 24px;font-size:34px"><b class="en" style="color:{t["accent"]}">{MA.esc(s[i]["en"][x:y])}</b> {MA.esc(v)}</span>' for x, y, v in sp)
        return f"""{label("정답 " + str(i + 1), CORRECT)}
<div style="font-size:36px;color:{MA.MUTED};font-weight:600">“{MA.esc(s[i]["ko"])}”</div>
<div class="en" style="font-size:{en_size(s[i]["en"], 92, 76)}px;font-weight:700;line-height:1.3;color:{MA.INK}">{highlight(s[i]["en"], sp, t)}</div>
<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:14px">{chips}</div>"""

    def question(i):
        a, b, v = blank_target(s[i]["en"], gl)
        words = s[i]["en"][a:b].split()
        blank = " ".join(f'<span style="display:inline-block;min-width:{max(3, len(w)) * 0.6:.1f}em;border-bottom:8px solid {t["accent"]}">&nbsp;</span>' for w in words)
        hint = f"💡 힌트: {MA.esc(v)}" if v else f"💡 힌트: {len(words)}단어"
        return f"""{label("Q" + str(i + 1) + " · " + MA.esc(s[i]["q"]))}
<div style="font-size:70px;font-weight:900;line-height:1.35;color:{MA.INK}">“{MA.esc(s[i]["ko"])}”</div>
<div class="en" style="font-size:{en_size(s[i]["en"], 72, 62)}px;font-weight:600;line-height:1.5;color:{MA.INK}">{MA.esc(s[i]["en"][:a])}{blank}{MA.esc(s[i]["en"][b:])}</div>
<div style="font-size:36px;color:{MA.MUTED}">{hint}</div>"""

    out.append((answer(0), f'다음 문제 “{MA.esc(s[1]["ko"])}”'))
    out.append((question(1), "빈칸 정답은 다음 장"))
    out.append((answer(1), f'마지막 문제 “{MA.esc(s[2]["ko"])}”'))
    out.append((question(2), "빈칸 정답은 다음 장"))
    out.append((answer(2), "끝까지 본 사람만 보는 보너스 표현"))
    b = bonus.get(plan_date or sc["date"])
    if b:
        out.append((f"""{label("🎁 보너스 · 이렇게도 말해요")}
<div class="en" style="font-size:{en_size(b[0], 88, 74)}px;font-weight:700;line-height:1.3;color:{MA.INK}">{MA.esc(b[0])}</div>
<div style="font-size:42px;line-height:1.5">{MA.esc(b[1])}</div>
<div style="font-size:34px;color:{MA.MUTED};line-height:1.55;background:{t["soft"]};border-radius:24px;padding:26px 34px">{MA.esc(b[2])}</div>""", "오늘 3문장 한 번에 정리"))
    recap = "".join(f'<div style="display:flex;gap:20px;align-items:flex-start;text-align:left"><span style="flex:none;width:52px;height:52px;border-radius:50%;background:{t["accent"]};color:#fff;'
                    f'display:grid;place-items:center;font-size:30px;font-weight:800">{n + 1}</span><span class="en" style="font-size:42px;font-weight:600;line-height:1.35;text-wrap:pretty">{MA.esc(x["en"])}</span></div>'
                    for n, x in enumerate(s))
    out.append((f"""<div style="font-size:52px;font-weight:900;color:{MA.INK}">몇 개 맞혔어요? ✍️</div>
<div style="font-size:36px;color:{MA.MUTED}">댓글에 0~3으로 남겨 보세요</div>
<div style="display:grid;gap:20px;background:{t["soft"]};border-radius:32px;padding:40px 44px;width:100%">{recap}</div>
<div style="font-size:42px;font-weight:800;color:{t["accent"]}">📌 저장해두고 출퇴근길에 3번만</div>
<div style="font-size:32px;color:{MA.MUTED};line-height:1.5">🎧 AI 원어민 발음 · 🎙️ 내 발음 점수는 프로필 링크</div>""", ""))
    return out


def render_cards(chrome, sc, plan_date, outdir, handle, gl, bonus):
    """자동 게시용: 보너스 표현이 있으면 8장, 없으면 7장. 파일 이름 목록을 돌려준다."""
    ss = slides(sc, gl, bonus, plan_date)
    names = []
    for k, sl in enumerate(ss, 1):
        png = outdir / f"card_{k:02d}.png"
        MA.shot(chrome, MA.page(1080, 1350, frame(sc, sl[0], sl[1], handle, k, len(ss)), EN_CSS), png, 1080, 1350)
        Image.open(png).convert("RGB").save(outdir / f"card_{k:02d}.jpg", quality=92); png.unlink()
        names.append(f"card_{k:02d}.jpg")
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dates", nargs="+")
    ap.add_argument("--handle", default="@commute.english.kr")
    ap.add_argument("--cover-only", action="store_true")
    a = ap.parse_args()
    chrome = next((c for c in [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                               r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"] if os.path.exists(c)), None) or sys.exit("Chrome 없음")
    plan = {r["date"]: r for r in json.loads(MA.PLAN.read_text(encoding="utf-8"))}
    gl, bonus = MA.load_gloss(), load_bonus()
    for date in a.dates:
        sc = plan[date]
        out = HERE / "samples" / f"quizA_{date}"; out.mkdir(parents=True, exist_ok=True)
        ss = slides(sc, gl, bonus)
        for k, sl in enumerate(ss, 1):
            if a.cover_only and k > 1:
                break
            png = out / f"card_{k:02d}.png"
            MA.shot(chrome, MA.page(1080, 1350, frame(sc, sl[0], sl[1], a.handle, k, len(ss)), EN_CSS), png, 1080, 1350)
            Image.open(png).convert("RGB").save(out / f"card_{k:02d}.jpg", quality=92); png.unlink()
    shutil.rmtree(HERE / "out" / ".chrome", ignore_errors=True)
    print("OK")


if __name__ == "__main__":
    main()
