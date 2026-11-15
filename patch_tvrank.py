#!/usr/bin/env python3
"""掃描頁加「💰 成交值前50／📊 成交量前50」名單（2026-11-15）
世杰選：前 50、ETF 保留、可切 合併／上市／上櫃。資料 data/rank.json（fetch_rank.py，rank.yml 排程）。
需先套過 patch_thli.py（v1115m）。用法：python3 patch_tvrank.py scan.html beta_scan_rk.html
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()


def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:90])
    s = s.replace(old, new)


# ---- CSS：市場切換鈕（跟「日·週·月」同一種樣式，三段可直接點）
rep(".sb button#fAll[aria-pressed=true]{background:var(--up);border-color:var(--up);color:#fff}",
    ".sb button#fAll[aria-pressed=true]{background:var(--up);border-color:var(--up);color:#fff}\n"
    ".sb button#rkM{flex:2.4 1 0;padding:0 2px}\n"
    ".sb button#rkM i{font-style:normal;font-weight:400;opacity:.45;padding:0 1px}\n"
    ".sb button#rkM i.on{font-weight:800;opacity:1;text-decoration:underline;text-underline-offset:2px}")

# ---- 第 3 行最後加市場切換鈕（只在排行名單顯示）
rep('<button class="f vs" data-vf="pb80" hidden title="淨值比分位 ≥80%">PB≥80%</button></div>',
    '<button class="f vs" data-vf="pb80" hidden title="淨值比分位 ≥80%">PB≥80%</button><button id="rkM" hidden title="排行範圍：合併＝上市＋上櫃一起排；也可只看上市或只看上櫃（直接點字切換）"></button></div>')

# ---- 全域
rep("let FH=null,FS=null,FDAYS=[],FALL=false,FPOOL=new Set(),FIRE=false,PAST=false;",
    "let FH=null,FS=null,FDAYS=[],FALL=false,FPOOL=new Set(),FIRE=false,PAST=false;\n"
    "// 2026-11-15：成交值／成交量排行（data/rank.json；RKM＝a 合併／L 上市／O 上櫃）\n"
    "let RK=null,RDAYS=[],RKM='a',RSETS={};const RKEY={vtop:'v',qtop:'q'},RMN={a:'合併',L:'上市',O:'上櫃'};")

rep("const TKEY={itop:'it',ftop:'fi',btop:'both'},TLAB={it:'📈 投信買超前20',fi:'🌐 外資買超前20',both:'🤝 土洋同買前20'},TCOL={it:'var(--ma20)',fi:'var(--accent)',both:'var(--warm)'};let TOPK='';",
    "const TKEY={itop:'it',ftop:'fi',btop:'both'},TLAB={it:'📈 投信買超前20',fi:'🌐 外資買超前20',both:'🤝 土洋同買前20',v:'💰 成交值前50',q:'📊 成交量前50'},TCOL={it:'var(--ma20)',fi:'var(--accent)',both:'var(--warm)',v:'var(--warm)',q:'var(--accent)'};let TOPK='';\n"
    "// ---- 2026-11-15：成交值／成交量排行。rank.json 每天存上市、上櫃各前 50；合併＝兩邊合起來重排取前 50\n"
    "function rkList(k,D){const h=RK&&RK.hist[D];if(!h)return [];const L=(h.L&&h.L[k])||[],O=(h.O&&h.O[k])||[];return (RKM==='L'?L:RKM==='O'?O:[...L,...O].sort((x,y)=>y[1]-x[1])).slice(0,RK.top||50)}\n"
    "function rkSet(k,D){const key=k+RKM+D;return RSETS[key]||(RSETS[key]=new Set(rkList(k,D).map(x=>x[0])))}\n"
    "const rkFmt=(k,x)=>k==='v'?(x>=10?Math.round(x):x.toFixed(1))+'億':x>=1e5?Math.round(x/1e4)+'萬':x>=1e4?(x/1e4).toFixed(1)+'萬':fmt(x);\n"
    "function rkHist(id,D){const k=RKEY[id],ds=RDAYS.filter(d=>d<=D),stk=c=>{let n=0;for(const d of ds){if(rkSet(k,d).has(c))n++;else break}return n};\n"
    "  return rkList(k,D).map(([c,x],i)=>{const n=stk(c);return {c,k,n,rank:i+1,val:rkFmt(k,x),r:`${md(D)} ${RMN[RKM]}${k==='v'?'成交值':'成交量'}第 ${i+1} 名・${k==='v'?fmt(x,x>=100?0:1)+' 億元':fmt(x)+' 張'}・連續 ${n} 天上榜${/^00/.test(c)?'・ETF':''}`}})}\n"
    "// 估值模式第 3 行有 4 顆篩選鈕比較擠 → 市場鈕縮成「合·市·櫃」\n"
    "function rkPaint(){const V=MODE==='v',b=$('rkM');b.style.flex=V?'0.95 1 0':'';b.innerHTML=[['a',V?'合':'合併'],['L',V?'市':'上市'],['O',V?'櫃':'上櫃']].map(([k,n])=>`<i data-rm=\"${k}\" class=\"${k===RKM?'on':''}\">${n}</i>`).join('·')}")
rep("function paintBar(){const V=MODE==='v';", "function paintBar(){const V=MODE==='v';rkPaint();")

# ---- init：平行載入 rank.json
rep("  const FHP=Promise.all(['data/fire_hist.json','data/fire_stats.json'].map(",
    "  const RKP=fetch('data/rank.json?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null);\n"
    "  const FHP=Promise.all(['data/fire_hist.json','data/fire_stats.json'].map(")

# 🔥 區塊之後插入兩個排行主題（放在 ★ 自選、🔥 主力訊號後面）；ETF 的名稱／市場／日K 接進來
rep("  $('themes').innerHTML=THEMES.map(t=>{const dm=t.name.match(",
    "  {const rj=await RKP;if(rj&&rj.hist&&rj.days&&rj.days.length){RK=rj;RDAYS=rj.days.slice();try{const m=localStorage.getItem('scanRkM');if(m==='L'||m==='O')RKM=m}catch(e){}\n"
    "    Object.entries(rj.nm||{}).forEach(([c,[n,m]])=>{if(!NAME[c]){NAME[c]=n;MKT[c]=m}});\n"
    "    // ETF 日K：本站分片沒有 ETF → 用 rank.json 的 xk 組一個假分片（列＝[收,張,…,開,高,低]），build() 照常畫\n"
    "    if(rj.xk&&rj.xk.days){const by={};Object.entries(rj.xk.d||{}).forEach(([c,a])=>{const g=c.slice(0,2);(by[g]=by[g]||{})[c]=a.map(r=>r?[r[0],r[1],null,null,null,null,null,null,r[2],r[3],r[4],null]:null)});\n"
    "      Object.keys(by).forEach(g=>{if(SHARD[g]===undefined)SHARD[g]={days:rj.xk.days,d:by[g]}})}\n"
    "    let at=0;while(at<THEMES.length&&(THEMES[at].id==='_fav'||THEMES[at].id==='fire'))at++;\n"
    "    THEMES.splice(at,0,{id:'vtop',name:`💰 成交值前50（${md(RDAYS[0])}）`,stocks:rkList('v',RDAYS[0]).map(x=>[x[0],''])},{id:'qtop',name:`📊 成交量前50（${md(RDAYS[0])}）`,stocks:rkList('q',RDAYS[0]).map(x=>[x[0],''])})}}\n"
    "  rkPaint();\n"
    "  $('themes').innerHTML=THEMES.map(t=>{const dm=t.name.match(")

# sortBar：市場切換（直接點字；點到空白處就循環）
rep("    if(b.id==='fAll'){FALL=!FALL;",
    "    if(b.id==='rkM'){const t=e.target.closest('i[data-rm]');RKM=t?t.dataset.rm:RKM==='a'?'L':RKM==='L'?'O':'a';try{localStorage.setItem('scanRkM',RKM)}catch(e){}rkPaint();pick(cur);return}\n"
    "    if(b.id==='fAll'){FALL=!FALL;")

# 面板分類：排行放「⭐ 自選・訊號籌碼」
rep("const A=THEMES.filter(t=>t.id==='_fav'||t.id==='fire'||(t.id in TKEY)),",
    "const A=THEMES.filter(t=>t.id==='_fav'||t.id==='fire'||(t.id in TKEY)||(t.id in RKEY)),")

# pick()
rep("  if(!(sel.kind==='t'&&(NSET.has(sel.id)||(sel.id in TKEY)||sel.id==='fire')))NDATE='';",
    "  if(!(sel.kind==='t'&&(NSET.has(sel.id)||(sel.id in TKEY)||(sel.id in RKEY)||sel.id==='fire')))NDATE='';")
rep("sel.kind==='t'&&sel.id!=='_fav'&&sel.id!=='fire'?'index.html#t/'",
    "sel.kind==='t'&&sel.id!=='_fav'&&sel.id!=='fire'&&!(sel.id in RKEY)?'index.html#t/'")
rep("  const isT=sel.kind==='t'&&(sel.id in TKEY)&&!!THIST,DAYS=isF?FDAYS:isT?TDAYS:NDAYS,D0=(isF?FDAYS[0]:!isT&&NXT?NOTICE.asof:DAYS[0])||'',isN=sel.kind==='t'&&(NSET.has(sel.id)||isT||isF);",
    "  const isR=sel.kind==='t'&&(sel.id in RKEY)&&!!RK;$('rkM').hidden=!isR;\n"
    "  const isT=sel.kind==='t'&&(sel.id in TKEY)&&!!THIST,DAYS=isF?FDAYS:isR?RDAYS:isT?TDAYS:NDAYS,D0=(isF?FDAYS[0]:isR?RDAYS[0]:!isT&&NXT?NOTICE.asof:DAYS[0])||'',isN=sel.kind==='t'&&(NSET.has(sel.id)||isT||isF||isR);")
rep("  if(isN){if(!NDATE||!(isF?FH.d:isT?THIST:HIST)[NDATE])NDATE=D0;\n    $('ndSel').innerHTML=isF?",
    "  if(isN){if(!NDATE||!(isF?FH.d:isR?RK.hist:isT?THIST:HIST)[NDATE])NDATE=D0;\n    $('ndSel').innerHTML=isR?DAYS.map(d=>`<option value=\"${d}\">📅 ${md(d)} 排行</option>`).join(''):isF?")
rep("TOPK=isT?TKEY[sel.id]:'';FIRE=isF;PAST=!!past;",
    "TOPK=isT?TKEY[sel.id]:isR?RKEY[sel.id]:'';FIRE=isF;PAST=!!past;")
rep("$('sortLi').title=isTh?'照首頁主題表的成份股順序':'照名單順序（第 1～20 名）';",
    "$('sortLi').title=isTh?'照首頁主題表的成份股順序':isR?'照排行名次（第 1～50 名）':'照名單順序（第 1～20 名）';")
rep("  const PL=past||isF?histList(sel.id,NDATE):null;",
    "  const PL=past||isF||isR?histList(sel.id,NDATE):null;")
rep("NLAB[sel.id]||TLAB[TKEY[sel.id]]}（${md(NDATE)} 名單",
    "NLAB[sel.id]||TLAB[TKEY[sel.id]]||TLAB[RKEY[sel.id]]}（${md(NDATE)} 名單")

# histList
rep("  if(id==='fire')return fireList(D);\n",
    "  if(id==='fire')return fireList(D);\n  if(id in RKEY)return RK?rkHist(id,D):[];\n")

# build()：上榜日（照目前的市場範圍）
rep("  if(TOPK&&THIST)Object.entries(THIST).forEach(([d,v])=>{if((v[TOPK]||[]).includes(c))nd[d]=TOPK});",
    "  if(TOPK&&THIST)Object.entries(THIST).forEach(([d,v])=>{if((v[TOPK]||[]).includes(c))nd[d]=TOPK});\n"
    "  if(RK&&(TOPK==='v'||TOPK==='q'))RDAYS.forEach(d=>{if(rkSet(TOPK,d).has(c))nd[d]=TOPK});")
rep("css(k==='it'?'--ma20':k==='fi'?'--accent':'--warm')", "css(k==='it'?'--ma20':k==='fi'||k==='q'?'--accent':'--warm')")

# 小卡標籤：排行顯示金額／張數（其他榜照舊「榜N」）
rep("title=\"${esc(m.r)}\">榜${m.n}</span>`:m.k==='g'?", "title=\"${esc(m.r)}\">${m.val||'榜'+m.n}</span>`:m.k==='g'?")
rep("TLAB[nm.k]?'第 '+nm.rank+' 名・連 '+nm.n+' 天上榜':", "TLAB[nm.k]?'第 '+nm.rank+' 名'+(nm.val?'・'+nm.val:'')+'・連 '+nm.n+' 天上榜':")

# 統計列（K 線模式）
rep("  $('cnt').innerHTML=all?fz+`<b>${R.length}</b>／${all} 檔${missTxt}",
    "  const rz=PMAP&&(TOPK==='v'||TOPK==='q')?(v=>{const e=v.filter(x=>/^00/.test(x.c)).length,o=v.filter(x=>MKT[x.c]==='上櫃').length,nw=v.filter(x=>x.n===1).length;"
    "return `${TOPK==='v'?'💰 成交值':'📊 成交量'}前 ${v.length}・<b>${RMN[RKM]}</b>（上市 ${v.length-o}・上櫃 ${o}${e?'・其中 ETF '+e:''}）・🆕 今天才上榜 <b>${nw}</b><br>`})(Object.values(PMAP)):'';\n"
    "  $('cnt').innerHTML=all?fz+rz+`<b>${R.length}</b>／${all} 檔${missTxt}")

# 估值模式：ETF 沒有本益比／淨值比，不去問 FinMind
rep("async function valGet(c){if(VAL[c])return VAL[c];",
    "async function valGet(c){if(VAL[c])return VAL[c];if(/^00/.test(c))throw new Error('ETF 沒有本益比');")

# 說明
rep("小卡 <b>榜N</b>＝連續 N 天上榜，K 棒底下的彩色點＝那天在這個榜上。",
    "小卡 <b>榜N</b>＝連續 N 天上榜，K 棒底下的彩色點＝那天在這個榜上。"
    "<b>💰 成交值前50／📊 成交量前50</b>＝全市場當天成交金額／成交張數最大的 50 檔（含 ETF，不含權證、特別股），第 3 行可切 <b>合併·上市·上櫃</b>；小卡標籤是當天的成交值（億元）或成交量（張），日期選單可看前幾天的排行；ETF 沒有法人籌碼與估值。")
rep("v1115m", "v1115n")

if dst.startswith('beta') and s.count('<title>') == 1 and '[beta]' not in s:
    s = s.replace('<title>', '<title>[beta] ')
open(dst, 'w', encoding='utf-8').write(s)
print('ok')
