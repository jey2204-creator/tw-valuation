#!/usr/bin/env python3
"""2026-11-24 掃描頁：新上市（K 棒 2～5 根）也畫小卡，右上標「新」。
起因：11/24 12:41 世杰問 ETF 名單「1 檔無日K（野村韓國科技30 009833）」——11/19 才上市，只有 3 根日 K＋今天盤中 1 根，build() 不到 6 根就不畫。
做法：build() 門檻 6 → 2 根（含今天即時棒）；不到 6 根的標 nw，小卡右上「新」（title 寫上市幾個交易日）；量比、20高突破對新上市不算（資料太少）；K 棒照一般寬度靠右畫。
用法：python3 patch_nw.py → beta_scan_nw.html；python3 patch_nw.py prod → scan.html。只能對 v1124f 跑一次。
"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
s = open('scan.html', encoding='utf-8').read()
E = [
 ("  if(bars.length<6)return null;\n",
  "  if(bars.length<2)return null;const nw=bars.length<6;   // 2026-11-24：新上市 2～5 根也畫，標「新」（以前 <6 根直接列進「無日K」）\n"),
 ("vr:v5?last.v/v5:null,vol:last.v||null,amt:last.v&&", "vr:v5&&!nw?last.v/v5:null,nw,vol:last.v||null,amt:last.v&&"),
 ("${liveTag(r)}${nbadge(r.c)}</div>",
  "${r.nw?`<span class=\"lv nw\" title=\"新上市：只有 ${r.bars.length} 個交易日的 K 線，均線、量比還算不出來\">新</span>`:''}${liveTag(r)}${nbadge(r.c)}</div>"),
 (".lv.dl{background:var(--chip);color:var(--muted)}",
  ".lv.dl{background:var(--chip);color:var(--muted)}\n.lv.nw{background:#2563eb}"),
 ("名單有股票讀不到日K (新掛牌、ETF、已下市) 時統計列會標「N 檔無日K」",
  "新上市只有 2～5 根 K 棒的也照畫，右上標<b>新</b> (均線、量比還算不出來)；名單有股票讀不到日K (掛牌第 1 天、已下市) 時統計列會標「N 檔無日K」"),
 ("const cw=(W-padL-padR)/m,bw=Math.max(1.2,cw*0.62);",
  "const nwS=r.nw?Math.max(0,NN-m):0,cw=(W-padL-padR)/(m+nwS),bw=Math.max(1.2,cw*0.62);   // 2026-11-24：新上市 K 棒少，照一般寬度靠右畫（不撐滿整格）"),
 ("const X=j=>padL+cw*j+cw/2,", "const X=j=>padL+cw*(j+nwS)+cw/2,"),
 ("v1124f", "v1124g"),
]
for a, b in E:
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)
# build() 裡的 20高（scan.html 另有一個海外用的 build 也有同一段，只改 build(c) 那個）
i = s.find('function build(c)'); j = s.find('hi20,brk:last.h>=hi20,', i); k = s.find('\nfunction', i)
assert 0 < i < j < k
s = s[:j] + 'hi20,brk:!nw&&last.h>=hi20,' + s[j + len('hi20,brk:last.h>=hi20,'):]
if not prod:
    s = s.replace('<title>', '<title>[beta] ', 1)
open('scan.html' if prod else 'beta_scan_nw.html', 'w', encoding='utf-8').write(s)
print('ok')
