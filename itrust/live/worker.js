// Cloudflare Worker：證交所 MIS 即時行情轉接（給 GitHub Pages「即時看線」itrust/live/ 用）
// 用法：GET https://<你的 worker>.workers.dev/?s=tse_2330,otc_6510,tse_t00
//   tse_＝上市、otc_＝上櫃；tse_t00＝加權指數。一次最多 120 檔，每 40 檔向證交所 MIS 發一次請求。
// 回傳：{ok, t, q:[{k,c,n,d,t,ms,z,pz,o,h,l,y,v,u,w,a1,b1}], err}
//   d＝資料日期 YYYYMMDD、t＝資料時間；z＝最新成交價（沒有就 null，頁面會改用買賣價），v＝累計成交量（張）
// 只轉接公開行情，不需要任何金鑰。部署：Cloudflare 後台 → Workers & Pages → 建立 → Hello World → 編輯程式碼 → 貼上本檔 → Deploy。

const ALLOW_ORIGINS = ["https://jey2204-creator.github.io"];   // 只讓自己的 GitHub Pages 頁面在瀏覽器裡呼叫
const MAX_SYMBOLS = 120;
const CHUNK = 40;
const MEMO_MS = 4000;          // 同一組代號 4 秒內重複查詢就直接回上一次的結果，減少打證交所
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

    const key = [...syms].sort().join(",");
    const hit = memo.get(key);
    if (hit && Date.now() - hit.at < MEMO_MS) return json(hit.body, 200, { ...cors, "X-Memo": "hit" });

    const q = [], err = [];
    for (let i = 0; i < syms.length; i += CHUNK) {
      try {
        q.push(...(await mis(syms.slice(i, i + CHUNK))));
      } catch (e) {
        err.push(String((e && e.message) || e));
      }
    }
    const body = { ok: q.length > 0, t: Date.now(), n: q.length, q, err };
    if (q.length) {
      memo.set(key, { at: Date.now(), body });
      if (memo.size > 200) memo.delete(memo.keys().next().value);
    }
    return json(body, q.length ? 200 : 502, cors);
  },
};

async function mis(part) {
  const exch = part.map((s) => s + ".tw").join("|");
  const u = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=" + encodeURIComponent(exch) + "&json=1&delay=0&_=" + Date.now();
  let r = await fetch(u, { headers: BASE_HEADERS });
  let js = await safeJson(r);
  if (!js || !Array.isArray(js.msgArray) || js.msgArray.length === 0) {
    // 有時 MIS 要先有 session cookie 才回資料：先開首頁拿 cookie 再重試一次
    const s = await fetch("https://mis.twse.com.tw/stock/index.jsp?lang=zh_tw", { headers: BASE_HEADERS });
    const all = typeof s.headers.getSetCookie === "function" ? s.headers.getSetCookie() : [s.headers.get("set-cookie") || ""];
    const cookie = all.map((c) => String(c).split(";")[0]).filter(Boolean).join("; ");
    r = await fetch(u, { headers: cookie ? { ...BASE_HEADERS, Cookie: cookie } : BASE_HEADERS });
    js = await safeJson(r);
  }
  if (!js || !Array.isArray(js.msgArray)) throw new Error("MIS HTTP " + r.status);
  return js.msgArray.map(pick);
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
