#!/usr/bin/env python3
"""回測：美股主題訊號 → 台股同主題之後的表現（batch21，不改網站）
資料：台股 data/hist/*.json（2025-05-28 起日收盤）＋ data/adj.json（2026-03 起除權息；2025 年用 2026 同期因子近似）
     美股 us/data/ohlc/*.json（日 K，分割調整）、us/data/earnings_auto.json（hist：公布日、驚喜率、首日反應）、us/data/{T}.json（季營收）
主題：data/themes.json 有 us 欄的 27 個（用今天的成份股回推，有後見之明）
"""
import json, glob, os, sys, math, statistics as st, datetime as dt, bisect, random
R = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda p: json.load(open(os.path.join(R, p), encoding='utf-8'))
TH = [t for t in J('data/themes.json')['themes'] if t.get('us')]

# ---------- 台股日收盤（還原） ----------
TW = {}
files = sorted(glob.glob(os.path.join(R, 'data/hist/*.json')))
TD = []
for f in files:
    j = J(f)
    if 'p' not in j: continue   # 休市日
    d = os.path.basename(f)[:8]; d = f'{d[:4]}-{d[4:6]}-{d[6:]}'; TD.append(d)
    for c, v in j['p'].items():
        if v and v[0]: TW.setdefault(c, {})[d] = v[0]
adj = J('data/adj.json')['ev']
def adjfac(c, d):
    f = 1.0
    for ed, k, *_ in adj.get(c, []):
        e = f'{ed[:4]}-{ed[4:6]}-{ed[6:]}'
        if d < e: f *= k
        pe = f'{int(ed[:4]) - 1}-{ed[4:6]}-{ed[6:]}'   # 2025 年同期近似
        if pe >= TD[0] and pe < '2026-03-06' and d < pe: f *= k
    return f
TWA = {c: {d: p * adjfac(c, d) for d, p in s.items()} for c, s in TW.items() if any(c in [x[0] for x in t['stocks']] for t in TH)}

# ---------- 美股日收盤 ----------
US = {}
for t in {u for th in TH for u in th['us']}:
    p = os.path.join(R, f'us/data/ohlc/{t}.json')
    if os.path.exists(p): US[t] = {r[0]: r[4] for r in J(f'us/data/ohlc/{t}.json')['k'] if r[4]}
def px_on_or_before(s, d, strict=False):
    ks = sorted(s) if not hasattr(s, '_k') else s._k
    i = bisect.bisect_left(ks, d) if strict else bisect.bisect_right(ks, d)
    return (ks[i - 1], s[ks[i - 1]]) if i > 0 else (None, None)
class S(dict):
    pass
for dct in (TWA, US):
    for k in list(dct):
        s = S(dct[k]); s._k = sorted(s); dct[k] = s
def ret(s, a, b, strict_b=False):
    da, pa = px_on_or_before(s, a, strict=strict_b)
    db, pb = px_on_or_before(s, b, strict=strict_b)
    if not pa or not pb or da == db or da is None: return None
    if (dt.date.fromisoformat(a) - dt.date.fromisoformat(da)).days > 7: return None
    return (pb / pa - 1) * 100
def addm(d, m):
    y, mo, dd = map(int, d.split('-')); mo += m
    while mo > 12: mo -= 12; y += 1
    while mo < 1: mo += 12; y -= 1
    import calendar
    return f'{y}-{mo:02d}-{min(dd, calendar.monthrange(y, mo)[1]):02d}'
med = lambda a: st.median(a) if a else None
def tw_theme(t, a, b):
    v = [r for c, _ in [x[:2] for x in t['stocks']] if c in TWA for r in [ret(TWA[c], a, b)] if r is not None]
    return med(v) if len(v) * 2 >= len(t['stocks']) else None
def us_theme(t, a, b):   # 美股：嚴格早於台股該日（美股收盤在台股收盤之後）
    v = [r for u in t['us'] if u in US for r in [ret(US[u], a, b, strict_b=True)] if r is not None]
    return med(v) if len(v) * 2 >= len(t['us']) else None
def spearman(x, y):
    n = len(x)
    if n < 5: return None
    rk = lambda v: {i: r for r, i in enumerate(sorted(range(n), key=lambda i: v[i]))}
    a, b = rk(x), rk(y)
    return 1 - 6 * sum((a[i] - b[i]) ** 2 for i in range(n)) / (n * (n * n - 1))

LAST = TD[-1]
# 月底訊號日（台股最後交易日）
ME = []
for i, d in enumerate(TD):
    if i + 1 == len(TD) or TD[i + 1][:7] != d[:7]: ME.append(d)
ME = [d for d in ME if d >= addm(TD[0], 1)]

def monthly(h):
    rows = []
    for t0 in ME:
        t1 = addm(t0, h)
        if t1 > LAST: continue
        r = []
        for t in TH:
            a = {'th': t['id'], 'usm': us_theme(t, addm(t0, -1), t0), 'twm': tw_theme(t, addm(t0, -1), t0), 'fw': tw_theme(t, t0, t1)}
            if None not in a.values(): r.append(a)
        if len(r) >= 10:
            mu = st.mean(x['fw'] for x in r)
            for x in r: x['ex'] = x['fw'] - mu; x['gap'] = x['usm'] - x['twm']; x['t0'] = t0
            rows.append(r)
    return rows

def evalsig(rows, k):
    ics, spr = [], []
    for r in rows:
        ic = spearman([x[k] for x in r], [x['ex'] for x in r]); ics.append(ic)
        s = sorted(r, key=lambda x: x[k]); n = len(s) // 3
        spr.append(st.mean(x['ex'] for x in s[-n:]) - st.mean(x['ex'] for x in s[:n]))
    m = st.mean(ics); sd = st.stdev(ics) if len(ics) > 1 else 0
    return dict(n=len(ics), ic=m, t=m / sd * math.sqrt(len(ics)) if sd else None, hit=sum(i > 0 for i in ics) / len(ics), spr=st.mean(spr), sprw=sum(x > 0 for x in spr) / len(spr))

out = {'window': [TD[0], LAST], 'themes': len(TH), 'months': len(ME)}
for h in (1, 3):
    rows = monthly(h)
    out[f'h{h}'] = {k: evalsig(rows, k) for k in ('usm', 'twm', 'gap')}
    # 置換檢定（打亂主題對應，看 usm IC 的隨機分布）
    random.seed(1); obs = out[f'h{h}']['usm']['ic']; cnt = 0; N = 2000
    for _ in range(N):
        ics = []
        for r in rows:
            ex = [x['ex'] for x in r]; random.shuffle(ex)
            ics.append(spearman([x['usm'] for x in r], ex))
        if abs(st.mean(ics)) >= abs(obs): cnt += 1
    out[f'h{h}']['usm']['perm_p'] = cnt / N
    random.seed(2); obs = out[f'h{h}']['gap']['ic']; cnt = 0
    for _ in range(N):
        ics = []
        for r in rows:
            ex = [x['ex'] for x in r]; random.shuffle(ex)
            ics.append(spearman([x['gap'] for x in r], ex))
        if abs(st.mean(ics)) >= abs(obs): cnt += 1
    out[f'h{h}']['gap']['perm_p'] = cnt / N
    if h == 1: ROWS1 = rows

# ---------- 同主題時間序列：美股本月 vs 台股下月（不扣大盤）----------
xs, ys = [], []
for r in ROWS1:
    for x in r: xs.append(x['usm']); ys.append(x['fw'])
out['pooled_usm_vs_twnext_raw_spearman'] = spearman(xs, ys)

# ---------- 同期（同一個月）連動：美股本月 vs 台股本月 ----------
ics = [spearman([x['usm'] for x in r], [x['twm'] for x in r]) for r in ROWS1]
out['same_month_ic'] = st.mean(ics)

# ---------- 隔日傳導：美股主題日報酬 → 台股主題隔日報酬 ----------
def daily_theme(t, src, days, members):
    res = {}
    for i in range(1, len(days)):
        a, b = days[i - 1], days[i]
        v = [(src[m][b] / src[m][a] - 1) * 100 for m in members if m in src and a in src[m] and b in src[m]]
        if len(v) * 2 >= len(members): res[b] = st.median(v)
    return res
USD = sorted({d for s in US.values() for d in s if d >= TD[0]})
lag = {0: [], 1: [], 2: []}
for t in TH:
    ud = daily_theme(t, US, USD, t['us']); twd = daily_theme(t, TWA, TD, [x[0] for x in t['stocks']])
    tws = sorted(twd)
    for L in (1, 2):
        pairs = []
        for d, v in ud.items():
            i = bisect.bisect_right(tws, d)   # 台股在美股該日之後的第 L 個交易日
            if i + L - 1 < len(tws): pairs.append((v, twd[tws[i + L - 1]]))
        if len(pairs) > 50: lag[L].append(st.correlation(*zip(*pairs)))
    pairs = [(ud[d], twd[d]) for d in ud if d in twd]   # 同一日曆日（台股先收盤，美股後收盤）
    if len(pairs) > 50: lag[0].append(st.correlation(*zip(*pairs)))
out['daily_corr'] = {f'lag{L}': (st.mean(v), len(v)) for L, v in lag.items()}

# ---------- 財報季燈號（重建）→ 台股之後 1／3 月 ----------
AUTO = J('us/data/earnings_auto.json')['q']
def stock_sig(u, sd):
    lo = (dt.date.fromisoformat(sd) - dt.timedelta(days=95)).isoformat()
    rows = [r for r in (AUTO.get(u) or {}).get('hist') or [] if r[4] and lo < r[4] <= sd]
    r = rows[-1] if rows else None
    surp = r[3] if r else None; react = r[6] if r and len(r) > 6 else None
    racc = None
    p = os.path.join(R, f'us/data/{u}.json')
    if os.path.exists(p):
        d = J(f'us/data/{u}.json')
        if d.get('freq') == 'Q':
            q = [x for x in d['q'] if x[10] and x[10] <= sd]
            by = {x[0]: x for x in q}
            def yoy(x):
                pp = by.get(f'{int(x[0][:2]) - 1:02d}{x[0][2:]}')
                return (x[2] / pp[2] - 1) * 100 if pp and pp[2] and pp[2] > 0 and x[2] is not None else None
            if len(q) >= 2 and q[-1][10] > lo:
                a, b = yoy(q[-1]), yoy(q[-2])
                if a is not None and b is not None: racc = a - b
    return racc, surp, react
def light(t, sd):
    N = len(t['us']); S = [stock_sig(u, sd) for u in t['us']]; c = []
    for i in range(3):
        v = [s[i] for s in S if s[i] is not None]
        c.append(st.median(v) if v and len(v) * 2 >= N else None)
    av = [x for x in c if x is not None]
    if len(av) < 2: return '⚪', c
    pos = sum(x > 0 for x in av)
    return ('🟢' if pos == len(av) else '🔴' if pos == 0 else '🟡'), c
SEAS = [d for d in ME if d[5:7] in ('02', '05', '08', '11')]
eg = {}
for sd in SEAS:
    for h in (1, 3):
        t1 = addm(sd, h)
        if t1 > LAST: t1 = LAST
        if dt.date.fromisoformat(t1) - dt.date.fromisoformat(sd) < dt.timedelta(days=20): continue
        r = []
        for t in TH:
            lt, c = light(t, sd); fw = tw_theme(t, sd, t1)
            if fw is not None: r.append((t['id'], lt, fw, c))
        if not r: continue
        mu = st.mean(x[2] for x in r)
        for th, lt, fw, c in r: eg.setdefault(h, []).append(dict(sd=sd, th=th, lt=lt, ex=fw - mu, fw=fw, full=t1 == addm(sd, h)))
out['light'] = {}
for h, rs in eg.items():
    g = {}
    for x in rs: g.setdefault(x['lt'], []).append(x['ex'])
    out['light'][h] = {k: (round(st.mean(v), 2), len(v), round(sum(e > 0 for e in v) / len(v), 2)) for k, v in g.items()}
    out['light'][f'{h}_seasons'] = sorted({(x['sd'], x['full']) for x in rs})
    by = {}
    for x in rs: by.setdefault(x['sd'], {}).setdefault(x['lt'], []).append(x['ex'])
    out['light'][f'{h}_byseason'] = {sd: {k: (round(st.mean(v), 1), len(v)) for k, v in d.items()} for sd, d in by.items()}
json.dump(out, open(os.path.join(R, 'tools/backtest_us_tw_result.json'), 'w'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
