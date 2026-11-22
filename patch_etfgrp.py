#!/usr/bin/env python3
"""2026-11-22 16:40 📦 ETF 主題頁分組標題列（世杰說「② 主題頁加分組標題列，做給我看」）。
選「全」且是名單順序（沒點欄位排序）時，每類前面插一列：「💰 高息 7檔  日 −6.3%・週 …・月 −20.6%」（該類中位數）；
點標題列＝切到那一類（同上方膠囊）。點欄位排序或只看一類時不顯示（排序後同類不會排在一起）。
用法：python3 patch_etfgrp.py       → beta.html
      python3 patch_etfgrp.py prod  → index.html
只能對 index v1122d 跑一次。
"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'

CSS = ("<style>/* 2026-11-22 ETF 分組標題列 */.lst tr.egh td{background:var(--line);padding:5px 8px;font:700 13px/1.3 var(--f-body);color:var(--fg);cursor:pointer;white-space:nowrap}"
       ".lst tr.egh td small{font-weight:400;font-size:11.5px;color:var(--muted);margin-left:4px}"
       ".lst tr.egh td .em{font:500 12px var(--f-num);margin-left:6px}</style>\n</head>")

E = [
    ("</head>", CSS),
    ("</thead><tbody>`+rows.map(([c,role])=>{",
     "</thead><tbody>`+rows.map(([c,role],ri)=>{const gk=etfCat(c),grp=ETC==='a'&&!k&&gk&&(ri===0||etfCat(rows[ri-1][0])!==gk)?(()=>{"
     "const gi=rows.filter(x=>etfCat(x[0])===gk).map(x=>x[0]),gm=j=>median(gi.map(i=>etfPx(i,j))),EM={'市值':'🏛️','高息':'💰','科技':'💻','債券':'🏦','國外':'🌏'};"
     "const sp=(v,lb,dg=1)=>`<span class=\"em ${sign(v)}\">${lb}${pct(v,dg)}</span>`;"
     "return `<tr class=\"egh\" data-eg=\"${gk}\"><td colspan=\"5\">${EM[gk]||'📦'} ${gk}<small>${gi.length}檔中位</small>${sp(gm(1),'日',2)}${sp(gm(2),'週')}${sp(gm(3),'月')}</td></tr>`})():'';"
     "return grp+(()=>{"),
    ("量比${fmt(vr,2)}</span></td></tr>`}).join('')+'</tbody>';",
     "量比${fmt(vr,2)}</span></td></tr>`})()}).join('')+'</tbody>';"),
    ("    if(e.target.closest('tr[data-id]'))location.href='scan.html#etf'};",
     "    {const g=e.target.closest('tr.egh');if(g){ETC=g.dataset.eg;etfPage();return}}\n"
     "    if(e.target.closest('tr[data-id]'))location.href='scan.html#etf'};"),
    ("上方「全 市值 高息…」可只看一類 (中位數也只算那類，離開 ETF 主題回到「全」)；",
     "上方「全 市值 高息…」可只看一類 (中位數也只算那類，離開 ETF 主題回到「全」)；選「全」且是名單順序時，每類前面有灰底標題列＝那類的日/週/月中位數，點標題列＝只看那類 (點欄位排序後不顯示)；"),
    ('<span style="opacity:.5">v1122d</span>', '<span style="opacity:.5">v1122e</span>'),
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
