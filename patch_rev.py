#!/usr/bin/env python3
"""2026-11-20 掃描頁：排序鈕「再點一次就反向」（做空用：日跌幅、投信連賣…排前面）。
起因：11/20 15:59 世杰貼成交值前50截圖，說「日」是日漲幅排序、想看日跌幅排序（做空用）；選方案 A。
做法：已選中的排序（含「日 週 月」「量比 值 量」裡已選中的那個字）再點一次 → 反向，鈕變綠底＋「▼」；再點一次回正向。
  換別的排序／換日週月／換模式就自動回正向（REVS 記的是「哪一個排序被反向」，對不上就失效）；不記在手機。
  反向時仍為昨收、沒資料的照樣排最後。估值模式的 貴／便宜／PE貴／PB貴 不反向（本來就成對）。
用法：python3 patch_rev.py → beta_scan_rev.html；python3 patch_rev.py prod → scan.html。只能對 v1120d 跑一次。
"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
s = open('scan.html', encoding='utf-8').read()
E = [
 # 狀態
 ("let MODE='k',RV='auto',SK_K='chg',SK_V='mh';",
  "let MODE='k',RV='auto',SK_K='chg',SK_V='mh',REVS='';const sSig=()=>sortK+':'+(sortK==='chg'?CHGP:sortK==='vr'?VQP:''),isRev=()=>!!REVS&&REVS===sSig()&&!VSK.has(sortK);/* 2026-11-20：反向排序 */"),
 # 點擊：同一個排序再點＝反向
 ("    if(b.dataset.k){{const t=e.target.closest('i[data-p]');",
  "    if(b.dataset.k){const sg0=sSig();{const t=e.target.closest('i[data-p]');"),
 ("sortK=b.dataset.k;try{localStorage.setItem('scanChgP',CHGP)}catch(e){}}else if(b.dataset.f)",
  "sortK=b.dataset.k;try{localStorage.setItem('scanChgP',CHGP)}catch(e){}{const sg=sSig();REVS=sg===sg0&&!VSK.has(sortK)&&REVS!==sg?sg:''}}else if(b.dataset.f)"),
 # 排序（K 線模式）
 ("  return R.sort((a,b)=>key(b)-key(a)||(b.chg??0)-(a.chg??0))}\n// 注意／處置標記",
  "  if(isRev()){const nul={chg:r=>(r.stale&&ck==='chg')||r[ck]==null,vr:r=>r.stale||(VQP==='a'?r.amt:VQP==='q'?r.vol:r.vr)==null,d20:r=>r.d20==null,h20:r=>!r.hi20}[sortK]||(()=>false);\n"
  "    return R.sort((a,b)=>nul(a)-nul(b)||key(a)-key(b)||(a.chg??0)-(b.chg??0))}   // 反向：小→大；昨收／沒資料的仍排最後\n"
  "  return R.sort((a,b)=>key(b)-key(a)||(b.chg??0)-(a.chg??0))}\n// 注意／處置標記"),
 # 排序（估值模式：只有 榜序、日週月 會反向）
 ("  return R.sort((a,b)=>key(b)-key(a)||(b.chg??0)-(a.chg??0))}\n// 2026-11-15：排行名單統計列第一行",
  "  if(isRev())return R.sort((a,b)=>(sortK==='chg'?(a[ck]==null)-(b[ck]==null):0)||key(a)-key(b)||(a.chg??0)-(b.chg??0));\n"
  "  return R.sort((a,b)=>key(b)-key(a)||(b.chg??0)-(a.chg??0))}\n// 2026-11-15：排行名單統計列第一行"),
 # 按鈕外觀
 ("if(b.dataset.k)b.setAttribute('aria-pressed',String(b.dataset.k===sortK));else if(b.dataset.f)",
  "if(b.dataset.k){b.setAttribute('aria-pressed',String(b.dataset.k===sortK));b.classList.toggle('rev',b.dataset.k===sortK&&isRev())}else if(b.dataset.f)"),
 (".sb button[data-k=chg] i.on{font-weight:800;opacity:1;text-decoration:underline;text-underline-offset:2px}\n",
  ".sb button[data-k=chg] i.on{font-weight:800;opacity:1;text-decoration:underline;text-underline-offset:2px}\n"
  "/* 2026-11-20：反向排序＝綠底＋▼ */\n"
  ".sb button.rev[aria-pressed=true]{background:var(--down);border-color:var(--down);color:#fff}\n"
  ".sb button.rev:not([data-k=chg]):not([data-k=vr])::after,.sb button.rev i.on::after{content:'▼';font-size:.62em;margin-left:1px;vertical-align:.12em;text-decoration:none;display:inline-block}\n"
  ".sb button.rev i{opacity:.7}.sb button.rev i.on{opacity:1}\n"),
 # 換名單時排序被自動換掉（榜序↔日漲）→ 反向一併取消，回來不會突然變反向
 ("RANKED=isRk;paintBar();", "RANKED=isRk;if(REVS&&REVS!==sSig())REVS='';paintBar();"),
 ("v1120d", "v1120e"),
]
for a, b in E:
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)
if not prod:
    s = s.replace('<title>', '<title>[beta] ', 1)
open('scan.html' if prod else 'beta_scan_rev.html', 'w', encoding='utf-8').write(s)
print('ok')
