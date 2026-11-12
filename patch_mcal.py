"""2026-11-12：月／季漲幅改日曆日（跟 XQ 一致）——beta 階段
fetch_momentum.py 多輸出 dc[代號]=[月%(日曆), 季%(日曆)]、calBase={m,q}（基準交易日）；d 內原本的 20／60 交易日不動。
beta.html（由 index.html 產生）有 dc 時月／季改讀 dc，頁尾說明改寫。"""
import re
p = open('fetch_momentum.py', encoding='utf-8').read()
a = '''    ids = sorted({c for _, r in pdays[-5:] for c in r["p"]})
    out = {}
'''
b = '''    ids = sorted({c for _, r in pdays[-5:] for c in r["p"]})
    out = {}
    # 2026/11/12：日曆日版月／季（跟 XQ 一致）＝對比「上個月／三個月前同一天」的收盤；那天休市就取之前最近的交易日
    stems = [s for s, _ in pdays]

    def cal_n(months):
        if not stems:
            return None, None
        t = dt.datetime.strptime(stems[-1], "%Y%m%d").date()
        y, mo = t.year, t.month - months
        while mo <= 0:
            y, mo = y - 1, mo + 12
        last = (dt.date(y + (mo == 12), mo % 12 + 1, 1) - dt.timedelta(days=1)).day
        tgt = f"{y:04d}{mo:02d}{min(t.day, last):02d}"
        idx = max((i for i, s in enumerate(stems) if s <= tgt), default=None)
        return (len(stems) - 1 - idx, stems[idx]) if idx is not None else (None, None)
    nM, baseM = cal_n(1)
    nQ, baseQ = cal_n(3)
    outc = {}
'''
assert p.count(a) == 1; p = p.replace(a, b)
a = '''        w, m, q = ret(cl, 5), ret(cl, 20), ret(cl, 60)
'''
b = a + '''        mc, qc = (ret(cl, nM) if nM else None), (ret(cl, nQ) if nQ else None)
        if mc is not None or qc is not None:
            outc[c] = [mc, qc]
'''
assert p.count(a) == 1; p = p.replace(a, b)
a = "    return out, pdays, idays\n"
assert p.count(a) == 1; p = p.replace(a, "    compute.cal = dict(dc=outc, calBase=dict(m=baseM, q=baseQ))\n" + a)
a = "diag.items()}, d=d)\n"
assert p.count(a) == 1; p = p.replace(a, "diag.items()}, d=d, **getattr(compute, 'cal', {}))\n")
open('fetch_momentum.py', 'w', encoding='utf-8').write(p)

s = open('index.html', encoding='utf-8').read()
a = "const mv=(id,k)=>MO&&MO.d[id]?MO.d[id][MF[k]]:null;"
b = "const mv=(id,k)=>{if(!MO)return null;if((k==='m'||k==='q')&&MO.dc){const c=MO.dc[id];return c?c[k==='m'?0:1]:null}return MO.d[id]?MO.d[id][MF[k]]:null};const calMd=k=>{const s=MO&&MO.calBase&&MO.calBase[k];return s?(+s.slice(4,6))+'/'+(+s.slice(6,8)):''};"
assert s.count(a) == 1; s = s.replace(a, b)
a = "週／月／季＝收盤對比 5／20／60 個交易日前（未還原除權息，跨除息日會略低）。"
b = "${MO&&MO.dc?`週＝收盤對比 5 個交易日前；月／季＝對比上個月／三個月前同一天（${calMd('m')}、${calMd('q')}，日曆日，跟 XQ 一致；那天休市取前一交易日）`:'週／月／季＝收盤對比 5／20／60 個交易日前'}（未還原除權息，跨除息日會略低）。"
assert s.count(a) == 1; s = s.replace(a, b)
open('beta.html', 'w', encoding='utf-8').write(s)
