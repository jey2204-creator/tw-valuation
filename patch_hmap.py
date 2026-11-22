#!/usr/bin/env python3
"""2026-11-22 17:41 🗺️ 主題熱力圖（世杰選「只做 ① 等大方格，做給我看」）。
新頁 #h：
  每個產業主題一格（等大，4 欄），顏色＝成份股漲跌中位數，固定七階色（紅漲綠跌）：
    日 ±0.5/1.5/3%、週 ±1.5/4/8%、月 ±3/8/15%、季 ±5/12/25%
  格內：主題名、中位數%、上漲家數/有資料家數。
  切換：「日 週 月 季」、「順序 漲幅」（順序＝首頁主題表順序，含手動排序/隱藏）；記在手機。
  不含自動名單（ETF、0050、注意股、投信買超…、⭐自選）；自訂主題會出現。
  點格子 → 下方展開該主題成份股小熱力圖（依市值排序，點個股 → 個股頁），附「📈 掃 K 線」「📋 主題頁」。
資料：日＝summary.json chg（收盤日 pxAsof）；週/月/季＝momentum.json（還原價、月/季日曆日，跟首頁一樣）。
入口：首頁入口清單「📈 K 線掃描」下方一列＋產業主題標題列「🗺️」。
用法：python3 patch_hmap.py       → beta.html
      python3 patch_hmap.py prod  → index.html
只能對 index v1122h 跑一次。
"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'

CSS = r"""<style>/* 2026-11-22 主題熱力圖 */
.hmc{display:flex;gap:8px;align-items:center;justify-content:space-between;margin:8px 0 6px}
.hmseg{display:flex;border:1px solid var(--line);border-radius:14px;overflow:hidden}
.hmseg button{border:0;background:none;color:var(--muted);font:500 13px/28px var(--f-body);padding:0 11px;-webkit-tap-highlight-color:transparent}
.hmseg button[aria-pressed="true"]{background:var(--accent);color:#fff;font-weight:700}
.hm{display:grid;grid-template-columns:repeat(4,1fr);gap:3px}
.hm.m3{grid-template-columns:repeat(3,1fr)}
.hmt{border:0;border-radius:7px;padding:6px 3px 5px;min-height:60px;text-align:center;color:var(--fg);font-family:var(--f-body);display:flex;flex-direction:column;justify-content:center;gap:1px;overflow:hidden;-webkit-tap-highlight-color:transparent;text-decoration:none}
.hmt .n{font-size:12px;font-weight:600;white-space:nowrap;line-height:1.25}
.hmt .n.s1{font-size:11px}.hmt .n.s2{font-size:10px;letter-spacing:-.3px}
.hmt .p{font:700 15px/1.2 var(--f-num)}
.hmt .c{font-size:10px;opacity:.75;line-height:1.2}
.hmt.l3,.hmt.l-3{color:#fff}.hmt.l3 .c,.hmt.l-3 .c{opacity:.9}
.hmt.l0{background:var(--grid)}
.hmt.l1{background:color-mix(in srgb,var(--up) 18%,var(--card))}.hmt.l2{background:color-mix(in srgb,var(--up) 45%,var(--card))}.hmt.l3{background:color-mix(in srgb,var(--up) 85%,#000)}
.hmt.l-1{background:color-mix(in srgb,var(--down) 18%,var(--card))}.hmt.l-2{background:color-mix(in srgb,var(--down) 45%,var(--card))}.hmt.l-3{background:color-mix(in srgb,var(--down) 85%,#000)}
.hmt.na{background:var(--card);border:1px dashed var(--line);color:var(--muted)}
.hmt.sel{outline:2.5px solid var(--accent);outline-offset:-1px}
.hmlg{display:flex;gap:2px;align-items:center;margin:8px 0 2px;font-size:10px;color:var(--muted)}
.hmlg i{flex:1;height:14px;border-radius:3px;display:flex;align-items:center;justify-content:center;font-style:normal;font-family:var(--f-num);font-size:9px;min-height:60px;min-height:14px}
.hmd{margin-top:10px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px}
.hmd h3{margin:0 0 4px;font-size:15px;display:flex;justify-content:space-between;align-items:center;gap:6px}
.hmd h3 a{font-size:12px;font-weight:500;color:var(--accent);text-decoration:none;white-space:nowrap;margin-left:8px}
.hmd .hmt{min-height:50px}
</style>
"""

SEC = r"""<section id="hmap" hidden>
  <div class="ehead"><a href="#">← 首頁</a><span class="meta" id="hmAsof"></span></div>
  <h1 style="font-size:22px;margin:6px 0 0">🗺️ 主題熱力圖</h1>
  <div class="hmc"><div class="hmseg" id="hmP"><button data-p="d">日</button><button data-p="w">週</button><button data-p="m">月</button><button data-p="q">季</button></div><div class="hmseg" id="hmS"><button data-s="o">順序</button><button data-s="v">漲幅</button></div></div>
  <p class="foot" id="hmTake" style="margin:0 0 6px"></p>
  <div class="hm" id="hmG"></div>
  <div class="hmlg" id="hmLg"></div>
  <div class="hmd" id="hmD" hidden></div>
  <p class="foot" id="hmFoot"></p>
</section>
"""

JS = r"""
// ---- 🗺️ 主題熱力圖（2026-11-22）：等大方格、成份股中位數、固定七階色 ----
let HMP=(()=>{const v=store.get('hmP');return ['d','w','m','q'].includes(v)?v:'d'})(),HMS=store.get('hmS')==='v'?'v':'o',HMSEL=null;
const HMTH={d:[.5,1.5,3],w:[1.5,4,8],m:[3,8,15],q:[5,12,25]},HML={d:'日',w:'週',m:'月',q:'季'};
const hmV=(id,k)=>{if(k==='d')return sv(id,'chg');if(!MO)return null;const i={w:0,m:1,q:2}[k];if(MO.da&&MO.da[id]&&MO.da[id][i]!=null)return MO.da[id][i];if(k!=='w'&&MO.dc&&MO.dc[id])return MO.dc[id][k==='m'?0:1];return MO.d[id]?MO.d[id][i]:null};
const hmLv=(v,k)=>{if(v==null)return null;const t=HMTH[k],a=Math.abs(v),l=a<t[0]?0:a<t[1]?1:a<t[2]?2:3;return v<0?-l:l};
const hmNm=t=>t.name.replace(/^\p{Extended_Pictographic}️?\s*/u,'');
const hmCap=id=>{const c=sv(id,'close'),s=S&&S.sh&&S.sh[id];return c&&s?c*s:0};
function hmStat(t){const ids=[...new Set(t.stocks.map(x=>x[0]))],vs=ids.map(i=>hmV(i,HMP)).filter(v=>v!=null);return {t,ids,n:vs.length,up:vs.filter(v=>v>0).length,dn:vs.filter(v=>v<0).length,m:median(vs)}}
function hmTile(lab,v,sub,attrs,sz){const l=hmLv(v,HMP);return `<button type="button" class="hmt ${l==null?'na':'l'+l}" ${attrs}><span class="n ${sz}">${esc(lab)}</span><span class="p">${v==null?'—':pct(v,HMP==='d'?2:1)}</span>${sub?`<span class="c">${sub}</span>`:''}</button>`}
const hmSz=s=>{const w=[...s].reduce((a,c)=>a+(/[\x00-\xff]/.test(c)?.55:1),0);return w>8.5?'s2':w>7?'s1':''};
function renderHmap(){
  $('hmP').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.p===HMP));
  $('hmS').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.s===HMS));
  const A=THEMES.filter(t=>!isAuto(t.id)&&!t.favt&&!t.etf&&t.stocks&&t.stocks.length);
  let R=A.map(hmStat);if(HMS==='v')R=[...R].sort((a,b)=>a.m==null?1:b.m==null?-1:b.m-a.m);
  const asof=HMP==='d'?(S&&S.pxAsof):(MO&&MO.asof),md=s=>s?`${+s.slice(4,6)}/${+s.slice(6,8)}`:'';
  $('hmAsof').textContent=asof?`收盤日 ${s2d(asof)}`:'';
  const ok=R.filter(r=>r.m!=null),u=ok.filter(r=>r.m>0).length,d=ok.filter(r=>r.m<0).length,srt=[...ok].sort((a,b)=>b.m-a.m);
  $('hmTake').innerHTML=ok.length?`<b>${HML[HMP]}</b>漲跌・${ok.length} 個主題：<span class="up">上漲 ${u}</span>・<span class="dn">下跌 ${d}</span>　最強 <b>${esc(hmNm(srt[0].t))}</b> <span class="${sign(srt[0].m)}">${pct(srt[0].m,1)}</span>・最弱 <b>${esc(hmNm(srt[srt.length-1].t))}</b> <span class="${sign(srt[srt.length-1].m)}">${pct(srt[srt.length-1].m,1)}</span>`:'資料還沒載入';
  $('hmG').innerHTML=R.map(r=>{const nm=hmNm(r.t);return hmTile(nm,r.m,r.n?`${r.up}/${r.n}↑`:'',`data-ht="${esc(r.t.id)}"${r.t.id===HMSEL?' aria-current="true"':''}`,hmSz(nm))}).join('');
  $('hmG').querySelectorAll('.hmt').forEach(b=>b.classList.toggle('sel',b.dataset.ht===HMSEL));
  const T=HMTH[HMP];$('hmLg').innerHTML=`<span style="margin-right:3px">跌</span>`+[-3,-2,-1,0,1,2,3].map(l=>`<i class="hmt l${l}" style="padding:0">${l===0?'0':(l<0?'−':'+')+T[Math.abs(l)-1]}</i>`).join('')+`<span style="margin-left:3px">漲</span>`;
  hmDetail();
  $('hmFoot').innerHTML=`每一格＝一個產業主題 (首頁主題表的內建＋自訂主題，不含 ETF、0050、注意股、投信買超、⭐自選這些自動名單；首頁隱藏的主題這裡也不出現)。數字＝成份股漲跌的<b>中位數</b> (不讓台積電、鴻海一檔決定整格顏色)；第三行「7/10↑」＝有資料的 10 檔中 7 檔上漲。<b>顏色固定七階</b>，同一個顏色每天代表一樣的幅度：最淺＝${T[0]}～${T[1]}%、中＝${T[1]}～${T[2]}%、最深＝${T[2]}% 以上，±${T[0]}% 以內灰色 (週 ±1.5/4/8%、月 ±3/8/15%、季 ±5/12/25%、日 ±0.5/1.5/3%)。日＝最新收盤漲跌 (盤後更新，盤中看到的是前一交易日)；週/月/季＝跟首頁一樣用還原價，週＝5 個交易日、月/季＝日曆日 (月基準 ${md(MO&&MO.calBase&&MO.calBase.m)}、季基準 ${md(MO&&MO.calBase&&MO.calBase.q)})。「順序」＝首頁主題表的順序 (含你的手動排序)，「漲幅」＝由強到弱。點格子＝下方展開成份股 (依市值排)；華通、啟碁、兆赫在兩個主題都會算。`;
}
function hmDetail(){const el=$('hmD'),t=HMSEL&&THEMES.find(x=>x.id===HMSEL);if(!t){el.hidden=true;return}
  const r=hmStat(t),ids=[...r.ids].sort((a,b)=>hmCap(b)-hmCap(a));
  el.hidden=false;el.innerHTML=`<h3><span>${esc(t.name)} <span class="${sign(r.m)}" style="font-family:var(--f-num)">${pct(r.m,HMP==='d'?2:1)}</span></span><span><a href="scan.html#${esc(t.id)}">📈 掃 K 線</a><a href="#t/${esc(t.id)}">📋 主題頁</a></span></h3><p class="foot" style="margin:0 0 6px">${HML[HMP]}漲跌・${r.n} 檔：上漲 ${r.up}・下跌 ${r.dn}・依市值由大到小，點一格看個股</p><div class="hm m3">`+
    ids.map(i=>{const nm=nameOf(i),v=hmV(i,HMP),c=hmCap(i);return hmTile(nm,v,c?`${i}・${c>=1e12?fmt(c/1e12,1)+'兆':fmt(c/1e8,0)+'億'}`:i,`data-hs="${i}"`,hmSz(nm))}).join('')+'</div>'}
document.addEventListener('click',e=>{if(!document.body||document.body.dataset.view!=='hmap')return;
  const p=e.target.closest('#hmP button'),s=e.target.closest('#hmS button'),g=e.target.closest('[data-ht]'),k=e.target.closest('[data-hs]');
  if(p){HMP=p.dataset.p;store.set('hmP',HMP);renderHmap()}
  else if(s){HMS=s.dataset.s;store.set('hmS',HMS);renderHmap()}
  else if(g){HMSEL=HMSEL===g.dataset.ht?null:g.dataset.ht;renderHmap();if(HMSEL)setTimeout(()=>$('hmD').scrollIntoView({behavior:'smooth',block:'nearest'}),30)}
  else if(k){location.hash=k.dataset.hs}});
const s2d=s=>`${s.slice(0,4)}/${s.slice(4,6)}/${s.slice(6,8)}`;
"""

E = [
    ('</head>', CSS + '</head>'),
    ('<section id="srank" hidden>', SEC + '<section id="srank" hidden>'),
    ("['home','theme','tlist','tedit','flist','srank']", "['home','theme','tlist','tedit','flist','srank','hmap']"),
    ("  else if(h==='s'){show('srank')",
     "  else if(h==='h'){show('hmap');document.title='主題熱力圖';renderHmap();if(VPREV!=='stock')scrollTo(0,0)}\n  else if(h==='s'){show('srank')"),
    ('<a class="act" href="#e">✏️ 編輯</a></span></h2>',
     '<a class="act" href="#h" aria-label="主題熱力圖" title="主題熱力圖">🗺️</a><a class="act" href="#e">✏️ 編輯</a></span></h2>'),
    ('<div class="hub" id="hub"><a class="srlink" href="scan.html"><b>📈 K 線掃描</b><span>一面小卡掃 K、量、投信外資</span></a>',
     '<div class="hub" id="hub"><a class="srlink" href="scan.html"><b>📈 K 線掃描</b><span>一面小卡掃 K、量、投信外資</span></a>'
     '<a class="srlink" href="#h"><b>🗺️ 主題熱力圖</b><span>一屏看各主題日/週/月/季強弱</span></a>'),
    ("function applyCfg(){THEMES=allThemes().filter(t=>!t.hidden)}", JS + "function applyCfg(){THEMES=allThemes().filter(t=>!t.hidden)}"),
    ('<span style="opacity:.5">v1122h</span>', '<span style="opacity:.5">v1122i</span>'),
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
