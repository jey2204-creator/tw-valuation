#!/usr/bin/env python3
"""注意／處置五名單都能看前幾天 ＋ K 棒標處置期間／名單日（2026-10-29）
用法：python3 patch_nhist.py scan.html beta_scan.html
"""
import sys, re
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
n0 = len(s)

def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (s.count(old), old[:80])
    s = s.replace(old, new)

# ---- 全域 ----
rep("NMAP={},HIST=null,HDAYS=[],NDATE='',",
    "NMAP={},PMAP=null,HIST=null,DH=null,HDAYS=[],NDATE='',")

# ---- 載入 dis_hist.json ＋ 日期選單改成五名單通用 ----
rep("""  try{HIST=await fetch('data/notice/hist.json?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null)}catch(e){HIST=null}
  if(HIST){HDAYS=Object.keys(HIST).filter(d=>HIST[d].att&&HIST[d].att.length).sort().reverse().slice(0,30);
    $('ndSel').innerHTML=HDAYS.map(d=>`<option value="${d}">📅 ${+d.slice(4,6)}/${+d.slice(6)} 名單・${HIST[d].att.length} 檔</option>`).join('');
    $('ndSel').addEventListener('change',e=>{NDATE=e.target.value;pick({kind:'t',id:'natt'})})}""",
"""  // 2026-10-29：五名單（注意／快達／處置／快結束／剛結束）都能看前幾天；處置期間來自 data/notice/dis_hist.json {代號|起日:{c,n,m,start,end,r,measure}}
  try{[HIST,DH]=await Promise.all([fetch('data/notice/hist.json?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null),fetch('data/notice/dis_hist.json?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null)])}catch(e){HIST=null}
  if(HIST){HDAYS=Object.keys(HIST).filter(d=>HIST[d].att&&HIST[d].att.length).sort().reverse().slice(0,30);
    $('ndSel').addEventListener('change',e=>{NDATE=e.target.value;pick(cur)})}""")

# ---- pick()：isN 擴成五名單；過去名單由 histList 算 ----
rep("  if(!(sel.kind==='t'&&sel.id==='natt'))NDATE='';",
    "  if(!(sel.kind==='t'&&NSET.has(sel.id)))NDATE='';")
rep("""  const isN=sel.kind==='t'&&sel.id==='natt';$('ndSel').hidden=!(isN&&HDAYS.length);
  if(isN){if(!NDATE||!HIST[NDATE])NDATE=HDAYS[0]||'';$('ndSel').value=NDATE}
  const past=isN&&NDATE&&HDAYS[0]&&NDATE!==HDAYS[0];
  const ids=past?HIST[NDATE].att.filter(c=>/^\\d{4}$/.test(c)):sel.kind==='n'?((NOTICE&&NOTICE[sel.id])||[]).map(x=>x.c):sel.kind==='t'?(THEMES.find(t=>t.id===sel.id)||{stocks:[]}).stocks.map(x=>x[0]):(IND[sel.id]||[]);
  const name=past?`🟡 注意股（${+NDATE.slice(4,6)}/${+NDATE.slice(6)} 名單）`:sel.kind==='n'?(NN[sel.id]||'注意股'):sel.kind==='t'?(THEMES.find(t=>t.id===sel.id)||{}).name:sel.id;document.title=`${name} K線掃描`;""",
"""  const isN=sel.kind==='t'&&NSET.has(sel.id);$('ndSel').hidden=!(isN&&HDAYS.length);
  if(isN){if(!NDATE||!HIST[NDATE])NDATE=HDAYS[0]||'';
    $('ndSel').innerHTML=HDAYS.map(d=>`<option value="${d}">📅 ${md(d)} 名單・${d===HDAYS[0]?((NOTICE&&NOTICE[NKEY[sel.id]])||[]).length:histList(sel.id,d).length} 檔</option>`).join('');$('ndSel').value=NDATE}
  const past=isN&&NDATE&&HDAYS[0]&&NDATE!==HDAYS[0];
  const PL=past?histList(sel.id,NDATE):null;PMAP=past?Object.fromEntries(PL.map(x=>[x.c,x])):null;
  const ids=past?PL.map(x=>x.c):sel.kind==='n'?((NOTICE&&NOTICE[sel.id])||[]).map(x=>x.c):sel.kind==='t'?(THEMES.find(t=>t.id===sel.id)||{stocks:[]}).stocks.map(x=>x[0]):(IND[sel.id]||[]);
  const name=past?`${NLAB[sel.id]}（${md(NDATE)} 名單${sel.id==='npre'?'・估算':''}）`:sel.kind==='n'?(NN[sel.id]||'注意股'):sel.kind==='t'?(THEMES.find(t=>t.id===sel.id)||{}).name:sel.id;document.title=`${name} K線掃描`;""")

# ---- histList 等工具（放在 loadShard 前） ----
rep("async function loadShard(g){",
"""// ---- 2026-10-29：用 hist.json（每日注意名單）＋ dis_hist.json（處置起迄）回推「選定日」的五種名單；交易日用平日近似（與 fetch_notice.py 的 left 一致） ----
const NSET=new Set(['natt','npre','ndis','nend','npost']),NKEY={natt:'att',npre:'pre',ndis:'dis',nend:'dend',npost:'dpost'},NLAB={natt:'🟡 注意股',npre:'🟠 快達處置',ndis:'🔴 處置股',nend:'⏳ 快處置結束',npost:'✅ 處置剛結束'};
function wdCount(a,b){if(!a||!b||a>=b)return 0;let n=0;const x=new Date(+a.slice(0,4),+a.slice(4,6)-1,+a.slice(6));for(let i=0;i<120;i++){x.setDate(x.getDate()+1);const s=x.getFullYear()+String(x.getMonth()+1).padStart(2,'0')+String(x.getDate()).padStart(2,'0');if(s>b)break;if(x.getDay()%6)n++}return n}
function histList(id,D){if(!HIST)return [];
  const DHv=Object.values(DH||{}).filter(v=>v&&v.c&&/^\\d{4}$/.test(v.c));
  const act=DHv.filter(v=>v.start<=D&&D<v.end),actC=new Set(act.map(v=>v.c));
  const dis={};act.forEach(v=>{if(!dis[v.c]||v.end>dis[v.c].end)dis[v.c]=v});((HIST[D]||{}).dis||[]).forEach(c=>{if(/^\\d{4}$/.test(c)&&!dis[c])dis[c]={c,start:'',end:'',r:''}});
  const mk=v=>({c:v.c,k:'r',n:v.end?wdCount(D,v.end):null,r:v.r||'',end:md(v.end),start:v.start});
  if(id==='ndis')return Object.values(dis).map(mk).sort((a,b)=>(a.n??99)-(b.n??99));
  if(id==='nend')return Object.values(dis).map(mk).filter(x=>x.n!=null&&x.n<=3).sort((a,b)=>a.n-b.n);
  if(id==='npost'){const m={};DHv.filter(v=>v.end&&v.end<=D&&wdCount(v.end,D)<=10&&!actC.has(v.c)).forEach(v=>{if(!m[v.c]||v.end>m[v.c].end)m[v.c]=v});
    return Object.values(m).map(v=>({c:v.c,k:'g',n:wdCount(v.end,D),r:v.r||'',end:md(v.end),start:v.start})).sort((a,b)=>a.n-b.n)}
  const days=Object.keys(HIST).filter(d=>d<=D).sort(),att=d=>(HIST[d]||{}).att||[];
  const cnt=(c,w)=>days.slice(-w).filter(d=>att(d).includes(c)).length,streak=c=>{let n=0;for(let i=days.length-1;i>=0&&att(days[i]).includes(c);i--)n++;return n};
  if(id==='natt')return att(D).filter(c=>/^\\d{4}$/.test(c)).map(c=>({c,k:'y',n:streak(c),r:`${md(D)} 列注意（連 ${streak(c)} 天、近10日 ${cnt(c,10)} 次、近30日 ${cnt(c,30)} 次）`})).sort((a,b)=>b.n-a.n);
  if(id==='npre'){const set=new Set();days.slice(-30).forEach(d=>att(d).forEach(c=>set.add(c)));
    return [...set].filter(c=>/^\\d{4}$/.test(c)&&!actC.has(c)).map(c=>({c,k:'o',n:cnt(c,10),n30:cnt(c,30)})).filter(x=>x.n>=5||x.n30>=11).map(x=>({...x,r:`估算：到 ${md(D)} 近10日 ${x.n} 次、近30日 ${x.n30} 次列注意`})).sort((a,b)=>b.n-a.n)}
  return []}
async function loadShard(g){""")

# ---- build()：加處置期間；K 棒底下的點只留「列注意日」（處置改畫底色） ----
rep("  const nd=HIST?Object.fromEntries(Object.entries(HIST).filter(([d,v])=>(v.att||[]).includes(c)||(v.dis||[]).includes(c)).map(([d,v])=>[d,(v.dis||[]).includes(c)?'r':'y'])):{};",
    "  const dp=DH?Object.values(DH).filter(v=>v&&v.c===c&&v.start&&v.end).map(v=>[v.start,v.end]):[];\n  const nd=HIST?Object.fromEntries(Object.entries(HIST).filter(([d,v])=>(v.att||[]).includes(c)).map(([d])=>[d,'y'])):{};")
rep("return {c,n:NAME[c]||c,bars,nd,px:last.c,", "return {c,n:NAME[c]||c,bars,nd,dp,px:last.c,")

# ---- 標籤：過去名單用 PMAP ----
rep("function nbadge(c){const m=NMAP[c];if(!m)return '';return m.k==='r'",
    "function nbadge(c){const m=PMAP?PMAP[c]:NMAP[c];if(!m)return '';return m.k==='g'?`<span class=\"tg\" style=\"background:var(--accent)\" title=\"處置剛結束\">畢${m.n!=null?m.n:''}</span>`:m.k==='r'")
rep("const nm=NMAP[r.c],ntag=nm?`<span class=\"ntag\" style=\"background:${nm.k==='r'?'var(--up)':nm.k==='o'?'#d9731a':'#b88600'}\">${nm.k==='r'?'處置中'+(nm.end?'～'+nm.end:''):nm.k==='o'?'快達處置':'注意 連'+nm.n+'天'}</span>`:'';",
    "const nm=PMAP?PMAP[r.c]:NMAP[r.c],ntag=nm?`<span class=\"ntag\" style=\"background:${nm.k==='g'?'var(--accent)':nm.k==='r'?'var(--up)':nm.k==='o'?'#d9731a':'#b88600'}\">${nm.k==='g'?'處置 '+(nm.end||'')+' 結束・後 '+nm.n+' 日':nm.k==='r'?'處置中'+(nm.end?'～'+nm.end:''):nm.k==='o'?'快達處置':'注意 連'+nm.n+'天'}</span>`:'';")

# 放大卡圖例
rep("${r.nd&&Object.keys(r.nd).length?'<span><i style=\"width:7px;height:7px;border-radius:50%;background:#e0a800\"></i>列注意日</span>':''}</div>",
    "${r.nd&&Object.keys(r.nd).length?'<span><i style=\"width:7px;height:7px;border-radius:50%;background:#e0a800\"></i>列注意日</span>':''}${r.dp&&r.dp.length?'<span><i style=\"width:12px;height:9px;background:var(--up);opacity:.18\"></i>處置期間</span>':''}${NDATE&&PMAP?'<span><i style=\"height:0;border-top:1.5px dashed var(--fg)\"></i>名單日 '+md(NDATE)+'</span>':''}</div>")

# ---- drawK：處置期間底色＋名單日直線（畫在格線之前） ----
rep("  g.strokeStyle=ln;g.lineWidth=1;g.font='10px '+css('--f-num');g.textBaseline='middle';\n  (mini?[0.25,0.5,0.75]",
"""  // 2026-10-29：處置期間淡紅底色（價格＋量＋籌碼整欄），名單日（選了過去日期時）畫一條直虛線
  if(r.dp&&r.dp.length){g.save();g.fillStyle=up;g.globalAlpha=mini?.13:.1;let j0=-1;vis.forEach((x,j)=>{const inb=r.dp.some(([a,b])=>x.d>=a&&x.d<b);if(inb&&j0<0)j0=j;if((!inb||j===m-1)&&j0>=0){const j1=inb?j:j-1;g.fillRect(X(j0)-cw/2,top,cw*(j1-j0+1),Hh-top-axisH);j0=-1}});g.restore()}
  if(NDATE&&PMAP){const j=vis.findIndex(x=>x.d===NDATE);if(j>=0){g.save();g.strokeStyle=fg;g.globalAlpha=.55;g.lineWidth=1;g.setLineDash([3,3]);g.beginPath();g.moveTo(X(j),top);g.lineTo(X(j),Hh-axisH);g.stroke();g.restore()}}
  g.strokeStyle=ln;g.lineWidth=1;g.font='10px '+css('--f-num');g.textBaseline='middle';
  (mini?[0.25,0.5,0.75]""")

# ---- 說明文字 ----
rep("選「注意股」時可用日期選單看前幾天的名單。",
    "K 棒上<span style=\"background:var(--up);opacity:.25\">　　</span>淡紅底＝處置期間（起迄來自官方公告，迄日當天算結束）。選注意／快達／處置／快結束／剛結束任一名單時，最左邊的日期選單可看前幾天的名單（K 棒照舊畫到最新交易日，虛線＝那天）；過去的快達處置名單為估算（近10日≥5次或近30日≥11次）；<b>畢N</b>＝處置結束後第 N 個交易日。")

# hashchange：#n/xxx 統一走自動主題
rep("if(h.startsWith('n/')){if(!cur||cur.kind!=='n'||cur.id!==h.slice(2))pick({kind:'n',id:h.slice(2)})}",
    "if(h.startsWith('n/')){const id='n'+h.slice(2);if(!cur||cur.kind!=='t'||cur.id!==id)pick(THEMES.some(t=>t.id===id)?{kind:'t',id}:{kind:'n',id:h.slice(2)})}")

if dst.startswith('beta'):
    rep('<title>', '<title>[beta] ', 1) if s.count('<title>')==1 else None
open(dst, 'w', encoding='utf-8').write(s)
print('ok', n0, '->', len(s))
