// commute-english-bot — 출근길 영어(@commute.english.kr) 자동 게시.
// 승인 없이 매일 06:00 KST 부터 5분마다 확인해서:
//   1) 카드뉴스(캐러셀)를 올리고  2) 릴스 컨테이너를 만든 뒤  3) 영상 처리가 끝나면 릴스를 올린다.
// 게시물 파일은 GitHub Actions 가 전날 20:00 KST 에 https://ssong032.github.io/commute-english-cards/posts/<날짜>/ 에 올려둔다.
// 멈추기: /pause?k=비밀값  (다시 시작: /resume?k=비밀값). 상태 보기: /status?k=비밀값
// Secrets: IG_ACCESS_TOKEN(페이지 토큰, 만료 없음), IG_USER_ID, WEBHOOK_SECRET

const IG = "https://graph.facebook.com/v23.0";
const MEDIA = "https://ssong032.github.io/commute-english-cards/posts";
const KST = 9 * 3600 * 1000;
const PUBLISH_HOUR = 6;      // 06:00 KST 부터 게시
const REEL_TIMEOUT_MIN = 45; // 릴스 영상 처리 대기 한도
const MAX_ERRORS = 4;        // 같은 날 오류가 이만큼 쌓이면 그날은 멈춤 (중복 게시 방지)

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function kstNow() { const d = new Date(Date.now() + KST); return { ymd: d.toISOString().slice(0, 10), hour: d.getUTCHours() }; }
async function getPost(env, ymd) { return JSON.parse((await env.STATE.get(`post:${ymd}`)) || "{}"); }
async function putPost(env, ymd, p) { await env.STATE.put(`post:${ymd}`, JSON.stringify(p), { expirationTtl: 60 * 60 * 24 * 40 }); }

async function igCall(url, params, method = "POST") {
  const body = new URLSearchParams(params);
  const r = method === "POST" ? await fetch(url, { method, body }) : await fetch(`${url}?${body}`);
  const j = await r.json();
  if (j.error) {
    const e = j.error, extra = [e.error_user_title, e.error_user_msg].filter(Boolean).join(": ");
    throw new Error(`${e.message || "IG error"} (${e.code || r.status}${e.error_subcode ? "/" + e.error_subcode : ""})${extra ? " - " + extra : ""}`);
  }
  return j;
}
async function manifest(ymd) {
  const r = await fetch(`${MEDIA}/${ymd}/manifest.json?t=${Date.now()}`, { cf: { cacheTtl: 0 } });
  if (!r.ok) return null;
  return await r.json();
}
async function permalink(env, id) {
  try { return (await igCall(`${IG}/${id}`, { fields: "permalink", access_token: env.IG_ACCESS_TOKEN }, "GET")).permalink; }
  catch (e) { return "(링크 확인 실패 · 게시는 완료)"; } // 이미 게시됨: 다시 시도하면 중복 게시되므로 오류로 두지 않는다
}
async function publishCarousel(env, ymd, m) {
  const t = env.IG_ACCESS_TOKEN, uid = env.IG_USER_ID, kids = [];
  for (const f of m.cards.slice(0, 10)) {
    const c = await igCall(`${IG}/${uid}/media`, { image_url: `${MEDIA}/${ymd}/${f}`, is_carousel_item: "true", access_token: t });
    kids.push(c.id);
  }
  const car = await igCall(`${IG}/${uid}/media`, { media_type: "CAROUSEL", children: kids.join(","), caption: m.caption, access_token: t });
  for (let i = 0; i < 10; i++) {
    const s = await igCall(`${IG}/${car.id}`, { fields: "status_code", access_token: t }, "GET");
    if (s.status_code === "FINISHED") break;
    if (s.status_code === "ERROR" || s.status_code === "EXPIRED") throw new Error(`카드 컨테이너 ${s.status_code}`);
    await sleep(4000);
  }
  const pub = await igCall(`${IG}/${uid}/media_publish`, { creation_id: car.id, access_token: t });
  return await permalink(env, pub.id);
}
async function startReel(env, ymd, m) {
  const c = await igCall(`${IG}/${env.IG_USER_ID}/media`, {
    media_type: "REELS", video_url: `${MEDIA}/${ymd}/${m.reel}`, caption: m.reel_caption,
    cover_url: `${MEDIA}/${ymd}/reel_cover.jpg`, share_to_feed: "true", access_token: env.IG_ACCESS_TOKEN,
  });
  return c.id;
}
async function checkReel(env, cid) { // 처리 중이면 null, 게시되면 링크
  const s = await igCall(`${IG}/${cid}`, { fields: "status_code,status", access_token: env.IG_ACCESS_TOKEN }, "GET");
  if (s.status_code === "ERROR" || s.status_code === "EXPIRED") throw new Error(`릴스 처리 실패 (${s.status_code}${s.status ? ": " + s.status : ""})`);
  if (s.status_code !== "FINISHED") return null;
  const pub = await igCall(`${IG}/${env.IG_USER_ID}/media_publish`, { creation_id: cid, access_token: env.IG_ACCESS_TOKEN });
  return await permalink(env, pub.id);
}

async function tick(env, force = false) {
  if (await env.STATE.get("paused")) return "paused";
  if (!env.IG_ACCESS_TOKEN || !env.IG_USER_ID) return "no token";
  const { ymd, hour } = kstNow();
  if (hour < PUBLISH_HOUR && !force) return "before 06:00";
  const p = await getPost(env, ymd);
  if (p.done) return "done";
  try {
    const m = await manifest(ymd);
    if (!m) { p.last_err = "게시물 파일이 아직 없어요 (GitHub Actions 확인)"; await putPost(env, ymd, p); return p.last_err; }
    if (!p.cards) { p.cards = await publishCarousel(env, ymd, m); p.cards_at = new Date().toISOString(); await putPost(env, ymd, p); }
    if (!p.reel_cid) { p.reel_cid = await startReel(env, ymd, m); p.reel_started = Date.now(); await putPost(env, ymd, p); return "reel started"; }
    if (!p.reel) {
      const link = await checkReel(env, p.reel_cid);
      if (!link) {
        if (Date.now() - p.reel_started > REEL_TIMEOUT_MIN * 60000) throw new Error("릴스 영상 처리 시간 초과");
        return "reel processing";
      }
      p.reel = link; p.reel_at = new Date().toISOString();
    }
    p.done = true; await putPost(env, ymd, p);
    return "posted";
  } catch (e) {
    p.errors = (p.errors || 0) + 1; p.last_err = String(e.message || e);
    if (p.errors >= MAX_ERRORS) p.done = true; // 그날은 포기 (다음 날 다시)
    if (String(p.last_err).includes("릴스")) { p.reel_cid = p.done ? p.reel_cid : null; }
    await putPost(env, ymd, p);
    return "error: " + p.last_err;
  }
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (!env.WEBHOOK_SECRET || url.searchParams.get("k") !== env.WEBHOOK_SECRET) return new Response("ok");
    const json = (o) => new Response(JSON.stringify(o, null, 1), { headers: { "content-type": "application/json; charset=utf-8" } });
    if (url.pathname === "/status") {
      const out = { paused: !!(await env.STATE.get("paused")), now_kst: kstNow(), token: !!env.IG_ACCESS_TOKEN, days: {} };
      for (let i = 0; i < 7; i++) {
        const d = new Date(Date.now() + KST - i * 86400000).toISOString().slice(0, 10);
        const p = await getPost(env, d); if (Object.keys(p).length) out.days[d] = p;
      }
      return json(out);
    }
    if (url.pathname === "/pause") { await env.STATE.put("paused", new Date().toISOString()); return json({ paused: true }); }
    if (url.pathname === "/resume") { await env.STATE.delete("paused"); return json({ paused: false }); }
    if (url.pathname === "/check") { // 게시 없이 연결·파일만 확인
      const d = url.searchParams.get("d") || kstNow().ymd, m = await manifest(d), r = { date: d, manifest: !!m };
      if (m) {
        r.files = {};
        for (const f of [...m.cards, m.reel, "reel_cover.jpg"]) { const h = await fetch(`${MEDIA}/${d}/${f}`, { method: "HEAD" }); r.files[f] = `${h.status} ${h.headers.get("content-type")}`; }
      }
      if (env.IG_ACCESS_TOKEN && env.IG_USER_ID) {
        try { r.ig = await igCall(`${IG}/${env.IG_USER_ID}`, { fields: "username,media_count", access_token: env.IG_ACCESS_TOKEN }, "GET"); }
        catch (e) { r.ig_error = String(e.message || e); }
      }
      return json(r);
    }
    if (url.pathname === "/run") return json({ result: await tick(env, url.searchParams.get("force") === "1") });
    return new Response("ok");
  },
  async scheduled(event, env, ctx) { ctx.waitUntil(tick(env)); },
};
