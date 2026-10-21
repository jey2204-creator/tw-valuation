// Cloudflare Worker：即時行情轉接（給 GitHub Pages「即時看線」itrust/live/ 用）
// 來源：證交所 MIS（即時）為主；證交所擋掉 Cloudflare 時（盤中常見，依機房不同）改用 Yahoo Finance 備援（約延遲 20 分鐘）。
// 用法：GET https://<你的 worker>.workers.dev/?s=tse_2330,otc_6510,tse_t00
//   tse_＝上市、otc_＝上櫃；tse_t00＝加權指數。一次最多 40 檔（頁面每 20 檔發一次）。
//   選填 &src=mis 或 &src=yahoo：只用指定來源（測試用）。
// 回傳：{ok, t, n, q:[{k,c,n,d,t,ms,z,pz,o,h,l,y,v,u,w,a1,b1,src}], err, src:{mis,yahoo}}
//   d＝資料日期 YYYYMMDD、t＝資料時間；z＝最新成交價（沒有就 null，頁面會改用買賣價），v＝累計成交量（張）；src＝每檔的來源
// 只轉接公開行情，不需要任何金鑰。部署：Cloudflare 後台 → Workers & Pages → 建立 → Hello World → 編輯程式碼 → 貼上本檔 → Deploy。
// 目前部署在 https://twse-live.jey2204.workers.dev（2026/10/21；後台貼的是本檔去掉註解的單行版本，功能相同）。
// 免費方案每次請求最多 50 個對外連線：MIS 最多 3 次＋Yahoo 每檔 1 次，所以一次最多 40 檔。

const ALLOW_ORIGINS = ["https://jey2204-creator.github.io"];   // 只讓自己的 GitHub Pages 頁面在瀏覽器裡呼叫
const MAX_SYMBOLS = 40;
const MEMO_MS = 4000;          // 同一組代號 4 秒內重複查詢就直接回上一次的結果，減少打證交所
const MIS_MS = 5000;           // 證交所每次連線最多等 5 秒：盤後它常常掛住 20 秒才回，超時就改用 Yahoo
const YH_MS = 8000;
const memo = new Map();

const UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1";
const BASE_HEADERS = {
  "User-Agent": UA,
  "Accept": "application/json, text/javascript, */*; q=0.01",
  "Accept-Language": "zh-TW,zh;q=0.9",
  "Referer": "https://mis.twse.com.tw/stock/fibest.jsp?lang=zh_tw",
};

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const cors = corsHeaders(request.headers.get("Origin") || "");
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (request.method !== "GET") return json({ ok: false, err: "GET only" }, 405, cors);

    const raw = (url.searchParams.get("s") || "").toLowerCase().split(",").map((x) => x.trim()).filter(Boolean);
    const syms = [...new Set(raw)].filter((x) => /^(tse|otc)_[0-9a-z]{2,6}$/.test(x)).slice(0, MAX_SYMBOLS);
    if (!syms.length) {
      return json({ ok: false, err: "no symbols", usage: "?s=tse_2330,otc_6510,tse_t00" }, 400, cors);
    }
    const src = url.searchParams.get("src") || "";   // "mis" | "yahoo" | ""（自動：MIS 失敗才用 Yahoo）

    const key = src + "|" + [...syms].sort().join(",");
    const hit = memo.get(key);
    if (hit && Date.now() - hit.at < MEMO_MS) return json(hit.body, 200, { ...cors, "X-Memo": "hit" });

    const q = [], err = [];
    if (src !== "yahoo") {
      try {
        q.push(...(await mis(syms)));
      } catch (e) {
        err.push("MIS: " + String((e && e.message) || e));
      }
    }
    const got = new Set(q.map((x) => x.k));
    const pending = syms.filter((s) => !got.has(s));
    if (pending.length && src !== "mis") {
      const rows = await Promise.all(pending.map((s) => yahoo(s).catch((e) => { err.push("Yahoo " + s + ": " + String((e && e.message) || e)); return null; })));
      q.push(...rows.filter(Boolean));
    }
    const body = { ok: q.length > 0, t: Date.now(), n: q.length, q, err,
      src: { mis: q.filter((x) => x.src === "mis").length, yahoo: q.filter((x) => x.src === "yahoo").length } };
    if (q.length) {
      memo.set(key, { at: Date.now(), body });
      if (memo.size > 200) memo.delete(memo.keys().next().value);
    }
    return json(body, q.length ? 200 : 502, cors);
  },
};

// 證交所 MIS：一次查全部（最多 40 檔）；沒資料時先到首頁拿 session cookie 再試一次
async function mis(part) {
  const exch = part.map((s) => s + ".tw").join("|");
  const u = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=" + encodeURIComponent(exch) + "&json=1&delay=0&_=" + Date.now();
  let r = null, js = null;
  try {
    r = await fetch(u, { headers: BASE_HEADERS, signal: AbortSignal.timeout(MIS_MS) });
    js = await safeJson(r);
  } catch (e) { /* 連線被切斷或超時，下面用 cookie 再試一次 */ }
  if (!js || !Array.isArray(js.msgArray) || js.msgArray.length === 0) {
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
