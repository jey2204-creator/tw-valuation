#!/usr/bin/env python3
"""2026-11-22 16:49 📦 ETF 含息報酬（世杰選 🥇，出 beta）。
資料：fetch_adj.py 開始收 ETF 除息 → data/adj.json；fetch_rank.py build_etf 用除息係數還原 → data/etf.json 的 px 已含息、adj=true、div={代號:[[除息日, 配息%]]}。
這支只改主題頁文字：說明列「未還原配息」→「已含息」；週欄下方「息11/18」＝近 20 個交易日內除息；頁尾說明。
（掃描頁 ETF 小卡的週/月漲幅也會自動含息，因為掃描頁本來就用 adj.json 還原，不用改程式。）
用法：python3 patch_etfdiv.py       → beta.html
      python3 patch_etfdiv.py prod  → index.html
只能對 index v1122e 跑一次。
"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'

E = [
    ("漲跌<b>未還原配息</b>：跨除息日會偏低 (高股息季配、月配最明顯)。",
     "${ETFJ.adj?'漲跌<b>已含息</b> (配息加回，等於配息再投入；週欄下方「息11/18」＝近 20 個交易日內有除息)。':'漲跌<b>未還原配息</b>：跨除息日會偏低 (高股息季配、月配最明顯)。'}"),
    ("<td class=\"${sign(w)}\">${pct(w)}</td>",
     "<td class=\"${sign(w)}\">${pct(w)}${(()=>{const L=(ETFJ.div&&ETFJ.div[c])||[],x=L[L.length-1];if(!x)return '';"
     "const ok=ETFJ.d20?x[0]>=ETFJ.d20:true;return ok?`<span class=\"sub\" style=\"color:var(--muted)\" title=\"除息 ${+x[0].slice(4,6)}/${+x[0].slice(6)}，配息約占前一日收盤 ${x[1]}%\">息${+x[0].slice(4,6)}/${+x[0].slice(6)}</span>`:''})()}</td>"),
    ("對比 5/20/60 個交易日前收盤，<b>未還原配息</b>；",
     "對比 5/20/60 個交易日前收盤，${ETFJ&&ETFJ.adj?'<b>已含息</b> (除息日之前的價位 × 還原係數＝參考價 ÷ 前一日收盤，跟個股、XQ 的還原方式一樣；配息資料：證交所/櫃買除權息計算結果表)；週欄下方「息11/18」＝近 20 個交易日內的除息日 (點住可看配息占比)':'<b>未還原配息</b>'}；"),
    ('<span style="opacity:.5">v1122e</span>', '<span style="opacity:.5">v1122f</span>'),
]

s = open('index.html', encoding='utf-8').read()
for a, b in E:
    assert s.count(a) == 1, (s.count(a), a[:60])
    s = s.replace(a, b)
if not prod:
    s = s.replace('<title>', '<title>[beta] ', 1)
dst = 'index.html' if prod else 'beta.html'
open(dst, 'w', encoding='utf-8').write(s)
print('ok', dst)
