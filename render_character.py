# -*- coding: utf-8 -*-
"""캐릭터 릴스 — 자체 제작 캐릭터 '토리'(헤드폰 쓴 출근길 고양이)가 AI 원어민 음성으로 말한다.
입 모양 3단계(닫힘/반/열림)를 음성 크기에 맞추고, 3초마다 눈을 깜빡인다. 외부 앱·유료 서비스 없음.
daily.py 가 build() 를 부른다.
"""
import shutil, subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image

import make_assets as MA

HERE = Path(__file__).resolve().parent
MUSIC = HERE / "music"
SR, FPS = 24000, 30


def tori(mouth, blink):
    """토리 SVG. mouth: 0 닫힘, 1 반, 2 열림. blink: 눈 감음."""
    eyes = ('<path d="M-95 -20 q22 14 44 0" stroke="#1d1d1f" stroke-width="10" fill="none" stroke-linecap="round"/>'
            '<path d="M51 -20 q22 14 44 0" stroke="#1d1d1f" stroke-width="10" fill="none" stroke-linecap="round"/>') if blink else (
            '<ellipse cx="-73" cy="-22" rx="19" ry="24" fill="#1d1d1f"/><circle cx="-66" cy="-32" r="7" fill="#fff"/>'
            '<ellipse cx="73" cy="-22" rx="19" ry="24" fill="#1d1d1f"/><circle cx="80" cy="-32" r="7" fill="#fff"/>')
    mouths = ['<path d="M-26 38 q13 14 26 0 q13 14 26 0" stroke="#1d1d1f" stroke-width="8" fill="none" stroke-linecap="round"/>',
              '<ellipse cx="0" cy="46" rx="24" ry="15" fill="#7a2531"/><ellipse cx="0" cy="54" rx="13" ry="6" fill="#e5737f"/>',
              '<ellipse cx="0" cy="52" rx="30" ry="30" fill="#7a2531"/><ellipse cx="0" cy="68" rx="17" ry="9" fill="#e5737f"/>']
    return f"""<svg viewBox="-300 -330 600 640" width="660" height="704" xmlns="http://www.w3.org/2000/svg">
<path d="M-210 300 q0 -170 210 -170 q210 0 210 170 z" fill="#1f4fd1"/>
<rect x="-46" y="190" width="92" height="62" rx="10" fill="#fff"/><text x="0" y="232" font-size="30" font-weight="800" text-anchor="middle" fill="#1f4fd1" font-family="Arial">T</text>
<path d="M-190 -80 L-195 -295 L-55 -165 z" fill="#ffd9a8"/><path d="M190 -80 L195 -295 L55 -165 z" fill="#ffd9a8"/>
<path d="M-172 -125 L-176 -250 L-95 -170 z" fill="#f6a8b4"/><path d="M172 -125 L176 -250 L95 -170 z" fill="#f6a8b4"/>
<ellipse cx="0" cy="0" rx="215" ry="190" fill="#ffe4bf"/>
<path d="M-205 -40 q205 -260 410 0" stroke="#e0752d" stroke-width="26" fill="none" stroke-linecap="round"/>
<rect x="-238" y="-60" width="62" height="110" rx="28" fill="#e0752d"/><rect x="176" y="-60" width="62" height="110" rx="28" fill="#e0752d"/>
{eyes}
<ellipse cx="-120" cy="34" rx="30" ry="17" fill="#f6a8b4" opacity=".7"/><ellipse cx="120" cy="34" rx="30" ry="17" fill="#f6a8b4" opacity=".7"/>
<path d="M-12 14 l12 10 l12 -10 z" fill="#d97a6c"/>
{mouths[mouth]}
<path d="M-150 30 l-70 -8 M-150 44 l-68 10 M150 30 l70 -8 M150 44 l68 10" stroke="#c9a37a" stroke-width="5" stroke-linecap="round"/>
</svg>"""


def scene(sc, bubble, mouth, blink, handle):
    d, col, cname = MA.LINE[sc["cat"]]
    return MA.page(1080, 1920, f"""<div style="width:1080px;height:1920px;background:linear-gradient(#eef3ff,#f7f9fc 55%,#e6ecf7);position:relative;overflow:hidden">
<div style="position:absolute;left:80px;right:80px;top:150px;display:flex;align-items:center;gap:20px;font-size:38px;font-weight:700;color:{MA.MUTED}">{MA.badge(sc["cat"], 66)}<span>{cname} · {MA.esc(sc["title"])}</span></div>
<div style="position:absolute;left:70px;right:70px;top:270px;min-height:560px;background:#fff;border-radius:48px;padding:56px 60px;box-shadow:0 10px 0 rgba(31,79,209,.12);display:flex;flex-direction:column;gap:28px;justify-content:center">{bubble}
<div style="position:absolute;left:50%;bottom:-46px;transform:translateX(-50%);width:0;height:0;border-left:46px solid transparent;border-right:46px solid transparent;border-top:50px solid #fff"></div></div>
<div style="position:absolute;left:0;right:0;bottom:250px;display:flex;justify-content:center">{tori(mouth, blink)}</div>
<div style="position:absolute;left:0;right:0;bottom:170px;text-align:center;font-size:40px;font-weight:800;color:{col}">출근길 고양이 토리</div>
<div style="position:absolute;left:80px;bottom:90px;font-size:32px;color:{MA.MUTED};font-weight:600">🚇 {MA.esc(handle)} · 🔊 AI 음성</div></div>""")


def build(chrome, sc, wavs, out_mp4, cover_jpg, handle, gl, ffmpeg):
    """sc: 게시용 장면(날짜는 실제 게시일). wavs: 문장 3개의 24kHz wav 경로."""
    tmp = Path(out_mp4).parent / "_f"; tmp.mkdir(exist_ok=True)
    s = sc["steps"]
    bubbles = {"hook": f'<div style="font-size:44px;font-weight:700;color:{MA.BLUE}">오늘의 장면</div><div style="font-size:66px;font-weight:900;line-height:1.35">{MA.esc(sc["scene"].split(". ")[0].rstrip("."))}.</div><div style="font-size:52px;font-weight:800">이럴 때 영어로 뭐라고 할까? 🤔</div>'}
    for i, x in enumerate(s):
        bubbles[f"q{i}"] = f'<div style="font-size:42px;font-weight:800;color:{MA.BLUE}">{i + 1} / 3 · {MA.esc(x["q"])}</div><div style="font-size:72px;font-weight:900;line-height:1.35">“{MA.esc(x["ko"])}”</div><div style="font-size:48px;font-weight:700;color:{MA.MUTED}">토리가 영어로 말해 볼게요 👂</div>'
        bubbles[f"a{i}"] = f'<div style="font-size:42px;font-weight:800;color:{MA.BLUE}">{i + 1} / 3 · 🔁 듣고 따라 해 보세요</div><div style="font-size:74px;font-weight:800;line-height:1.3">{MA.mark(x["en"], MA.gloss_spans(x["en"], gl))}</div><div style="font-size:46px;line-height:1.4">{MA.esc(x["ko"])}</div>'
    bubbles["end"] = '<div style="font-size:58px;font-weight:900;line-height:1.4">오늘 3문장, 저장해두고<br>출근길에 같이 말해요 📌</div><div style="font-size:44px;color:#5f6878">🎙️ 내 발음 점수는 프로필 링크</div>'
    sil = lambda sec: np.zeros(int(SR * sec), dtype=np.float32)
    voice = [sf.read(w, dtype="float32")[0] for w in wavs]
    segs, track = [("hook", 2.8)], [sil(2.8)]
    for i, v in enumerate(voice):
        segs.append((f"q{i}", 1.8)); track.append(sil(1.8))
        a = np.concatenate([sil(0.2), v, sil(max(1.8, len(v) / SR)), sil(0.3)])
        segs.append((f"a{i}", len(a) / SR)); track.append(a)
    segs.append(("end", 3.0)); track.append(sil(3.0))
    audio = np.concatenate(track); sf.write(tmp / "voice.wav", audio, SR)
    n = int(len(audio) / SR * FPS); hop = SR // FPS
    rms = np.array([np.sqrt(np.mean(audio[k * hop:(k + 1) * hop] ** 2) + 1e-12) for k in range(n)])
    peak = np.percentile(rms[rms > 1e-4], 95) if (rms > 1e-4).any() else 1
    mouth = np.where(rms < peak * 0.12, 0, np.where(rms < peak * 0.5, 1, 2))
    blink = np.array([(k % 96) in (90, 91, 92, 93) for k in range(n)])
    bounds, t = [], 0.0
    for name, sec in segs:
        bounds.append((name, int(round(t * FPS)), int(round((t + sec) * FPS)))); t += sec
    need, frames = set(), []
    for name, a, b in bounds:
        for k in range(a, min(b, n)):
            key = (name, int(mouth[k]), bool(blink[k])); need.add(key); frames.append(key)
    for name, m, bl in sorted(need):
        MA.shot(chrome, scene(sc, bubbles[name], m, bl, handle), tmp / f"{name}_{m}_{int(bl)}.png", 1080, 1920)
    with open(tmp / "list.txt", "w", encoding="utf-8") as f:
        prev, cnt = None, 0
        for key in frames + [None]:
            if key == prev:
                cnt += 1; continue
            if prev is not None:
                f.write(f"file '{(tmp / f'{prev[0]}_{prev[1]}_{int(prev[2])}.png').as_posix()}'\nduration {cnt / FPS:.4f}\n")
            prev, cnt = key, 1
        last = frames[-1]
        f.write(f"file '{(tmp / f'{last[0]}_{last[1]}_{int(last[2])}.png').as_posix()}'\n")
    total = len(audio) / SR
    bgm = sorted(MUSIC.glob("*.m4a"))[sc["day"] % 6]
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"), "-i", str(tmp / "voice.wav"),
                    "-stream_loop", "-1", "-i", str(bgm), "-filter_complex",
                    f"[1:a]aresample=48000[v];[2:a]aresample=48000,volume=0.08,afade=t=out:st={total - 1.5:.2f}:d=1.5[b];[v][b]amix=inputs=2:duration=first:normalize=0[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
                    "-t", f"{total:.2f}", "-movflags", "+faststart", str(out_mp4)], check=True)
    Image.open(tmp / "hook_0_0.png").convert("RGB").save(cover_jpg, quality=92)
    shutil.rmtree(tmp)
    return total
