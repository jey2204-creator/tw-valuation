"""2026-11-13：當天沒成交（暫停交易／零成交）的股票，週／月／6 日漲幅的基準日改跟「市場最新交易日」走，跟 XQ 一致
例：浩鼎 11/13 沒成交 → 原本從它自己最後一根（11/12）往回數 5 根＝+38.2%；XQ 從 11/13 往回數 5 個交易日（11/6）＝+33.68%
  掃描頁：週＝市場倒數第 6 個交易日（含今日即時棒）當天或之前最近一根；月＝市場最新日的上個月同一天
  注意頁：週／6 日／月同上
後端 fetch_momentum.py／notice_mo.py 另外改（最新一天沒成交就用最近一筆收盤當現價，不再顯示「—」）
用法：python3 patch_md.py [prod]   （預設 scan.html→beta_scan_md.html、notice.html→beta_notice.html）"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
def rep(s, a, b):
    assert s.count(a) == 1, (s.count(a), a[:70])
    return s.replace(a, b)

# ---------------- scan.html
c = open('scan.html', encoding='utf-8').read()
c = rep(c, "  bars.forEach(b=>b.rc=b.c);const adjF=",
        "  // 2026-11-13：MD＝市場交易日（分片的 days＋今天的即時日），ML＝市場最新日；週／月的基準日照它算，當天沒成交的股票才會跟 XQ 一致\n"
        "  const MD=days.map(String);{let g='';LIVE.forEach(v=>{if(v&&!v.miss&&v.d&&String(v.d)>g)g=String(v.d)});if(g>MD[MD.length-1])MD.push(g)}const ML=MD[MD.length-1];\n"
        "  const barAt=k=>{const t=MD[MD.length-1-k];if(!t)return null;let b=null;for(const x of bars){if(String(x.d)<=t)b=x;else break}return b};\n"
        "  bars.forEach(b=>b.rc=b.c);const adjF=")
c = rep(c, "chg5:n>5&&bars[n-6].rc?last.rc/(bars[n-6].rc*adjF(bars[n-6].d,last.d))-1:null,chg20:calM(bars,adjF),",
        "chg5:(b=>b&&b.rc?last.rc/(b.rc*adjF(b.d,ML))-1:null)(barAt(5)),chg20:calM(bars,adjF,ML),")
c = rep(c, "function calM(bars,adjF){const n=bars.length;if(n<2)return null;const last=bars[n-1],ld=String(last.d),",
        "function calM(bars,adjF,ML){const n=bars.length;if(n<2)return null;const last=bars[n-1],ld=String(ML||last.d),")
c = rep(c, "return last.rc/(bars[bi].rc*adjF(bars[bi].d,last.d))-1;", "return last.rc/(bars[bi].rc*adjF(bars[bi].d,ld))-1;")
open('scan.html' if prod else 'beta_scan_md.html', 'w', encoding='utf-8').write(c)

# ---------------- notice.html
n = open('notice.html', encoding='utf-8').read()
n = rep(n, "  const rt=b=>b&&b.c?last.c/(b.c*adjF(c,b.d,last.d))-1:null;",
        "  const ML=String(days[days.length-1]),at=k=>{const t=days[days.length-1-k];if(!t)return null;let b=null;for(const x of bars){if(x.d<=t)b=x;else break}return b};   /* 2026-11-13：基準日跟市場最新交易日走（當天沒成交的股票才會跟 XQ 一致） */\n"
        "  const rt=b=>b&&b.c?last.c/(b.c*adjF(c,b.d,ML))-1:null;")
n = rep(n, "const c6=rt(bars[n-7]);", "const c6=rt(at(6));")
n = rep(n, "const w=rt(bars[n-6]);", "const w=rt(at(5));")
n = rep(n, "  const ld=last.d,tm=new Date(", "  const ld=ML,tm=new Date(")
n = rep(n, " v1113h`", " v1113i`")
open('notice.html' if prod else 'beta_notice.html', 'w', encoding='utf-8').write(n)
print('ok', 'prod' if prod else 'beta')
