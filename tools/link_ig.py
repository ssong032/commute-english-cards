# -*- coding: utf-8 -*-
"""@commute.english.kr 연결: 바탕화면\\클로드\\tokens.txt 의 IG_USER_TOKEN(연장한 사용자 토큰)으로
만료 없는 페이지 토큰을 만들어 Cloudflare Worker(commute-english-bot) secret 에 넣는다.
토큰 값은 절대 출력하지 않는다. 끝나면 tokens.txt 에서 IG_USER_TOKEN 줄만 지운다.
실행: python -X utf8 tools/link_ig.py
"""
import json, os, subprocess, sys, tempfile, time, urllib.parse, urllib.request
from pathlib import Path

TOKENS = Path(os.path.expanduser("~")) / "Desktop" / "클로드" / "tokens.txt"
WORKER = Path(__file__).resolve().parent.parent / "worker"
G = "https://graph.facebook.com/v23.0"
WANT = "commute.english.kr"


def get(path, **params):
    url = f"{G}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        j = json.load(e)
        sys.exit(f"Graph 오류: {j.get('error', {}).get('message', e)}")


def main():
    lines = TOKENS.read_text(encoding="utf-8").splitlines()
    ut = next((l.split("=", 1)[1].strip() for l in lines if l.strip().startswith("IG_USER_TOKEN")), "")
    if not ut:
        sys.exit("tokens.txt 에 IG_USER_TOKEN= 줄이 없어요")
    dbg = get("debug_token", input_token=ut, access_token=ut)["data"]
    exp = dbg.get("expires_at", 0)
    print("사용자 토큰:", dbg.get("type"), "· 앱", dbg.get("app_id"), "· 만료", "없음" if not exp else time.strftime("%Y-%m-%d %H:%M", time.localtime(exp)))
    if exp and exp - time.time() < 7 * 86400:
        print("⚠️ 짧은 토큰이에요. Access Token Tool 에서 'Extend Access Token' 한 토큰이어야 만료 없는 페이지 토큰이 나와요.")
    ids = set()
    for g in dbg.get("granular_scopes", []):
        if g["scope"].startswith("pages_"):
            ids.update(g.get("target_ids", []))
    try:  # 비즈니스 로그인 앱은 me/accounts 가 비어 오기도 해서 보조로만 쓴다
        ids.update(a["id"] for a in get("me/accounts", fields="id", access_token=ut).get("data", []))
    except SystemExit:
        pass
    found = None
    for pid in sorted(ids):
        p = get(pid, fields="name,access_token,instagram_business_account{id,username}", access_token=ut)
        ig = p.get("instagram_business_account") or {}
        print(f"  페이지 {p.get('name')} ({pid}) → 인스타 {ig.get('username', '연결 없음')}")
        if ig.get("username") == WANT:
            found = (pid, p["access_token"], ig["id"])
    if not found:
        sys.exit(f"{WANT} 와 연결된 페이지를 못 찾았어요. 인스타가 프로페셔널 계정인지, 페이지와 연결됐는지, 권한 창에서 그 페이지를 체크했는지 확인해 주세요.")
    pid, pt, igid = found
    pd = get("debug_token", input_token=pt, access_token=pt)["data"]
    print("페이지 토큰 만료:", "없음 ✅" if not pd.get("expires_at") else time.strftime("%Y-%m-%d %H:%M", time.localtime(pd["expires_at"])))
    me = get(igid, fields="username,media_count", access_token=pt)
    print("인스타 확인:", me.get("username"), "· 게시물", me.get("media_count"), "· IG id", igid)
    fd, tmp = tempfile.mkstemp(suffix=".json", dir=WORKER)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"IG_ACCESS_TOKEN": pt, "IG_USER_ID": igid}, f)
    try:
        r = subprocess.run("npx wrangler secret bulk " + Path(tmp).name, cwd=WORKER, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print("Worker secret:", "OK" if r.returncode == 0 else "실패\n" + r.stdout[-400:] + r.stderr[-400:])
    finally:
        os.remove(tmp)
    TOKENS.write_text("\n".join(l for l in lines if not l.strip().startswith("IG_USER_TOKEN")) + "\n", encoding="utf-8")
    print("tokens.txt 에서 IG_USER_TOKEN 줄을 지웠어요.")


if __name__ == "__main__":
    main()
