// Cloudflare Worker：即時行情轉接（給 GitHub Pages「即時看線」itrust/live/ 用）
// 來源（依序）：證交所 MIS（即時）→ 富果 Fugle 行情 API（即時，免費 60 次／分）→ Yahoo Finance（約延遲 20 分鐘）。
//   證交所盤中常擋 Cloudflare 機房：MIS 失敗後 3 分鐘內直接跳過，不再每次白等 5～15 秒。
//   富果：每檔 1 次請求，結果快取 50 秒（多人／多分頁共用）；每分鐘自己限 54 次，頁面目前分頁（&p=1）優先用，
//   其他分頁只在額度還剩 >24 次時才用富果，超過就改 Yahoo；收到 429 停用富果 60 秒。
//   富果金鑰放在 Worker secret FUGLE_API_KEY（GitHub Secret 同名，由 itrust_live_worker.yml 部署時寫入）。
// 用法：GET https://<你的 worker>.workers.dev/?s=tse_2330,otc_6510,tse_t00
//   tse_＝上市、otc_＝上櫃；tse_t00＝加權指數。一次最多 40 檔（頁面每 20 檔發一次）。
//   選填 &src=mis／fugle／yahoo：只用指定來源（測試用）；&p=1：目前分頁（富果優先）。
// 回傳：{ok, t, n, q:[{k,c,n,d,t,ms,z,pz,o,h,l,y,v,u,w,a1,b1,src}], err, src:{mis,fugle,yahoo}, fb:{left,off}}
//   d＝資料日期 YYYYMMDD、t＝資料時間；z＝最新成交價（沒有就 null，頁面會改用買賣價），v＝累計成交量（張）；src＝每檔的來源
// 部署：push 到 main 後由 .github/workflows/itrust_live_worker.yml 自動部署到 https://twse-live.jey2204.workers.dev
// 免費方案每次請求最多 50 個對外連線：MIS 最多 3 次＋富果／Yahoo 每檔 1 次，程式自己算著用，超過 48 次就不再發。

const ALLOW_ORIGINS = ["https://jey2204-creator.github.io"];   // 只讓自己的 GitHub Pages 頁面在瀏覽器裡呼叫
const MAX_SYMBOLS = 40;
const MEMO_MS = 4000;          // 同一組代號 4 秒內重複查詢就直接回上一次的結果，減少打證交所
const MIS_MS = 5000;           // 證交所每次連線最多等 5 秒：盤後它常常掛住 20 秒才回，超時就改用 Yahoo
const YH_MS = 8000;
const FG_MS = 6000;
const SUB_MAX = 48;            // 每次請求最多對外連線數（免費方案上限 50，留 2 次餘裕）
const MIS_COOL_MS = 180000;    // MIS 失敗後跳過 3 分鐘
const FG_TTL_MS = 50000;       // 富果每檔結果快取 50 秒
const FG_PER_MIN = 54;         // 富果免費 60 次／分，自己限 54
const FG_RESERVE = 24;         // 非目前分頁的請求，額度要剩 >24 才用富果
const memo = new Map();
const fgCache = new Map();     // k → {at, row}
let misOffUntil = 0, fgOffUntil = 0, fgWin = 0, fgUsed = 0;

const UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1";
const BASE_HEADERS = {
  "User-Agent": UA,
  "Accept": "application/json, text/javascript, */*; q=0.01",
  "Accept-Language": "zh-TW,zh;q=0.9",
  "Referer": "https://mis.twse.com.tw/stock/fibest.jsp?lang=zh_tw",
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const cors = corsHeaders(request.headers.get("Origin") || "");
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (request.method !== "GET") return json({ ok: false, err: "GET only" }, 405, cors);

    const raw = (url.searchParams.get("s") || "").toLowerCase().split(",").map((x) => x.trim()).filter(Boolean);
    const syms = [...new Set(raw)].filter((x) => /^(tse|otc)_[0-9a-z]{2,6}$/.test(x)).slice(0, MAX_SYMBOLS);
    if (!syms.length) {
      return json({ ok: false, err: "no symbols", usage: "?s=tse_2330,otc_6510,tse_t00" }, 400, cors);
    }
    const src = url.searchParams.get("src") || "";   // "mis" | "fugle" | "yahoo" | ""（自動）
    const pri = url.searchParams.get("p") === "1";
    const key = (env && env.FUGLE_API_KEY) || "";

    const mk = src + "|" + [...syms].sort().join(",");
    const hit = memo.get(mk);
    if (hit && Date.now() - hit.at < MEMO_MS) return json(hit.body, 200, { ...cors, "X-Memo": "hit" });

    const q = [], err = [], ctx = { sub: 0 };
    const pend = () => { const got = new Set(q.map((x) => x.k)); return syms.filter((s) => !got.has(s)); };

    // 1) 證交所 MIS（最近失敗過就先跳過）
    if (src === "mis" || (!src && Date.now() >= misOffUntil)) {
      try {
        q.push(...(await mis(syms, ctx)));
        misOffUntil = 0;
      } catch (e) {
        err.push("MIS: " + String((e && e.message) || e));
        misOffUntil = Date.now() + MIS_COOL_MS;
      }
    }
    // 2) 富果
    if ((src === "fugle" || !src) && pend().length) {
      if (!key) err.push("Fugle: 沒有設定 FUGLE_API_KEY");
      else q.push(...(await fugleMany(pend(), key, pri || src === "fugle", ctx, err)));
    }
    // 3) Yahoo
    if ((src === "yahoo" || !src) && pend().length) {
      const left = pend().slice(0, Math.max(0, SUB_MAX - ctx.sub));
      if (left.length < pend().length) err.push("連線數上限：" + (pend().length - left.length) + " 檔這次沒查");
      ctx.sub += left.length;
      const rows = await Promise.all(left.map((s) => yahoo(s).catch((e) => { err.push("Yahoo " + s + ": " + String((e && e.message) || e)); return null; })));
      q.push(...rows.filter(Boolean));
    }
    const cnt = (n) => q.filter((x) => x.src === n).length;
    const body = { ok: q.length > 0, t: Date.now(), n: q.length, q, err,
      src: { mis: cnt("mis"), fugle: cnt("fugle"), yahoo: cnt("yahoo") },
      fb: { left: Math.max(0, FG_PER_MIN - fgUsedNow()), off: fgOffUntil > Date.now(), mis_off: misOffUntil > Date.now() } };
    if (q.length) {
      memo.set(mk, { at: Date.now(), body });
      if (memo.size > 200) memo.delete(memo.keys().next().value);
    }
    return json(body, q.length ? 200 : 502, cors);
  },
};

// ---- 富果 Fugle（即時，每檔 1 次請求）----
function fgUsedNow() {
  const w = Math.floor(Date.now() / 60000);
  if (w !== fgWin) { fgWin = w; fgUsed = 0; }
  return fgUsed;
}

async function fugleMany(list, key, pri, ctx, err) {
  const out = [], need = [], now = Date.now();
  for (const k of list) {
    const c = fgCache.get(k);
    if (c && now - c.at < FG_TTL_MS) out.push(c.row); else need.push(k);
  }
  if (!need.length) return out;
  if (fgOffUntil > now) { err.push("Fugle: 額度用完，暫停到 " + tpe(Math.floor(fgOffUntil / 1000)).t); return out; }
  const room = Math.max(0, FG_PER_MIN - fgUsedNow() - (pri ? 0 : FG_RESERVE));
  const take = need.slice(0, Math.min(room, Math.max(0, SUB_MAX - ctx.sub)));
  if (take.length < need.length) err.push("Fugle: 本分鐘額度留給目前分頁，" + (need.length - take.length) + " 檔改用 Yahoo");
  fgUsed += take.length; ctx.sub += take.length;
  const rows = await Promise.all(take.map((k) => fugle(k, key).catch((e) => {
    const m = String((e && e.message) || e);
    if (/^429/.test(m)) fgOffUntil = Date.now() + 60000;
    err.push("Fugle " + k + ": " + m);
    return null;
  })));
  for (const r of rows) if (r) { fgCache.set(r.k, { at: Date.now(), row: r }); out.push(r); }
  if (fgCache.size > 600) for (const [k, v] of fgCache) if (Date.now() - v.at > FG_TTL_MS) fgCache.delete(k);
  return out;
}

async function fugle(k, key) {
  const [, c] = k.split("_");
  const sym = c === "t00" ? "IX0001" : c.toUpperCase();
  const r = await fetch("https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/" + encodeURIComponent(sym),
    { headers: { "X-API-KEY": key, "Accept": "application/json" }, signal: AbortSignal.timeout(FG_MS) });
  const js = await safeJson(r);
  if (r.status !== 200 || !js || !js.symbol) throw new Error(r.status + (js && js.message ? " " + js.message : ""));
  return fugleRow(k, c, js);
}

// 富果 intraday/quote → 頁面用的欄位（時間欄位是微秒；成交量：個股為張、指數為金額不用）
function fugleRow(k, c, j) {
  const us = j.lastUpdated || (j.lastTrade && j.lastTrade.time) || j.closeTime || null;
  const sec = us ? Math.floor(epochMs(us) / 1000) : null;
  const ts = sec ? tpe(sec) : { d: j.date ? String(j.date).replace(/-/g, "") : null, t: null };
  const last = num(j.lastPrice != null ? j.lastPrice : j.closePrice);
  const trial = !!j.isTrial;
  const b1 = j.bids && j.bids[0] ? num(j.bids[0].price) : null;
  const a1 = j.asks && j.asks[0] ? num(j.asks[0].price) : null;
  const tv = j.total && j.total.tradeVolume != null ? Number(j.total.tradeVolume) : null;
  return {
    k, c, n: j.name || c, d: ts.d, t: ts.t, ms: sec ? sec * 1000 : null,
    z: trial ? null : last, pz: trial ? last : null,
    o: num(j.openPrice), h: num(j.highPrice), l: num(j.lowPrice),
    y: num(j.previousClose != null ? j.previousClose : j.referencePrice),
    v: c === "t00" ? null : Number.isFinite(tv) ? Math.round(tv) : null,
    u: num(j.priceHighLimit), w: num(j.priceLowLimit), a1, b1, src: "fugle",
  };
}
const epochMs = (x) => { const n = Number(x); return n > 1e14 ? n / 1000 : n > 1e11 ? n : n * 1000; };

// 證交所 MIS：一次查全部（最多 40 檔）；沒資料時先到首頁拿 session cookie 再試一次
async function mis(part, ctx) {
  const exch = part.map((s) => s + ".tw").join("|");
  const u = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=" + encodeURIComponent(exch) + "&json=1&delay=0&_=" + Date.now();
  let r = null, js = null;
  try {
    ctx.sub++;
    r = await fetch(u, { headers: BASE_HEADERS, signal: AbortSignal.timeout(MIS_MS) });
    js = await safeJson(r);
  } catch (e) { /* 連線被切斷或超時，下面用 cookie 再試一次 */ }
  if (!js || !Array.isArray(js.msgArray) || js.msgArray.length === 0) {
    ctx.sub += 2;
    const s = await fetch("https://mis.twse.com.tw/stock/index.jsp?lang=zh_tw", { headers: BASE_HEADERS, signal: AbortSignal.timeout(MIS_MS) });
    const all = typeof s.headers.getSetCookie === "function" ? s.headers.getSetCookie() : [s.headers.get("set-cookie") || ""];
    const cookie = all.map((c) => String(c).split(";")[0]).filter(Boolean).join("; ");
    r = await fetch(u, { headers: cookie ? { ...BASE_HEADERS, Cookie: cookie } : BASE_HEADERS, signal: AbortSignal.timeout(MIS_MS) });
    js = await safeJson(r);
  }
  if (!js || !Array.isArray(js.msgArray)) throw new Error("HTTP " + (r ? r.status : "?"));
  if (!js.msgArray.length) throw new Error("empty");
  return js.msgArray.map(pick);
}

// Yahoo Finance v8 chart（不用金鑰；台股約延遲 20 分鐘）：上市 XXXX.TW、上櫃 XXXX.TWO、加權指數 ^TWII
async function yahoo(k) {
  const [ex, c] = k.split("_");
  const ys = c === "t00" ? "^TWII" : c.toUpperCase() + (ex === "otc" ? ".TWO" : ".TW");
  const u = "https://query1.finance.yahoo.com/v8/finance/chart/" + encodeURIComponent(ys) + "?interval=1m&range=1d&includePrePost=false";
  const r = await fetch(u, { headers: { "User-Agent": UA, "Accept": "application/json" }, signal: AbortSignal.timeout(YH_MS) });
  const js = await safeJson(r);
  const res = js && js.chart && Array.isArray(js.chart.result) && js.chart.result[0];
  if (!res || !res.meta) {
    const ce = js && js.chart && js.chart.error;
    throw new Error("HTTP " + r.status + (ce ? " " + (ce.description || ce.code) : ""));
  }
  const m = res.meta, qq = (res.indicators && res.indicators.quote && res.indicators.quote[0]) || {};
  const o = (qq.open || []).find((x) => x != null);
  const highs = (qq.high || []).filter((x) => x != null), lows = (qq.low || []).filter((x) => x != null);
  const h = m.regularMarketDayHigh != null ? m.regularMarketDayHigh : highs.length ? Math.max(...highs) : null;
  const l = m.regularMarketDayLow != null ? m.regularMarketDayLow : lows.length ? Math.min(...lows) : null;
  const vol = m.regularMarketVolume != null ? m.regularMarketVolume : (qq.volume || []).reduce((a, b) => a + (b || 0), 0);
  const y = m.previousClose != null ? m.previousClose : m.chartPreviousClose;
  const ts = m.regularMarketTime ? tpe(m.regularMarketTime) : { d: null, t: null };
  return {
    k, c, n: m.shortName || m.longName || c, d: ts.d, t: ts.t, ms: m.regularMarketTime ? m.regularMarketTime * 1000 : null,
    z: num(m.regularMarketPrice), pz: null, o: num(o), h: num(h), l: num(l), y: num(y),
    v: c === "t00" ? null : vol != null ? Math.round(vol / 1000) : null,   // 股 → 張
    u: null, w: null, a1: null, b1: null, src: "yahoo",
  };
}

// epoch 秒 → 台北時間的日期與時間
function tpe(sec) {
  const d = new Date((sec + 8 * 3600) * 1000), p = (n) => String(n).padStart(2, "0");
  return { d: "" + d.getUTCFullYear() + p(d.getUTCMonth() + 1) + p(d.getUTCDate()), t: p(d.getUTCHours()) + ":" + p(d.getUTCMinutes()) + ":" + p(d.getUTCSeconds()) };
}

const num = (v) => {
  if (v == null) return null;
  const x = parseFloat(String(v).replace(/,/g, ""));
  return Number.isFinite(x) && x > 0 ? x : null;
};
const first = (s) => (typeof s === "string" ? num(s.split("_")[0]) : null);

function pick(m) {
  return {
    k: (m.ex || "") + "_" + m.c,
    c: m.c,
    n: m.n,
    d: m.d,
    t: m.t,
    ms: num(m.tlong),
    z: num(m.z),
    pz: num(m.pz),
    o: num(m.o),
    h: num(m.h),
    l: num(m.l),
    y: num(m.y),
    v: num(m.v),
    u: num(m.u),
    w: num(m.w),
    a1: first(m.a),
    b1: first(m.b),
    src: "mis",
  };
}

async function safeJson(r) {
  try {
    return JSON.parse(await r.text());
  } catch (e) {
    return null;
  }
}

function corsHeaders(origin) {
  const ok = ALLOW_ORIGINS.includes(origin) || /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin);
  return {
    "Access-Control-Allow-Origin": ok ? origin : ALLOW_ORIGINS[0],
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

function json(body, status, headers) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", ...headers },
  });
}
