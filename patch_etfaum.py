#!/usr/bin/env python3
"""2026-11-22 14:40 📦 ETF 名單改成「每類規模前 5 大＋保留 00713、00940、00892」（共 23 檔），類別內依規模排序。
名單與規模在 fetch_rank.py 的 ETF_THEME（規模手動填，玩股網 11/20 排行）；data/etf.json 多了 aum、aumAsof。
這支只改主題頁顯示：備註後面加「・規模 2.16兆／3716億」、說明文字改成依規模。
用法：python3 patch_etfaum.py       → beta.html
      python3 patch_etfaum.py prod  → index.html
只能對 index v1122a 跑一次。
"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'

E = [
    ("desc:'常見台股 ETF 固定名單：市值型、高股息、科技/半導體、債券'",
     "desc:'台股 ETF 各類規模前 5 大 (市值型、高股息、科技/半導體、債券)＋00713、00940、00892'"),
    ("<span class=\"cd\">${c}</span>${role?`<div class=\"role\">${esc(role)}</div>`:''}</td>",
     "<span class=\"cd\">${c}</span>${role?`<div class=\"role\" style=\"white-space:nowrap\">${esc(role.replace(/^[^｜]*｜/,''))}${(()=>{const v=ETFJ.aum&&ETFJ.aum[c];return v?`・${v>=1e4?(v/1e4).toFixed(2)+'兆':Math.round(v)+'億'}`:''})()}</div>`:''}</td>"),
    ("名單順序＝類別 (市值→高息→科技→債券)，同類別內依近 20 個交易日平均成交值由大到小；本站沒有 ETF 規模 (受益權單位×淨值) 資料，所以不是依規模。",
     "名單＝各類規模前 5 大＋00713、00940、00892；順序＝類別 (市值→高息→科技→債券)，同類別內依規模由大到小。股名下方＝說明・規模 (例「台灣50・2.16兆」)；規模 (淨值×受益權單位數)，${ETFJ&&ETFJ.aumAsof?+ETFJ.aumAsof.slice(4,6)+'/'+ +ETFJ.aumAsof.slice(6):''} 的數字 (玩股網排行，00892 取證交所)，<b>不會每天自動更新</b>，排名變動時告訴 Claude 調整；規模會跟著股價漲跌，大跌時排名變化不一定是資金流出。"),
    ('<span style="opacity:.5">v1122a</span>', '<span style="opacity:.5">v1122c</span>'),
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
