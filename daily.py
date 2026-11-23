# -*- coding: utf-8 -*-
"""출근길 영어 — 하루치 인스타 게시물 자동 제작 (GitHub Actions가 매일 20:00 KST에 실행).

- 게시일 D(기본: 내일, 한국 시간)의 장면을 2027 계획에서 고른다. 2027년이 아니면 364일(52주)씩 옮겨
  같은 요일의 장면을 쓴다 → 요일 노선이 맞는다.
- 카드뉴스(퀴즈형 7~8장, 계절 테마는 실제 게시일 기준) + 토리 캐릭터 릴스 + 캡션 + manifest.json 을 만든다.
- 원어민 음성은 사이트에 올려둔 mp3(https://ssong032.github.io/commute-english/audio/)를 받아 쓴다.
실행: python daily.py [--date 2026-11-25] [--out pub/posts] [--keep 4]
"""
import argparse, datetime as dt, json, os, shutil, subprocess, sys, urllib.request
from pathlib import Path

import make_assets as MA
import render_quiz as RQ
import render_character as RC

HERE = Path(__file__).resolve().parent
AUDIO = "https://ssong032.github.io/commute-english/audio"
SITE = "ssong032.github.io/commute-english"
HANDLE = "@commute.english.kr"
LAUNCH = dt.date.fromisoformat(os.environ.get("LAUNCH_DATE", "2026-11-24"))
KST = dt.timezone(dt.timedelta(hours=9))
WD = "월화수목금토일"
HASH = {"work": ["#회사영어", "#직장인영어", "#비즈니스영어"], "food": ["#식당영어", "#카페영어", "#주문영어"],
        "home": ["#생활영어", "#일상영어", "#영어공부"], "care": ["#병원영어", "#생활영어회화", "#실전영어"],
        "people": ["#스몰토크", "#영어대화", "#감정표현"], "weekend": ["#쇼핑영어", "#주말영어", "#영어회화공부"],
        "travel": ["#여행영어", "#공항영어", "#해외여행영어"]}
BASE_TAGS = ["#영어회화", "#출근길영어", "#영어표현", "#하루한문장", "#영어퀴즈"]


def plan_date(d):
    """2027년 계획에서 같은 요일의 날짜로 옮긴다 (52주 = 364일 단위)."""
    while d.year < 2027:
        d += dt.timedelta(days=364)
    while d.year > 2027:
        d -= dt.timedelta(days=364)
    return d


def find_chrome():
    for c in [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium-browser", "/usr/bin/chromium"]:
        if os.path.exists(c):
            return c
    c = shutil.which("google-chrome") or shutil.which("chromium")
    return c or sys.exit("Chrome 을 찾지 못했어요")


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def tags(sc):
    return " ".join((BASE_TAGS + [t for t in HASH[sc["cat"]] if t not in BASE_TAGS])[:9])


def card_caption(sc):
    s = sc["steps"]
    return "\n".join([
        f'Q. “{s[0]["ko"]}” 영어로? 🤔',
        f'{sc["title"]} · 정답은 넘겨서 확인 👉', "",
        sc["scene"], "",
        "문제 3개 + 정답, 몇 개 맞혔는지 댓글에 0~3으로 남겨 주세요 ✍️",
        "📌 저장해두고 출퇴근길에 3번만",
        "🎧 AI 원어민 발음 · 🎙️ 내 발음 점수: 프로필 링크", "",
        tags(sc)])


def reel_caption(sc):
    s = sc["steps"]
    lines = [f'🐱 토리랑 따라 말하기 · {sc["title"]}', "", sc["scene"], ""]
    for i, x in enumerate(s):
        lines += [f'{i + 1}. {x["en"]}', f'   {x["ko"]}']
    lines += ["", "🔁 한 문장씩 듣고 바로 따라 해 보세요", "🎙️ 내 발음 점수 받기: 프로필 링크",
              "🔊 영상 속 음성은 AI 원어민 보이스예요", "", tags(sc)]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="")
    ap.add_argument("--out", default=str(HERE / "pub" / "posts"))
    ap.add_argument("--keep", type=int, default=4, help="out 폴더에 남길 날짜 수 (오래된 것 삭제)")
    a = ap.parse_args()
    D = dt.date.fromisoformat(a.date) if a.date else (dt.datetime.now(KST) + dt.timedelta(days=1)).date()
    P = plan_date(D)
    plan = {r["date"]: r for r in json.loads(MA.PLAN.read_text(encoding="utf-8"))}
    base = plan[P.isoformat()]
    sc = dict(base, date=D.isoformat(), weekday=WD[D.weekday()], day=(D - LAUNCH).days + 1)
    assert base["weekday"] == sc["weekday"], "요일 노선이 안 맞아요"
    a.out = str(Path(a.out).resolve())
    out = Path(a.out) / D.isoformat()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    print(f"== {D} ({sc['weekday']}) ← 계획 {P} · {sc['title']}")
    chrome, ff, gl, bonus = find_chrome(), ffmpeg(), MA.load_gloss(), RQ.load_bonus()
    # 원어민 음성 받기 → 24kHz 모노 wav
    wavs = []
    for i in range(3):
        mp3, wav = out / f"_v{i}.mp3", out / f"_v{i}.wav"
        urllib.request.urlretrieve(f"{AUDIO}/{P.isoformat()}-{i}.mp3", mp3)
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(mp3), "-ar", "24000", "-ac", "1", str(wav)], check=True)
        wavs.append(wav)
    cards = RQ.render_cards(chrome, sc, P.isoformat(), out, HANDLE, gl, bonus)
    secs = RC.build(chrome, sc, wavs, out / "reel.mp4", out / "reel_cover.jpg", HANDLE, gl, ff)
    for f in out.glob("_v*"):
        f.unlink()
    m = {"date": D.isoformat(), "plan_date": P.isoformat(), "title": sc["title"], "cards": cards,
         "reel": "reel.mp4", "reel_seconds": round(secs, 1), "caption": card_caption(sc), "reel_caption": reel_caption(sc)}
    (out / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "caption.txt").write_text(m["caption"] + "\n\n---- 릴스 ----\n" + m["reel_caption"], encoding="utf-8")
    shutil.rmtree(HERE / "out", ignore_errors=True)
    # 오래된 날짜 정리
    days = sorted(p for p in Path(a.out).iterdir() if p.is_dir())
    for p in days[:-a.keep] if len(days) > a.keep else []:
        shutil.rmtree(p)
    print(f"OK cards {len(cards)} · reel {secs:.1f}s")


if __name__ == "__main__":
    main()
