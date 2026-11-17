#!/usr/bin/env python3
"""2026-11-17 掃描頁：全主題即時報價預抓＋「下一主題」鈕

用法：python3 patch_pf.py            → 讀 scan.html，輸出 beta_scan_pf.html
      python3 patch_pf.py prod       → 直接改 scan.html（已套用過會因 assert 中止）

起因：世杰 9 點多掃各主題 K 線，小卡多半還是「昨」。原因＝只問畫面上看得到的小卡（≤25 檔）、
      60 秒一輪、滑動不補問；日漲排序又把「昨」排最後，往下滑到的剛好都是沒問過的。
做法（方案 Ⓐ）：
  1. 進主題 0.3 秒就問整份名單（≤40 檔一次問完；>40 檔先問畫面上的，其餘排進背景）。
  2. 背景預抓：所有主題的成份股依「目前主題之後」的順序，每批 40 檔、只用證交所 MIS（&src=mis，
     不吃富果額度），抓完後每 5 分鐘整輪更新；「下一主題」每 60 秒更新並先載入它的日K分片。
  3. 進主題時報價在 50 秒內就不再問（直接畫今日棒，不會先「昨」再重排）。
  4. 滑動停下 0.35 秒，畫面上有小卡還沒拿到今天報價就立刻補問。
  5. 小卡下方加「‹ 上一個｜下一主題 XXX N ›」，順序＝上方名單橫列。
"""
import sys

PROD = len(sys.argv) > 1 and sys.argv[1] == 'prod'
SRC = 'scan.html'
OUT = 'scan.html' if PROD else 'beta_scan_pf.html'
VER = 'v1117d'

s = open(SRC, encoding='utf-8').read()
assert 'pfRun' not in s, '已套用過'


def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (s.count(old), old[:80])
    s = s.replace(old, new)


# ---- CSS ----
rep('.foot{padding:4px 12px 12px;',
    '/* 2026-11-17 下一主題鈕 */\n'
    '.nx{display:flex;gap:6px;padding:0 5px 10px}\n'
    '.nx[hidden]{display:none}\n'
    '.nx button{font:600 15px/1.3 var(--f-body);padding:12px 10px;border-radius:12px;border:1px solid var(--line);background:var(--card);color:var(--fg);-webkit-tap-highlight-color:transparent}\n'
    '.nx .p{flex:0 0 auto;color:var(--muted);font-weight:500}\n'
    '.nx .n{flex:1;min-width:0;background:var(--sel);color:var(--selfg);border-color:transparent}\n'
    '.nx small{opacity:.65;font-weight:400;font-size:12px}\n'
    '.foot{padding:4px 12px 12px;')

# ---- HTML ----
rep('<p class="foot" id="foot"></p>', '<div class="nx" id="nx" hidden></div>\n<p class="foot" id="foot"></p>')

# ---- pick()：換名單就重畫下一主題鈕 ----
rep("async function pick(sel){cur=sel;apClose();", "async function pick(sel){cur=sel;apClose();nxPaint();")

# ---- render()：統計列尾端放預抓進度 ----
rep("投信連買≥3 <b>${ROWS.filter(r=>r.ts>=3).length}</b> 檔・點小卡放大`:'';",
    "投信連買≥3 <b>${ROWS.filter(r=>r.ts>=3).length}</b> 檔・點小卡放大<span id=\"pfS\"></span>`:'';pfPaint();")

# ---- 版本、頁尾說明 ----
rep('<span style="opacity:.5">v1115t</span>',
    '統計列的 <b>⚡ N／M</b>＝所有主題成份股的即時報價已先抓好幾檔（盤中才有；抓完後切主題不用再等）；小卡最下方「下一主題 ›」照上方名單順序換下一個。 <span style="opacity:.5">' + VER + '</span>')

rep('（每 60 秒更新畫面上看得到的小卡；', '（進名單就問整份名單、之後每 60 秒更新；超過 40 檔的名單先問畫面上的，其餘背景補上；')
# ---- liveWant：≤40 檔的名單整份問，不只看畫面上的 ----
rep("  return CUR_IDS.some(c=>VISIBLE.has(c)&&MKT[c]&&!liveHasToday(c))}",
    "  {const A=CUR_IDS.filter(lvOK);return (A.length<=LV_MAX?A:A.filter(c=>VISIBLE.has(c))).some(c=>!liveHasToday(c))}}")

# ---- liveRefresh 整段換掉 ----
a = s.index('async function liveRefresh(){')
b = s.index('function liveDbgShow(){')
NEW_REFRESH = r'''// 2026-11-17 Ⓐ 全主題預抓：進主題就問整份名單（≤40 檔）；kick＝剛進主題／回前景／滑動停下，只問超過 50 秒沒更新的
const LV_MAX=40,LV_FRESH=50000,PF_TTL=300000,PFAT=new Map(),PF={busy:false,have:0,total:0,off:0,n:0,last:''};
const lvSleep=ms=>new Promise(r=>setTimeout(r,ms));
function lvOK(c){return !!MKT[c]&&/^[0-9A-Za-z]{2,6}$/.test(c)}
function lvAge(c){const q=LIVE.get(c);return Date.now()-Math.max(q&&q._at||0,PFAT.get(c)||0)}
function lvAgeF(c){const q=LIVE.get(c);return Date.now()-(q&&q._at||0)}   // 只看前景／背景真的拿到報價的時間（背景沒拿到的，進主題要用富果／Yahoo 補問）
function lvRepaint(){const top=scrollY;ROWS=CUR_IDS.map((c,i)=>{const r=build(c);if(r)r.li=i;return r}).filter(Boolean);render();scrollTo(0,top);if(openI>=0){SHR=rows();fillSheet()}}
function lvUrl(ids){return LIVE_API+'/?s='+ids.map(c=>(MKT[c]==='上櫃'?'otc_':'tse_')+c).join(',')}
function liveMerge(j,ids,bg){const now=Date.now(),today=tpe().ymd,open=marketOpenNow();let n=0;
  if(!bg){const got=new Set(j.q.map(q=>q&&q.c));ids.forEach(c=>{if(!got.has(c)&&!LIVE.get(c))LIVE.set(c,{c,miss:true,_at:now})})}
  j.q.forEach(q=>{if(!q||!q.c)return;const old=LIVE.get(q.c);if(q.src==='yahoo'&&old&&old.src!=='yahoo'&&now-old._at<15*60000)return;
    if(q.z==null&&q.pz==null&&old&&!old.miss&&old.d===q.d&&(old.z??old.pz)!=null)q.pz=old.z??old.pz;   // 這輪沒成交價就沿用上一輪的最後成交價
    // 2026-10-30：收盤後拿到的報價若日期不是今天（來源回舊快照），視同沒拿到→小標 ○、下一輪再問，不再默默停在「昨」
    if(!open&&q.d&&q.d<today){if(!bg)LIVE.set(q.c,{c:q.c,miss:true,_at:now,_old:q});return}
    q._at=now;LIVE.set(q.c,q);if(q.d>=today)n++});
  return n}
async function liveRefresh(kick){if(liveBusy||!liveWant())return;const open=marketOpenNow();
  const all=CUR_IDS.filter(lvOK);let ids=all;
  if(all.length>LV_MAX){const vis=all.filter(c=>VISIBLE.has(c));ids=(vis.length?vis:all).slice(0,LV_MAX)}
  if(!open)ids=ids.filter(c=>!liveHasToday(c)&&lvAgeF(c)>LV_FRESH);else if(kick===true)ids=ids.filter(c=>lvAgeF(c)>LV_FRESH);
  if(!ids.length){pfRun();return}liveBusy=true;
  try{const ctl=new AbortController(),to=setTimeout(()=>ctl.abort(),20000);
    // 投本比即時頁 90 秒內有刷新（localStorage 心跳）→ 讓它優先用富果；否則這頁帶 p=1 自己優先
    let hb=0;try{hb=+localStorage.getItem('live_hb')||0}catch(e){}const pri=Date.now()-hb>90000;
    const res=await fetch(lvUrl(ids)+(pri?'&p=1':''),{signal:ctl.signal,cache:'no-store'});clearTimeout(to);
    const j=await res.json();if(j&&j.q){liveMerge(j,ids,false);
      if(!open)liveAfterClose++;
      LIVE_DBG={at:new Date().toTimeString().slice(0,8),ask:ids,n:j.n,src:j.src,fb:j.fb,err:j.err,q:j.q.map(q=>q&&[q.c,q.d,q.t,q.z??q.pz,q.src].join('|'))};if(location.search.includes('dbg=1'))liveDbgShow();
      lvRepaint()}
  }catch(e){}
  liveBusy=false;pfRun()}
// ---- 背景預抓：其他主題的成份股，只用證交所 MIS（不吃富果額度），不重畫畫面 ----
function nxAdj(d){if(!cur||cur.kind!=='t'||THEMES.length<2)return null;const i=THEMES.findIndex(t=>t.id===cur.id);return i<0?null:THEMES[(i+d+THEMES.length)%THEMES.length]}
function pfOrder(){const i=cur&&cur.kind==='t'?THEMES.findIndex(t=>t.id===cur.id):-1,seq=i<0?THEMES:[...THEMES.slice(i+1),...THEMES.slice(0,i)],seen=new Set(),out=[];
  const add=c=>{if(lvOK(c)&&!seen.has(c)){seen.add(c);out.push(c)}};CUR_IDS.forEach(add);seq.forEach(t=>t.stocks.forEach(x=>add(x[0])));return out}
function pfWant(){if(document.visibilityState!=='visible'||Date.now()<PF.off)return false;if(marketOpenNow())return true;const t=tpe();return t.dow>=1&&t.dow<=5&&t.min>13*60+36&&shardLatest()<t.ymd}
function pfPaint(){const el=document.getElementById('pfS');if(!el)return;const on=PF.total&&(marketOpenNow()||PF.have);
  el.innerHTML=on?`・<span title="所有主題成份股的即時報價已先抓好的檔數（只用證交所來源，每 5 分鐘整輪更新；下一主題每分鐘更新）">⚡ ${PF.have}／${PF.total}</span>`:''}
async function pfRun(){if(PF.busy||!pfWant())return;PF.busy=true;
  try{const ord=pfOrder(),nt=nxAdj(1),nx=new Set(nt?nt.stocks.map(x=>x[0]):[]),open=marketOpenNow(),today=tpe().ymd;PF.total=ord.length;const CS=new Set(CUR_IDS),sel0=cur;let dirty=false;const flush=()=>{if(dirty&&cur===sel0){dirty=false;lvRepaint()}};
    const cnt=()=>{PF.have=ord.filter(c=>{const q=LIVE.get(c);return q&&!q.miss&&q.d===today}).length;pfPaint()};cnt();
    if(nt)[...new Set([...nx].map(c=>c.slice(0,2)))].forEach(g=>loadShard(g));   // 下一主題的日K分片先載好
    let need=ord.filter(c=>open?lvAge(c)>(nx.has(c)?LV_FRESH:PF_TTL):(!liveHasToday(c)&&lvAge(c)>PF_TTL)),bad=0;
    while(need.length&&bad<2&&pfWant()){
      if(liveBusy){await lvSleep(300);continue}
      const ids=need.slice(0,LV_MAX);need=need.slice(LV_MAX);let n=-1;
      try{const ctl=new AbortController(),to=setTimeout(()=>ctl.abort(),12000);const res=await fetch(lvUrl(ids)+'&src=mis',{signal:ctl.signal,cache:'no-store'});clearTimeout(to);
        const j=await res.json();const now=Date.now();ids.forEach(c=>PFAT.set(c,now));if(j&&j.q){n=liveMerge(j,ids,true);PF.n++;if(n>0&&ids.some(c=>CS.has(c)))dirty=true;else flush()}PF.last=new Date().toTimeString().slice(0,8)+' '+ids.length+'→'+n+(j&&j.err&&j.err.length?' '+j.err[0]:'')}catch(e){PF.last='err '+String(e&&e.message||e)}
      if(n<=0)bad++;else bad=0;cnt();await lvSleep(500)}
    flush();
    if(bad>=2)PF.off=Date.now()+(open?120000:900000);   // 連兩批沒有今天的報價（證交所掛了／休市）→ 先停一陣子，進主題時照舊用富果／Yahoo 補
  }catch(e){}
  PF.busy=false;if(location.search.includes('dbg=1'))liveDbgShow()}
// ---- 下一主題鈕（順序＝上方名單橫列）----
function nxPaint(){const el=document.getElementById('nx');if(!el)return;const n=nxAdj(1);if(!n){el.hidden=true;return}
  const nm=t=>t.name.replace(/\s*[（(]\d{1,2}\/\d{1,2}[）)]\s*$/,''),last=THEMES.findIndex(t=>t.id===cur.id)===THEMES.length-1;el.hidden=false;
  el.innerHTML=`<button class="p" data-d="-1" title="上一主題：${esc(nm(nxAdj(-1)))}">‹ 上一個</button><button class="n" data-d="1">${last?'↺ 回第一個':'下一主題'}　${esc(nm(n))} <small>${n.stocks.length}</small> ›</button>`}
document.getElementById('nx').addEventListener('click',e=>{const b=e.target.closest('button[data-d]');if(!b)return;const t=nxAdj(+b.dataset.d);if(t){pick({kind:'t',id:t.id});scrollTo(0,0)}});
// 滑動停下：畫面上有小卡還沒拿到今天的報價就立刻補問（不用等 60 秒那一輪）
{let st=0;addEventListener('scroll',()=>{clearTimeout(st);st=setTimeout(()=>{if(CUR_IDS.some(c=>VISIBLE.has(c)&&lvOK(c)&&!liveHasToday(c)&&lvAgeF(c)>LV_FRESH))liveRefresh(true)},350)},{passive:true})}
'''
s = s[:a] + NEW_REFRESH + s[b:]

# ---- 除錯面板多列預抓狀態 ----
rep("+'\\n輪數='+liveAfterClose+' 可視='+[...VISIBLE].join(',')}",
    "+'\\n輪數='+liveAfterClose+' 可視='+[...VISIBLE].join(',')+'\\n預抓='+PF.have+'／'+PF.total+' 批次='+PF.n+' 最後='+PF.last+(PF.off>Date.now()?' 暫停中':'')}")

# ---- liveKick：首問 1.5 秒 → 0.3 秒；每個名單各自算收盤後補問輪數 ----
rep("function liveKick(){clearInterval(liveTimer);liveTimer=setInterval(liveRefresh,60000);setTimeout(liveRefresh,1500)}",
    "function liveKick(){clearInterval(liveTimer);liveAfterClose=0;liveTimer=setInterval(()=>liveRefresh(),60000);setTimeout(()=>liveRefresh(true),300)}")
rep("document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')liveRefresh()});",
    "document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')liveRefresh(true)});")

# ---- load()：進名單後畫下一主題鈕（名單檔數可能跟著日期變）----
rep("render();liveKick();if(MODE==='v')valKick();", "render();nxPaint();liveKick();if(MODE==='v')valKick();")

if not PROD:
    s = s.replace('<title>', '<title>β ', 1)
open(OUT, 'w', encoding='utf-8').write(s)
print('wrote', OUT, len(s))
