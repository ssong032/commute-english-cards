# -*- coding: utf-8 -*-
"""인스타그램 계정 세팅용 이미지 만들기 (HTML → headless Chrome 캡처).

실행: python -X utf8 make_assets.py [--handle @아이디] [--date 2027-01-26]
결과: out/profile.png, out/highlight_*.png, out/pinned_*.png, out/sample_<date>_01..06.png
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "data" / "plan_2027.json"
GLOSS = HERE / "data" / "glossary.txt"
SITE = "ssong032.github.io/commute-english"
LINE = {"work": ("월", "#3a6fd8", "회사·출근길"), "food": ("화", "#e0752d", "먹고 마시기"), "home": ("수", "#2f9e6a", "집과 동네"),
        "care": ("목", "#b0479b", "생활 서비스·건강"), "people": ("금", "#c99410", "사람·감정"),
        "weekend": ("토", "#1aa3b8", "쇼핑·주말"), "travel": ("일", "#7a5bd6", "여행")}
NAVY, BLUE, BG, INK, MUTED = "#13254f", "#1f4fd1", "#f4f6f9", "#141821", "#5f6878"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load_gloss():
    out = []
    for line in GLOSS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            k, v = line.split("|")
            for x in k.split("/"):
                out.append((x.strip().lower(), v.strip()))
    return sorted(out, key=lambda t: -len(t[0]))


def gloss_spans(en, gl):
    low, taken, out = en.lower().replace("’", "'"), [], []
    for k, v in gl:
        for m in re.finditer(r"(?<![a-z'])" + re.escape(k) + r"(?![a-z])", low):
            a, b = m.span()
            if not any(a < y and b > x for x, y in taken):
                taken.append((a, b)); out.append((a, b, v)); break
    return sorted(out)


def mark(en, spans):
    h, p = "", 0
    for a, b, _ in spans:
        h += esc(en[p:a]) + f"<u>{esc(en[a:b])}</u>"; p = b
    return h + esc(en[p:])


def page(w, h, body, extra_css=""):
    fonts = (HERE / "fonts").as_uri()
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family: KR; src: url("{fonts}/NotoSansKR-VF.ttf"); font-weight: 100 900; }}
@font-face {{ font-family: EMO; src: url("{fonts}/NotoColorEmoji.ttf"); }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ width: {w}px; height: {h}px; overflow: hidden; }}
body {{ font-family: KR, EMO, sans-serif; color: {INK}; background: {BG}; word-break: keep-all; overflow-wrap: anywhere; }}
u {{ text-decoration: underline dotted {BLUE}; text-decoration-thickness: 5px; text-underline-offset: 10px; }}
{extra_css}
</style></head><body>{body}</body></html>"""


def shot(chrome, html, out, w, h):
    tmp = out.with_suffix(".html")
    tmp.write_text(html, encoding="utf-8")
    extra = [] if os.name == "nt" else ["--no-sandbox"]  # GitHub 리눅스 서버용
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", *extra,
                    f"--user-data-dir={HERE / 'out' / '.chrome'}", "--allow-file-access-from-files",
                    f"--window-size={w},{h + 240}", "--virtual-time-budget=2500", f"--screenshot={out}", tmp.as_uri()],
                   check=True, capture_output=True)
    # 헤드리스 크롬은 창 아래쪽 일부를 가끔 안 그린다 → 창을 크게 열고 정확한 크기로 자른다
    from PIL import Image
    im = Image.open(out); im.load()
    im.crop((0, 0, w, h)).save(out)
    tmp.unlink()
    print("  ", out.name)


def ring(size, width):
    """7개 노선 색으로 된 원형 띠 (프로필 테두리)."""
    cols = [c for _, c, _ in LINE.values()]
    stops, step = [], 360 / len(cols)
    for i, c in enumerate(cols):
        stops.append(f"{c} {i * step:.1f}deg {(i + 1) * step - 2:.1f}deg, transparent {(i + 1) * step - 2:.1f}deg {(i + 1) * step:.1f}deg")
    return (f'<div style="position:absolute;inset:0;border-radius:50%;background:conic-gradient({",".join(stops)});'
            f'-webkit-mask:radial-gradient(circle, transparent {size / 2 - width}px, #000 {size / 2 - width + 1}px);"></div>')


def profile(chrome, out):
    s = 1080
    body = f"""<div style="position:relative;width:{s}px;height:{s}px;background:{NAVY};display:grid;place-items:center">
{ring(s, 70)}
<div style="text-align:center;color:#fff;line-height:1">
  <div style="font-size:330px;font-weight:900;letter-spacing:-8px">EN</div>
  <div style="font-size:112px;font-weight:800;margin-top:26px">출근길 영어</div>
</div></div>"""
    shot(chrome, page(s, s, body), out / "profile.png", s, s)


HIGHLIGHTS = [("start", "🚇", "시작하기", BLUE), ("work", "💼", "회사", LINE["work"][1]), ("food", "🍽️", "먹고 마시기", LINE["food"][1]),
              ("home", "🏠", "집과 동네", LINE["home"][1]), ("care", "🏥", "병원·은행", LINE["care"][1]),
              ("travel", "✈️", "여행", LINE["travel"][1]), ("game", "🎮", "게임 연습", NAVY)]


def highlights(chrome, out):
    w, h = 1080, 1920
    for key, emo, name, col in HIGHLIGHTS:
        body = f"""<div style="width:{w}px;height:{h}px;background:{col};display:grid;place-items:center">
<div style="text-align:center;color:#fff"><div style="font-family:EMO;font-size:300px;line-height:1">{emo}</div>
<div style="font-size:84px;font-weight:800;margin-top:40px">{name}</div></div></div>"""
        shot(chrome, page(w, h, body), out / f"highlight_{key}.png", w, h)


def frame(inner, handle, foot="", bg=BG):
    return f"""<div style="width:1080px;height:1350px;background:{bg};padding:84px 84px 150px;display:flex;flex-direction:column;gap:36px;position:relative;overflow:hidden">
{inner}
<div style="position:absolute;left:84px;right:84px;bottom:58px;display:flex;justify-content:space-between;align-items:center;font-size:30px;line-height:1.4;color:{MUTED};font-weight:600">
<span>🚇 {esc(handle)}</span><span>{esc(foot)}</span></div></div>"""


def badge(cat, size=64):
    d, c, _ = LINE[cat]
    return (f'<span style="display:inline-grid;place-items:center;width:{size}px;height:{size}px;border-radius:50%;'
            f'background:{c};color:#fff;font-weight:800;font-size:{size * .5:.0f}px">{d}</span>')


def pinned(chrome, out, handle):
    rows = "".join(
        f'<div style="display:flex;align-items:center;gap:26px;font-size:40px;font-weight:700">{badge(k, 70)}<span>{d}요일 · {n}</span></div>'
        for k, (d, c, n) in LINE.items())
    p1 = frame(f"""<div style="font-size:34px;font-weight:700;color:{BLUE}">출근길 영어 노선도</div>
<div style="font-size:92px;font-weight:900;line-height:1.15;letter-spacing:-2px">출근길 5분,<br>하루 한 장면</div>
<div style="font-size:38px;color:{MUTED};line-height:1.5">요일마다 노선이 정해져 있어요.<br>장면 하나에 이어지는 문장 3개씩.</div>
<div style="display:grid;gap:22px;margin-top:10px">{rows}</div>""", handle, "매일 아침 7시")
    shot(chrome, page(1080, 1350, p1), out / "pinned_1_intro.png", 1080, 1350)

    steps = [("📌", "저장하기", "아침에 올라온 장면을 저장해요."), ("🗣️", "소리 내 읽기", "출근길에 문장 3개를 세 번씩 따라 말해요."),
             ("🎮", "게임으로 연습", "프로필 링크에서 4단계 게임으로 익혀요."), ("🔁", "복습 열차", "잊을 때쯤 사이트가 다시 물어봐요.")]
    st = "".join(f"""<div style="display:flex;gap:30px;align-items:flex-start;background:#fff;border-radius:28px;padding:34px 36px">
<div style="font-family:EMO;font-size:64px;line-height:1">{e}</div><div><div style="font-size:44px;font-weight:800">{i + 1}. {t}</div>
<div style="font-size:34px;color:{MUTED};margin-top:8px">{d}</div></div></div>""" for i, (e, t, d) in enumerate(steps))
    p2 = frame(f"""<div style="font-size:34px;font-weight:700;color:{BLUE}">이 계정 200% 쓰는 법</div>
<div style="font-size:84px;font-weight:900;line-height:1.15;letter-spacing:-2px">보기만 하면<br>안 늘어요</div>
<div style="display:grid;gap:22px">{st}</div>""", handle, "저장 필수 📌")
    shot(chrome, page(1080, 1350, p2), out / "pinned_2_howto.png", 1080, 1350)

    lv = [("1단계", "뜻 보고 고르기"), ("2단계", "단어 순서 맞추기"), ("3단계", "빈칸 채우기"), ("4단계", "듣고 따라 쓰기")]
    lvs = "".join(f"""<div style="display:flex;align-items:center;gap:24px;font-size:42px;font-weight:700">
<span style="background:{BLUE};color:#fff;border-radius:99px;padding:8px 26px;font-size:34px">{a}</span>{b}</div>""" for a, b in lv)
    p3 = frame(f"""<div style="font-size:34px;font-weight:700;color:#9db7f0">무료 연습 사이트</div>
<div style="font-size:84px;font-weight:900;line-height:1.15;color:#fff;letter-spacing:-2px">읽은 문장,<br>게임으로 내 것 만들기</div>
<div style="display:grid;gap:26px;background:#fff;border-radius:32px;padding:44px">{lvs}</div>
<div style="font-size:36px;color:#dbe4ff;line-height:1.6">인턴에서 대표까지 직급 승진 · 60초 스피드 퀴즈<br>밑줄 단어는 뜻이 바로 아래에</div>
<div style="font-size:38px;font-weight:800;color:#fff">🔗 {SITE}</div>""", handle, "프로필 링크 👆", bg=NAVY)
    shot(chrome, page(1080, 1350, p3), out / "pinned_3_site.png", 1080, 1350)


def sample(chrome, out, handle, date):
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    sc = next(r for r in plan if r["date"] == date)
    gl = load_gloss()
    d, col, cname = LINE[sc["cat"]]
    m, dd = int(date[5:7]), int(date[8:10])
    tag = f'<div style="display:flex;align-items:center;gap:18px;font-size:32px;font-weight:700;color:{MUTED}">{badge(sc["cat"], 58)}<span>DAY {sc["day"]} · {m}월 {dd}일 {d}요일 · {cname}</span></div>'
    slides = []
    first_q = sc["steps"][0]["q"].rstrip("?")
    slides.append(f"""{tag}
<div style="font-size:40px;font-weight:700;color:{col};margin-top:30px">오늘의 장면</div>
<div style="font-size:100px;font-weight:900;line-height:1.15;letter-spacing:-2px">{esc(sc["title"])}</div>
<div style="font-size:44px;line-height:1.55;color:{INK}">{esc(sc["scene"])}</div>
<div style="font-size:52px;font-weight:800;background:#fff;border-radius:28px;padding:34px 40px;border-left:14px solid {col}">이럴 때, 영어로 {esc(first_q)}?</div>
<div style="font-size:38px;font-weight:700;color:{BLUE}">넘겨서 문장 3개 익히기 👉</div>""")
    stations = "".join(f"""<div style="display:flex;gap:30px;align-items:center;position:relative">
<span style="width:56px;height:56px;border-radius:50%;background:#fff;border:12px solid {col};flex:none;z-index:1"></span>
<div><div style="font-size:30px;color:{MUTED};font-weight:700">{i + 1}번째 역</div><div style="font-size:46px;font-weight:800">{esc(s["q"])}</div></div></div>"""
                        for i, s in enumerate(sc["steps"]))
    slides.append(f"""{tag}
<div style="font-size:40px;font-weight:700;color:{col}">이렇게 말해보세요</div>
<div style="font-size:64px;font-weight:900;line-height:1.3">{esc(sc["guide"])}</div>
<div style="position:relative;display:grid;gap:64px;padding:20px 0">
<div style="position:absolute;left:27px;top:40px;bottom:40px;width:12px;background:{col};border-radius:6px"></div>{stations}</div>""")
    for i, s in enumerate(sc["steps"]):
        sp = gloss_spans(s["en"], gl)
        chips = "".join(f'<span style="background:#fff;border:2px solid #dfe3ea;border-radius:18px;padding:12px 22px;font-size:34px"><b style="color:{BLUE}">{esc(s["en"][a:b])}</b> {esc(v)}</span>' for a, b, v in sp)
        slides.append(f"""{tag}
<div style="display:flex;align-items:center;gap:22px"><span style="background:{col};color:#fff;border-radius:99px;padding:10px 30px;font-size:34px;font-weight:800">{i + 1} / 3</span>
<span style="font-size:48px;font-weight:800">{esc(s["q"])}</span></div>
<div style="font-size:74px;font-weight:800;line-height:1.3;letter-spacing:-1px;margin-top:20px">{mark(s["en"], sp)}</div>
<div style="font-size:46px;line-height:1.5;color:{INK}">{esc(s["ko"])}</div>
<div style="display:flex;flex-wrap:wrap;gap:16px">{chips}</div>""")
    recap = "".join(f'<div style="font-size:40px;font-weight:700;line-height:1.35">{i + 1}. {esc(s["en"])}</div>' for i, s in enumerate(sc["steps"]))
    slides.append(f"""{tag}
<div style="font-size:40px;font-weight:700;color:{col}">오늘의 3문장</div>
<div style="display:grid;gap:24px;background:#fff;border-radius:32px;padding:44px">{recap}</div>
<div style="font-size:46px;font-weight:800;line-height:1.5">📌 저장하고 출근길에<br>세 번씩 소리 내 읽기</div>
<div style="font-size:40px;color:{MUTED};line-height:1.5">🔊 AI 원어민 발음 듣고 🎙️ 내 발음 점수 받기<br>프로필 링크 👆</div>""")
    for k, body in enumerate(slides, 1):
        shot(chrome, page(1080, 1350, frame(body, handle, f"{k}/{len(slides)}")), out / f"sample_{date}_{k:02d}.png", 1080, 1350)
    return sc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", default="@commute.english.kr")
    ap.add_argument("--date", default="2027-01-26")
    a = ap.parse_args()
    chrome = next((c for c in [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                               r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "/usr/bin/google-chrome"]
                   if os.path.exists(c)), None) or sys.exit("Chrome/Edge 를 찾지 못했어요")
    out = HERE / "out"; out.mkdir(exist_ok=True)
    profile(chrome, out); highlights(chrome, out); pinned(chrome, out, a.handle)
    sc = sample(chrome, out, a.handle, a.date)
    print("OK", sc["title"])


if __name__ == "__main__":
    main()
