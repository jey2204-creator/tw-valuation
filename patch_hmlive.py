#!/usr/bin/env python3
"""2026-11-23 18:49 主題熱力圖「日」接即時（世杰選「① 自動即時，出 beta」）。
- 盤中（平日 08:59～13:36）熱力圖畫面開著＋前景時，向 Cloudflare Worker（twse-live，跟掃描頁同一個）問全部主題成份股即時報價：
  先用 &src=mis（只問證交所 MIS，不吃富果額度），每批 40 檔、間隔 0.3 秒；MIS 沒拿到的再問一輪不帶 src（MIS→富果→Yahoo），
  都不帶 p=1（投本比頁優先用富果）。之後每 60 秒一輪；切到背景就停。
- 收盤後：排程還沒把今天收盤寫進 summary.json（pxAsof < 今天）前，繼續補問（最多 12 輪），不會跳回昨天。
- 日漲跌＝即時價（z，沒成交用 pz）÷ 昨收（y）−1；summary 已是今天的就用 summary。週/月/季維持收盤資料。
- 標題「即時 12:27・238/243 檔」；展開的成份股也是即時；底部多留 90px（Safari 網址列）。
- 網址加 ?hlnow=YYYYMMDDHHMM 可模擬時間（測試用）。
用法：python3 patch_hmlive.py → beta.html；python3 patch_hmlive.py prod → index.html（只能對沒有 HLIVE 的 index 跑一次）。
"""
import sys, re
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'

JS = r"""
// ---- 熱力圖即時（2026-11-23）：Worker twse-live，先 MIS、缺的再一輪 MIS→富果→Yahoo，不帶 p=1 ----
const HL_API='https://twse-live.jey2204.workers.dev',HLIVE=new Map();let hlBusy=false,hlAfter=0,hlLast='',hlTimer=null;
function hlTpe(){const m=/hlnow=(\d{12})/.exec(location.search);if(m){const s=m[1];const d=new Date(Date.UTC(+s.slice(0,4),+s.slice(4,6)-1,+s.slice(6,8),+s.slice(8,10),+s.slice(10,12)));return {ymd:s.slice(0,8),min:d.getUTCHours()*60+d.getUTCMinutes(),dow:d.getUTCDay(),hm:s.slice(8,10)+':'+s.slice(10,12)}}
  const d=new Date(Date.now()+8*3600e3);return {ymd:d.toISOString().slice(0,10).replace(/-/g,''),min:d.getUTCHours()*60+d.getUTCMinutes(),dow:d.getUTCDay(),hm:d.toISOString().slice(11,16)}}
const hlOpen=()=>{const t=hlTpe();return t.dow>=1&&t.dow<=5&&t.min>=8*60+59&&t.min<=13*60+36};
const hlMk=c=>{const x=LIST.find(r=>r[0]===c);return x?x[2]:null};
function hlIds(){const s=new Set();THEMES.filter(t=>!isAuto(t.id)&&!t.favt&&!t.etf&&t.stocks).forEach(t=>t.stocks.forEach(x=>{if(/^[0-9A-Za-z]{4,6}$/.test(x[0])&&hlMk(x[0]))s.add(x[0])}));return [...s]}
const hlToday=c=>{const q=HLIVE.get(c);return !!(q&&q.d===hlTpe().ymd)};
const hlSumToday=()=>!!(S&&S.pxAsof&&S.pxAsof>=hlTpe().ymd);
function hlWant(){if(document.visibilityState!=='visible'||!document.body||document.body.dataset.view!=='hmap')return false;if(hlSumToday())return false;
  if(hlOpen())return true;const t=hlTpe();if(!(t.dow>=1&&t.dow<=5&&t.min>13*60+36))return false;return hlAfter<12&&hlIds().some(c=>!hlToday(c))}
const hlUrl=(ids,mis)=>HL_API+'/?s='+ids.map(c=>(hlMk(c)==='上櫃'?'otc_':'tse_')+c).join(',')+(mis?'&src=mis':'');
async function hlAsk(ids,mis){const today=hlTpe().ymd;let n=0;for(let k=0;k<ids.length;k+=40){const part=ids.slice(k,k+40);
  try{const ctl=new AbortController(),to=setTimeout(()=>ctl.abort(),15000);const r=await fetch(hlUrl(part,mis),{signal:ctl.signal,cache:'no-store'});clearTimeout(to);const j=await r.json();
    (j&&j.q||[]).forEach(q=>{if(!q||!q.c||q.d!==today)return;const px=q.z!=null?q.z:q.pz!=null?q.pz:(HLIVE.get(q.c)||{}).px;if(px==null||!q.y)return;HLIVE.set(q.c,{px,y:q.y,d:q.d,t:q.t,src:q.src,_at:Date.now()});n++})}catch(e){}
  if(k+40<ids.length)await new Promise(r=>setTimeout(r,300))}return n}
async function hlRefresh(){if(hlBusy||!hlWant())return;hlBusy=true;
  try{const open=hlOpen(),all=hlIds(),fresh=c=>{const q=HLIVE.get(c);return q&&q.d===hlTpe().ymd&&Date.now()-q._at<50000};
    let ids=open?all.filter(c=>!fresh(c)):all.filter(c=>!hlToday(c));
    if(ids.length){await hlAsk(ids,true);const miss=ids.filter(c=>!hlToday(c)||(open&&!fresh(c)));if(miss.length&&miss.length<=120)await hlAsk(miss,false)}
    if(!open)hlAfter++;hlLast=hlTpe().hm;if(document.body.dataset.view==='hmap')renderHmap()}catch(e){}
  hlBusy=false}
function hlKick(){hlRefresh();if(!hlTimer)hlTimer=setInterval(hlRefresh,60000)}
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')hlRefresh()});
function hlD(id){if(hlSumToday())return null;const q=HLIVE.get(id);return q&&q.d===hlTpe().ymd?(q.px/q.y-1)*100:null}
"""

E = [
    ("const hmV=(id,k)=>{if(k==='d')return sv(id,'chg');",
     JS + "const hmV=(id,k)=>{if(k==='d'){const l=hlD(id);return l!=null?l:sv(id,'chg')}"),
    ("$('hmAsof').textContent=asof?`收盤日 ${s2d(asof)}`:'';",
     "{const ids=hlIds(),nl=ids.filter(c=>hlD(c)!=null).length;$('hmAsof').innerHTML=HMP==='d'&&nl?`<b style=\"color:var(--accent)\">即時 ${esc(hlLast||'')}</b>・${nl}/${ids.length} 檔`:(asof?`收盤日 ${s2d(asof)}`:'')}"),
    ("show('hmap');document.title='主題熱力圖';renderHmap();",
     "show('hmap');document.title='主題熱力圖';renderHmap();hlKick();"),
    ('<section id="hmap" hidden>', '<section id="hmap" hidden style="padding-bottom:90px">'),
    ("`每一格＝一個產業主題",
     "`<b>盤中即時</b>：日＝即時價對昨收 (跟掃描頁同一個來源，先問證交所，沒拿到的再問富果/Yahoo；畫面開著每 60 秒更新，切到背景就停)，標題顯示「即時 時間・拿到幾檔」；收盤後排程更新前也是今天的即時收盤。週/月/季仍是收盤資料，不含今天盤中。<br>每一格＝一個產業主題"),
]

s = open('index.html', encoding='utf-8').read()
assert 'HLIVE' not in s
for a, b in E:
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)
assert len(re.findall(r'opacity:\.5">v11\d\d[a-z]+</span>', s)) == 1
s = re.sub(r'opacity:\.5">v11\d\d[a-z]+</span>', 'opacity:.5">v1123a</span>', s)
if not prod:
    s = s.replace('<title>', '<title>[beta] ', 1)
dst = 'index.html' if prod else 'beta.html'
open(dst, 'w', encoding='utf-8').write(s)
print('ok', dst)
