#!/usr/bin/env python3
"""投信／外資／土洋買超前 20 也能看前幾天的名單 ＋ K 棒標上榜日（2026-10-30）
需先套過 patch_nhist.py。用法：python3 patch_tophist.py scan.html beta_scan.html
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()

def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

rep("PMAP=null,HIST=null,DH=null,HDAYS=[],", "PMAP=null,HIST=null,DH=null,HDAYS=[],THIST=null,TDAYS=[],TOPL=null,")
rep("  if(!(sel.kind==='t'&&NSET.has(sel.id)))NDATE='';", "  if(!(sel.kind==='t'&&(NSET.has(sel.id)||(sel.id in TKEY))))NDATE='';")

# 讀 itrust_top.json 的 hist
rep("  if(TOP&&TOP.lists){const md=TOP.asof?",
    "  // 2026-10-30：itrust_top.json 的 hist {YYYYMMDD:{it:[…],fi:[…],both:[…]}}＝每個名單日的前 20 代號（top_extract.py 累積 150 天）\n  if(TOP&&TOP.hist){THIST=TOP.hist;TOPL=TOP.lists||{};TDAYS=Object.keys(THIST).sort().reverse().slice(0,30)}\n  if(TOP&&TOP.lists){const md=TOP.asof?")

# pick()：日期清單依名單種類切換
rep("  const isN=sel.kind==='t'&&NSET.has(sel.id);$('ndSel').hidden=!(isN&&HDAYS.length);\n  if(isN){if(!NDATE||!HIST[NDATE])NDATE=HDAYS[0]||'';",
    "  const isT=sel.kind==='t'&&(sel.id in TKEY)&&!!THIST,DAYS=isT?TDAYS:HDAYS,isN=sel.kind==='t'&&(NSET.has(sel.id)||isT);$('ndSel').hidden=!(isN&&DAYS.length);\n  if(isN){if(!NDATE||!(isT?THIST:HIST)[NDATE])NDATE=DAYS[0]||'';")
rep("$('ndSel').innerHTML=HDAYS.map(d=>`<option value=\"${d}\">📅 ${md(d)} 名單・${d===HDAYS[0]?((NOTICE&&NOTICE[NKEY[sel.id]])||[]).length:histList(sel.id,d).length} 檔</option>`).join('');",
    "$('ndSel').innerHTML=DAYS.map(d=>`<option value=\"${d}\">📅 ${md(d)} 名單・${d===DAYS[0]?(isT?(TOPL[TKEY[sel.id]]||[]):((NOTICE&&NOTICE[NKEY[sel.id]])||[])).length:histList(sel.id,d).length} 檔</option>`).join('');")
rep("  const past=isN&&NDATE&&HDAYS[0]&&NDATE!==HDAYS[0];",
    "  const past=isN&&NDATE&&DAYS[0]&&NDATE!==DAYS[0];TOPK=isT?TKEY[sel.id]:'';")

# histList：加三個榜
rep("const NSET=new Set(['natt','npre','ndis','nend','npost']),",
    "const TKEY={itop:'it',ftop:'fi',btop:'both'},TLAB={it:'📈 投信買超前20',fi:'🌐 外資買超前20',both:'🤝 土洋同買前20'},TCOL={it:'var(--ma20)',fi:'var(--accent)',both:'var(--warm)'};let TOPK='';\nconst NSET=new Set(['natt','npre','ndis','nend','npost']),")
rep("function histList(id,D){if(!HIST)return [];",
    """function histList(id,D){
  if(id in TKEY){if(!THIST||!THIST[D])return [];const k=TKEY[id],tds=Object.keys(THIST).filter(d=>d<=D).sort();
    const stk=c=>{let n=0;for(let i=tds.length-1;i>=0&&(THIST[tds[i]][k]||[]).includes(c);i--)n++;return n};
    return (THIST[D][k]||[]).filter(c=>/^\\d{4}$/.test(c)).map((c,i)=>({c,k,n:stk(c),rank:i+1,r:`${md(D)} ${TLAB[k].slice(2)}第 ${i+1} 名・連續 ${stk(c)} 天上榜`}))}
  if(!HIST)return [];""")
rep("const name=past?`${NLAB[sel.id]}（${md(NDATE)} 名單",
    "const name=past?`${NLAB[sel.id]||TLAB[TKEY[sel.id]]}（${md(NDATE)} 名單")

# build()：上榜日（只看目前這個榜）
rep("  const nd=HIST?Object.fromEntries(Object.entries(HIST).filter(([d,v])=>(v.att||[]).includes(c)).map(([d])=>[d,'y'])):{};",
    "  const nd=HIST?Object.fromEntries(Object.entries(HIST).filter(([d,v])=>(v.att||[]).includes(c)).map(([d])=>[d,'y'])):{};\n  if(TOPK&&THIST)Object.entries(THIST).forEach(([d,v])=>{if((v[TOPK]||[]).includes(c))nd[d]=TOPK});")

# K 棒底下的點：上榜日用該榜顏色
rep("g.fillStyle=k==='r'?up:'#e0a800';g.beginPath();g.arc(X(j),y0,mini?1.6:2.6,0,Math.PI*2);g.fill()})}",
    "g.fillStyle=k==='r'?up:k==='y'?'#e0a800':css(k==='it'?'--ma20':k==='fi'?'--accent':'--warm');g.beginPath();g.arc(X(j),y0,mini?1.6:2.6,0,Math.PI*2);g.fill()})}")

# 標籤：榜N
rep("function nbadge(c){const m=PMAP?PMAP[c]:NMAP[c];if(!m)return '';return m.k==='g'?",
    "function nbadge(c){const m=PMAP?PMAP[c]:NMAP[c];if(!m)return '';return TLAB[m.k]?`<span class=\"tg\" style=\"background:${TCOL[m.k]}\" title=\"${esc(m.r)}\">榜${m.n}</span>`:m.k==='g'?")
rep("ntag=nm?`<span class=\"ntag\" style=\"background:${nm.k==='g'?'var(--accent)':",
    "ntag=nm?`<span class=\"ntag\" style=\"background:${TLAB[nm.k]?TCOL[nm.k]:nm.k==='g'?'var(--accent)':")
rep("\">${nm.k==='g'?'處置 '+(nm.end||'')+' 結束・後 '+nm.n+' 日':",
    "\">${TLAB[nm.k]?'第 '+nm.rank+' 名・連 '+nm.n+' 天上榜':nm.k==='g'?'處置 '+(nm.end||'')+' 結束・後 '+nm.n+' 日':")

# 放大卡圖例
rep("${r.nd&&Object.keys(r.nd).length?'<span><i style=\"width:7px;height:7px;border-radius:50%;background:#e0a800\"></i>列注意日</span>':''}",
    "${r.nd&&Object.values(r.nd).includes('y')?'<span><i style=\"width:7px;height:7px;border-radius:50%;background:#e0a800\"></i>列注意日</span>':''}${TOPK&&r.nd&&Object.values(r.nd).includes(TOPK)?`<span><i style=\"width:7px;height:7px;border-radius:50%;background:${TCOL[TOPK]}\"></i>上榜日</span>`:''}")

# 說明
rep("<b>畢N</b>＝處置結束後第 N 個交易日。",
    "<b>畢N</b>＝處置結束後第 N 個交易日。投信／外資／土洋買超前 20 也可用日期選單看前幾天的名單（9/29 起累積），小卡 <b>榜N</b>＝連續 N 天上榜，K 棒底下的彩色點＝那天在這個榜上。")

if dst.startswith('beta') and s.count('<title>') == 1 and '[beta]' not in s:
    s = s.replace('<title>', '<title>[beta] ')
open(dst, 'w', encoding='utf-8').write(s)
print('ok')
