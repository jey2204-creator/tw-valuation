#!/usr/bin/env python3
"""2026-11-20 掃描頁：「多｜空」切換（方案 B①）。接續 patch_rev.py（排序再點一次反向）。
起因：11/20 19:32 世杰問方案 B 怎麼做，20:53 選「照 ① 出 beta」。
做法（K 線模式才有；估值模式照舊顯示「篩」）：第 3 行最左的「篩」換成「多空」切換鈕（寬 30px，只比「篩」多 4px，免得排行名單的篩選鈕被切；鈕太小所以點一下就切到另一邊；不記在手機）。切到「空」：
  1. 篩選翻面：月線→破月（收盤 < 20 日線）、季線→破季、投連≥3→投賣≥3（投信連賣 ≥3 天）；量≥1.2 不變；選中＝綠底。
  2. 排序預設反向：日週月／投連／外連／月線／20低 預設「空方在前」（綠底＋▼），再點一次翻回；量比 值 量、榜序 不跟著翻。
  3. 20高→20低：前 20 日最低；小卡與放大卡的紅虛線（前 20 日高）換成綠虛線（前 20 日低）。
  4. 小卡外框：綠框＝今天下跌且觸及前 20 日低（多方的紅框不顯示）。
  5. 統計列：N 檔跌破月線・N 檔跌破季線・投信連賣≥3 N 檔。
用法：python3 patch_ls.py → beta_scan_ls.html；python3 patch_ls.py prod → scan.html。只能對 v1120e 跑一次。
"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
s = open('scan.html', encoding='utf-8').read()
E = [
 # ---- 狀態：SIDE＝l 多／s 空；isRev＝(手動反向) XOR (空方且這顆排序會跟著翻) ----
 ("isRev=()=>!!REVS&&REVS===sSig()&&!VSK.has(sortK);",
  "SHK=new Set(['chg','ts','fs','d20','h20']),sideS=()=>SIDE==='s'&&MODE==='k',isRev=()=>!VSK.has(sortK)&&((!!REVS&&REVS===sSig())!==(sideS()&&SHK.has(sortK))),brkL=r=>r.lo20>0&&r.bars[r.bars.length-1].l<=r.lo20;let SIDE='l';"),
 # ---- HTML：篩 → 多 空 ----
 ('<div class="r"><span class="lab">篩</span><button class="f" data-f="ma20"',
  '<div class="r"><span class="lab" id="flab">篩</span><button id="sideB" title="多＝找強勢股 (站上均線、投信連買、漲幅大的在前)；空＝找弱勢股 (跌破均線、投信連賣、跌幅大的在前)。不記在手機，重新整理回到「多」"><i data-s="l">多</i><i data-s="s">空</i></button><button class="f" data-f="ma20"'),
 # ---- CSS ----
 ("/* 2026-11-20：反向排序＝綠底＋▼ */\n",
  "/* 2026-11-20：多｜空 切換 */\n"
  ".sb #sideB{flex:none;display:flex;padding:0 2px;width:30px}.sb #sideB i{flex:1 1 0;font-style:normal;font-weight:400;opacity:.45;text-align:center;height:100%}\n"
  ".sb #sideB i.on{font-weight:800;opacity:1;text-decoration:underline;text-underline-offset:2px}\n"
  ".sb.sh #sideB{background:var(--down);border-color:var(--down);color:#fff}.sb.sh #sideB i{opacity:.7}.sb.sh #sideB i.on{opacity:1}\n"
  ".sb.sh button.f[data-f][aria-pressed=true]{background:var(--down);border-color:var(--down);color:#fff}\n"
  ".km.cold{border-color:var(--down);box-shadow:0 0 0 1px var(--down) inset}\n"
  "/* ▼ 不佔寬度（往右懸出），避免「日▼」「20低▼」在窄螢幕被切 */\n"
  ".sb button.rev:not([data-k=chg]):not([data-k=vr])::after,.sb button.rev i.on::after{font-size:.55em;margin-left:0;margin-right:-.55em}.sb button.rev:not([data-k=chg]):not([data-k=vr]){letter-spacing:-.5px;padding-right:.5em}\n"
  "/* 2026-11-20：反向排序＝綠底＋▼ */\n"),
 # ---- 點擊 ----
 ("    if(b.dataset.vf){VF[b.dataset.vf]=!VF[b.dataset.vf];paintBar();render();return}\n",
  "    if(b.dataset.vf){VF[b.dataset.vf]=!VF[b.dataset.vf];paintBar();render();return}\n"
  "    if(b.id==='sideB'){SIDE=SIDE==='s'?'l':'s';REVS='';paintBar();render();return}\n"),
 # ---- 按鈕外觀 ----
 ("function paintBar(){const V=MODE==='v';rkPaint();",
  "function paintBar(){const V=MODE==='v';rkPaint();{const S=sideS(),sb=$('sideB');$('sortBar').classList.toggle('sh',S);sb.hidden=V;$('flab').hidden=!V;sb.querySelectorAll('i').forEach(i=>i.classList.toggle('on',i.dataset.s===SIDE));"
  "[['ma20','月線','破月','收盤站上 20 日線','收盤跌破 20 日線'],['ma60','季線','破季','收盤站上 60 日線','收盤跌破 60 日線'],['ts3','投連≥3','投賣≥3','投信連買 ≥3 天','投信連賣 ≥3 天']].forEach(([k,a,b2,ta,tb])=>{const el=document.querySelector(`#sortBar .f[data-f=${k}]`);el.textContent=S?b2:a;el.title=S?tb:ta});"
  "const hb=document.querySelector('#sortBar button[data-k=h20]');hb.textContent=S?'20低':'20高';hb.title=S?'近20日低 (跌破或最接近前 20 日最低的在前)':'近20日高'}"),
 # ---- 資料：前 20 日低 ----
 ("hi20,brk:last.h>=hi20,", "hi20,brk:last.h>=hi20,lo20:(a=>a.length?Math.min(...a):null)(bars.slice(-21,-1).map(x=>x.l).filter(x=>x>0)),"),
 # ---- 篩選 ----
 ("function rowsK(){let R=ROWS.filter(r=>(!FL.ma20||(r.d20!=null&&r.d20>=0))&&(!FL.ma60||(r.d60!=null&&r.d60>=0))&&(!FL.ts3||r.ts>=3)&&",
  "function rowsK(){const S=sideS();let R=ROWS.filter(r=>(!FL.ma20||(r.d20!=null&&(S?r.d20<0:r.d20>=0)))&&(!FL.ma60||(r.d60!=null&&(S?r.d60<0:r.d60>=0)))&&(!FL.ts3||(S?r.ts<=-3:r.ts>=3))&&"),
 # ---- 排序：空方的 20低（用負值，配合反向＝跌破／最接近前 20 日低的在前）----
 ("h20:r=>(r.brk?10:0)+(r.hi20?r.px/r.hi20:0)}[sortK];\n  if(isRev()){const nul={",
  "h20:S?r=>-((brkL(r)?10:0)+(r.lo20&&r.px?r.lo20/r.px:0)):r=>(r.brk?10:0)+(r.hi20?r.px/r.hi20:0)}[sortK];\n  if(isRev()){const nul={"),
 ("d20:r=>r.d20==null,h20:r=>!r.hi20}[sortK]", "d20:r=>r.d20==null,h20:r=>S?!r.lo20:!r.hi20}[sortK]"),
 # ---- 統計列 ----
 ("・<b>${ROWS.filter(r=>r.d20!=null&&r.d20>=0).length}</b> 檔站上月線・<b>${ROWS.filter(r=>r.d60!=null&&r.d60>=0).length}</b> 檔站上季線・投信連買≥3 <b>${ROWS.filter(r=>r.ts>=3).length}</b> 檔・",
  "・${sideS()?`<b>${ROWS.filter(r=>r.d20!=null&&r.d20<0).length}</b> 檔跌破月線・<b>${ROWS.filter(r=>r.d60!=null&&r.d60<0).length}</b> 檔跌破季線・投信連賣≥3 <b>${ROWS.filter(r=>r.ts<=-3).length}</b> 檔`:`<b>${ROWS.filter(r=>r.d20!=null&&r.d20>=0).length}</b> 檔站上月線・<b>${ROWS.filter(r=>r.d60!=null&&r.d60>=0).length}</b> 檔站上季線・投信連買≥3 <b>${ROWS.filter(r=>r.ts>=3).length}</b> 檔`}・"),
 # ---- 小卡外框 ----
 ("  $('grid').innerHTML=R.map((r,i)=>`<article class=\"km${r.brk&&r.chg>0?' hot':''}\"",
  "  $('grid').innerHTML=R.map((r,i)=>`<article class=\"km${sideS()?(brkL(r)&&r.chg<0?' cold':''):(r.brk&&r.chg>0?' hot':'')}\""),
 # ---- K 線：紅虛線（前 20 日高）↔ 綠虛線（前 20 日低）----
 ("  const mini=!!opt.mini,all=r.bars,", "  const SHL=sideS()&&!r.ov&&r.lo20>0,LV=SHL?r.lo20:r.hi20,LC=SHL?dn:up;\n  const mini=!!opt.mini,all=r.bars,"),
 ("  if(r.hi20){hi=Math.max(hi,r.hi20);lo=Math.min(lo,r.hi20)}", "  if(LV){hi=Math.max(hi,LV);lo=Math.min(lo,LV)}"),
 ("  if(r.hi20){const y=Y(r.hi20);g.save();g.strokeStyle=up;", "  if(LV){const y=Y(LV);g.save();g.strokeStyle=LC;"),
 ("let y=Y(last.c);if(r.hi20){const yh=Y(r.hi20);g.fillStyle=up;g.fillRect(W-padR+1,yh-7,padR-2,14);g.fillStyle='#fff';g.textAlign='left';g.fillText(pxFmt(r.hi20),W-padR+4,yh);if(Math.abs(y-yh)<15)y=last.c>=r.hi20?yh-15:yh+15}",
  "let y=Y(last.c);if(LV){const yh=Y(LV);g.fillStyle=LC;g.fillRect(W-padR+1,yh-7,padR-2,14);g.fillStyle='#fff';g.textAlign='left';g.fillText(pxFmt(LV),W-padR+4,yh);if(Math.abs(y-yh)<15)y=last.c>=LV?yh-15:yh+15}"),
 ('<span><i style="height:0;border-top:1px dashed var(--up)"></i>前20日高</span>',
  '<span><i style="height:0;border-top:1px dashed var(--${sideS()&&!r.ov&&r.lo20>0?\'down\':\'up\'})"></i>前20日${sideS()&&!r.ov&&r.lo20>0?\'低\':\'高\'}</span>'),
 # ---- 頁尾說明 ----
 ("紅框＝今天上漲且觸及前 20 日高；",
  "紅框＝今天上漲且觸及前 20 日高；<b>多 空</b>＝切到「空」時篩選翻面 (破月/破季/投賣≥3)、日週月/投連/外連/月線/20低 預設把弱的排前面 (綠底▼，再點一次翻回)、紅虛線換成綠虛線＝前 20 日最低、綠框＝今天下跌且觸及前 20 日低，重新整理回到「多」；已選中的排序鈕再點一次＝反向；"),
 ("v1120e", "v1120f"),
]
for a, b in E:
    assert s.count(a) == (2 if a.startswith("hi20,brk:") else 1), (s.count(a), a[:70])
    s = s.replace(a, b)
if not prod:
    s = s.replace('<title>', '<title>[beta] ', 1)
open('scan.html' if prod else 'beta_scan_ls.html', 'w', encoding='utf-8').write(s)
print('ok')
