#!/usr/bin/env python3
"""長期回測（batch21 B）：2020 起月資料。美股主題近一月／美−台落差／台股自身動能／營收加速 → 台股主題未來 1、3 個月超額報酬
台股：tools/bt_data/tw_month.json（FinMind 月底還原收盤）；美股：us/data/{T}.json riv（月底收盤，分割調整、未含股息）、q（季營收＋公布日）
時點：美股月底收盤比台股月底收盤晚幾小時 → 「當月」版本有 1 天偷看；另做「跳一個月」版本（訊號月 m → 台股 m+1 月底到 m+2 月底）完全無偷看
"""
import json, os, sys, math, random, statistics as st
R = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda p: json.load(open(os.path.join(R, p), encoding='utf-8'))
TH = [t for t in J('data/themes.json')['themes'] if t.get('us')]
TWM = {c: {r[0]: r[1] for r in v} for c, v in J('tools/bt_data/tw_month.json')['d'].items()}
USM, USQ = {}, {}
for u in {u for t in TH for u in t['us']}:
    p = os.path.join(R, f'us/data/{u}.json')
    if os.path.exists(p):
        d = J(f'us/data/{u}.json'); USM[u] = {r[0]: r[1] for r in d.get('riv', []) if r[1]}
        if d.get('freq') == 'Q': USQ[u] = d['q']
def mshift(m, k):
    y, mo = int(m[:4]), int(m[5:]) + k
    while mo > 12: mo -= 12; y += 1
    while mo < 1: mo += 12; y -= 1
    return f'{y}-{mo:02d}'
def r_(s, a, b):
    return (s[b] / s[a] - 1) * 100 if a in s and b in s and s[a] > 0 else None
def th_ret(t, src, mem, a, b):
    v = [x for m in mem if m in src for x in [r_(src[m], a, b)] if x is not None]
    return st.median(v) if v and len(v) * 2 >= len(mem) else None
def spearman(x, y):
    n = len(x)
    if n < 6: return None
    def rk(v):
        o = sorted(range(n), key=lambda i: v[i]); r = [0] * n
        for k, i in enumerate(o): r[i] = k
        return r
    a, b = rk(x), rk(y)
    return 1 - 6 * sum((a[i] - b[i]) ** 2 for i in range(n)) / (n * (n * n - 1))
# 營收加速（訊號月月底前已公布的最新兩季）
def racc(u, m):
    q = [x for x in USQ.get(u, []) if x[10] and x[10][:7] <= m]
    if len(q) < 2 or mshift(q[-1][10][:7], 4) < m: return None
    by = {x[0]: x for x in q}
    def yoy(x):
        p = by.get(f'{int(x[0][:2]) - 1:02d}{x[0][2:]}')
        return (x[2] / p[2] - 1) * 100 if p and p[2] and p[2] > 0 and x[2] is not None else None
    a, b = yoy(q[-1]), yoy(q[-2])
    return a - b if a is not None and b is not None else None
MONTHS = sorted({m for s in TWM.values() for m in s})
LAST = MONTHS[-2]   # 最後一個月可能還沒結束
MONTHS = [m for m in MONTHS if '2020-02' <= m <= LAST]
def build(h, skip):
    rows = []
    for m in MONTHS:
        f0, f1 = mshift(m, skip), mshift(m, skip + h)
        if f1 > LAST: continue
        r = []
        for t in TH:
            tw = [x[0] for x in t['stocks']]
            a = dict(th=t['id'], usm=th_ret(t, USM, t['us'], mshift(m, -1), m), twm=th_ret(t, TWM, tw, mshift(m, -1), m), fw=th_ret(t, TWM, tw, f0, f1))
            v = [racc(u, m) for u in t['us']]; v = [x for x in v if x is not None]
            a['racc'] = st.median(v) if v and len(v) * 2 >= len(t['us']) else None
            if None not in (a['usm'], a['twm'], a['fw']): r.append(a)
        if len(r) >= 10:
            mu = st.mean(x['fw'] for x in r)
            for x in r: x['ex'] = x['fw'] - mu; x['gap'] = x['usm'] - x['twm']; x['m'] = m
            rows.append(r)
    return rows
def ev(rows, k, perm=True):
    ics, spr, yrs = [], [], {}
    for r in rows:
        rr = [x for x in r if x.get(k) is not None]
        if len(rr) < 8: continue
        ic = spearman([x[k] for x in rr], [x['ex'] for x in rr]); ics.append(ic); yrs.setdefault(rr[0]['m'][:4], []).append(ic)
        s = sorted(rr, key=lambda x: x[k]); n = len(s) // 3
        spr.append(st.mean(x['ex'] for x in s[-n:]) - st.mean(x['ex'] for x in s[:n]))
    if len(ics) < 3: return None
    m = st.mean(ics); sd = st.stdev(ics)
    o = dict(n=len(ics), ic=round(m, 3), t=round(m / sd * math.sqrt(len(ics)), 2), hit=round(sum(i > 0 for i in ics) / len(ics), 2),
             spr=round(st.mean(spr), 2), years={y: round(st.mean(v), 3) for y, v in sorted(yrs.items())})
    if perm:
        random.seed(7); c = 0; N = 1000
        for _ in range(N):
            s2 = []
            for r in rows:
                rr = [x for x in r if x.get(k) is not None]
                if len(rr) < 8: continue
                e = [x['ex'] for x in rr]; random.shuffle(e); s2.append(spearman([x[k] for x in rr], e))
            if abs(st.mean(s2)) >= abs(m): c += 1
        o['perm_p'] = c / N
    return o
out = {'months': [MONTHS[0], LAST], 'n_themes': len(TH), 'tw_src': J('tools/bt_data/tw_month.json').get('src')}
for skip in (0, 1):
    for h in (1, 3):
        rows = build(h, skip)
        out[f'skip{skip}_h{h}'] = {k: ev(rows, k) for k in ('usm', 'twm', 'gap', 'racc')}
        out[f'skip{skip}_h{h}']['themes_per_month'] = round(st.mean(len(r) for r in rows), 1)
        if skip == 0 and h == 1:
            ics = [spearman([x['usm'] for x in r], [x['twm'] for x in r]) for r in rows]; out['same_month_ic'] = round(st.mean(ics), 3)
# 財報季（2/5/8/11 月底）營收加速分組 → 台股之後 3 個月
g = {'加速': [], '減速': []}
for r in build(3, 0):
    if r[0]['m'][5:] not in ('02', '05', '08', '11'): continue
    for x in r:
        if x['racc'] is not None: g['加速' if x['racc'] > 0 else '減速'].append(x['ex'])
out['season_racc_3m'] = {k: dict(n=len(v), mean=round(st.mean(v), 2), median=round(st.median(v), 2), win=round(sum(e > 0 for e in v) / len(v), 2)) for k, v in g.items() if v}
json.dump(out, open(os.path.join(R, 'tools/backtest_long_result.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
