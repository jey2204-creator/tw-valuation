#!/usr/bin/env python3
"""2026-11-07 估值掃描（方案①）：scan.html 加「K線／估值」模式切換。
估值模式：小卡改畫近 3 年迷你本益比（或淨值比）河流圖＋目前倍數與歷史分位（🔴≥80%／🟠50–80／🟢≤20%），
排序加 PE貴／PE便宜／PB貴／PB便宜，篩選加 PE≥80%／PE≤20%／PB≥80%／PB≤20%；點小卡放大＝完整本益比＋淨值比河流圖。
資料來源順序：data/<id>.json（有排程的三檔）→ 個股頁留在手機裡的 6 小時快取（live5_）→ 本頁 24 小時月資料快取（rivc_）→ FinMind 即時（TaiwanStockPrice＋TaiwanStockPER，每檔 2 次）。
用法：python3 patch_val.py scan.html beta_scan.html
"""
import sys

src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()

def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:80])
    s = s.replace(old, new)

# ---------- CSS ----------
rep('''  --f-body:"Noto Sans TC",system-ui,-apple-system,"PingFang TC",sans-serif;''',
'''  --b1:#dbe9f7; --b2:#c3dcf0; --b3:#e6ecd2; --b4:#f6e1bd; --b5:#f3c7b3; --price:#151a23;
  --f-body:"Noto Sans TC",system-ui,-apple-system,"PingFang TC",sans-serif;''')
rep('''--chip:#222835; --sel:#e8ebf0; --selfg:#151a23; color-scheme:dark}}''',
'''--chip:#222835; --sel:#e8ebf0; --selfg:#151a23; --b1:#1b2b40; --b2:#20374f; --b3:#2d3a28; --b4:#463821; --b5:#4d2b24; --price:#f4f6fa; color-scheme:dark}}''')
rep('''.sb .per button{flex:none;padding:0 9px}''',
'''.sb .per button,.sb .mode button,.sb .rv button{flex:none;padding:0 9px}
/* 2026-11-07 估值掃描：模式鈕（K線／估值）＋河流選擇（本益比／淨值比）；小卡估值列 */
.sb .mode button[aria-pressed=true]{background:var(--accent);border-color:var(--accent);color:#fff}
.km-s .pv{display:inline-flex;align-items:center;gap:2px;flex:1 1 0;min-width:0;overflow:hidden}
.km-s .pv i{font-style:normal;color:var(--muted);font-weight:600;font-size:8.5px}
.km-s .pv b{font-weight:700;padding:0 3px;border-radius:3px;color:#fff;background:var(--muted)}
.km-s .pv b.p4{background:var(--up)}.km-s .pv b.p3{background:#d9731a}.km-s .pv b.p2{background:var(--muted)}.km-s .pv b.p1{background:var(--down)}.km-s .pv b.p0{background:var(--chip);color:var(--muted)}
.km-s .pv.off{opacity:.6;flex:0 0 auto}
.km.vld .km-cv{opacity:.35}
.tg.cy{background:var(--warm)}
.sh-cv.rv{height:210px}
.sh-t{font-size:12.5px;line-height:1.5;margin:4px 0 2px}.sh-t b{font-weight:900}.sh-t .pill{display:inline-block;padding:0 6px;border-radius:9px;background:#f6e1bd;color:#4a3000;font:700 11.5px var(--f-num)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .sh-t .pill{background:#463821;color:#f0d9b0}}
.cnt button{color:var(--accent);font-weight:700;padding:0 4px}''')

# ---------- HTML 控制列 ----------
rep('''<select id="ndSel" hidden title="看哪一天的注意名單"></select><span class="sp"></span><span class="per" style="display:contents">''',
'''<select id="ndSel" hidden title="看哪一天的注意名單"></select><span class="sp"></span><span class="mode" style="display:contents"><button data-m="k" aria-pressed="true" title="K 線掃描">K線</button><button data-m="v" title="估值掃描：迷你河流圖＋歷史分位">估值</button></span><span class="rv" style="display:contents" hidden><button data-r="pe" aria-pressed="true">本益比</button><button data-r="pb">淨值比</button></span><span class="per" style="display:contents">''')
rep('''<button data-k="h20" title="近20日高">20高</button></div>''',
'''<button data-k="h20" title="近20日高">20高</button><button data-k="peh" class="vs" hidden title="本益比歷史分位 高→低">PE貴</button><button data-k="pel" class="vs" hidden title="本益比歷史分位 低→高">PE便宜</button><button data-k="pbh" class="vs" hidden title="淨值比歷史分位 高→低">PB貴</button><button data-k="pbl" class="vs" hidden title="淨值比歷史分位 低→高">PB便宜</button></div>''')
rep('''<button class="f" data-f="vr12" title="量比 ≥1.2">量≥1.2</button></div>''',
'''<button class="f" data-f="vr12" title="量比 ≥1.2">量≥1.2</button><button class="f vs" data-vf="pe80" hidden title="本益比分位 ≥80%（歷史偏貴）">PE≥80%</button><button class="f vs" data-vf="pe20" hidden title="本益比分位 ≤20%（歷史偏便宜）">PE≤20%</button><button class="f vs" data-vf="pb80" hidden title="淨值比分位 ≥80%">PB≥80%</button><button class="f vs" data-vf="pb20" hidden title="淨值比分位 ≤20%">PB≤20%</button></div>''')

# ---------- JS ----------
rep('''const store={get(k){try{return JSON.parse(localStorage.getItem(k))}catch(e){return null}}};''',
'''const store={get(k){try{return JSON.parse(localStorage.getItem(k))}catch(e){return null}},set(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}};''')

# init：讀模式；paintBar 顯示／隱藏估值鈕
rep('''const n=+localStorage.getItem('scanN');if([20,40,60].includes(n))N=n}catch(e){}paintBar();''',
'''const n=+localStorage.getItem('scanN');if([20,40,60].includes(n))N=n;const m=localStorage.getItem('scanMode');if(m==='v'){MODE='v';sortK=SK_V}const rv=localStorage.getItem('scanRv');if(rv==='pb')RV='pb'}catch(e){}paintBar();
  valInit();''')
rep('''function paintBar(){const cb=document.querySelector('#sortBar button[data-k=chg]');''',
'''function paintBar(){const V=MODE==='v';document.querySelectorAll('#sortBar .vs').forEach(b=>b.hidden=!V);document.querySelectorAll('#sortBar button[data-k=vr],#sortBar button[data-k=ts],#sortBar button[data-k=fs],#sortBar button[data-k=d20],#sortBar button[data-k=h20],#sortBar .f[data-f]').forEach(b=>b.hidden=V);document.querySelector('#sortBar .per').hidden=V;document.querySelector('#sortBar .rv').hidden=!V;
  document.querySelectorAll('#sortBar .mode button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.m===MODE)));document.querySelectorAll('#sortBar .rv button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.r===RV)));document.querySelectorAll('#sortBar .f[data-vf]').forEach(b=>b.setAttribute('aria-pressed',String(!!VF[b.dataset.vf])));
  const cb=document.querySelector('#sortBar button[data-k=chg]');''')
# 排序鈕點擊：模式／河流／估值篩選
rep('''    if(b.dataset.k){if(b.dataset.k==='chg'&&sortK==='chg')CHGP=CHGP==='d'?'w':CHGP==='w'?'m':'d';sortK=b.dataset.k;try{localStorage.setItem('scanChgP',CHGP)}catch(e){}}else if(b.dataset.f){FL[b.dataset.f]=!FL[b.dataset.f]}''',
'''    if(b.dataset.m){if(MODE===b.dataset.m)return;MODE=b.dataset.m;try{localStorage.setItem('scanMode',MODE)}catch(e){}if(MODE==='v'){SK_K=sortK;if(!VSK.has(sortK))sortK=SK_V}else{SK_V=sortK;if(VSK.has(sortK))sortK=SK_K}paintBar();render();if(MODE==='v')valKick();return}
    if(b.dataset.r){RV=b.dataset.r;try{localStorage.setItem('scanRv',RV)}catch(e){}paintBar();render();return}
    if(b.dataset.vf){VF[b.dataset.vf]=!VF[b.dataset.vf];paintBar();render();return}
    if(b.dataset.k){if(b.dataset.k==='chg'&&sortK==='chg')CHGP=CHGP==='d'?'w':CHGP==='w'?'m':'d';sortK=b.dataset.k;try{localStorage.setItem('scanChgP',CHGP)}catch(e){}}else if(b.dataset.f){FL[b.dataset.f]=!FL[b.dataset.f]}''')
# pick 之後載入估值
rep('''  render();liveKick();
}''', '''  render();liveKick();if(MODE==='v')valKick();
}''')
# 進榜單時預設榜序：估值模式沿用（榜序對估值也有意義）
rep('''  $('sortLi').hidden=!isN;if(isN&&!RANKED)sortK='li';else if(!isN&&sortK==='li')sortK='chg';RANKED=isN;paintBar();''',
'''  $('sortLi').hidden=!isN;if(isN&&!RANKED)sortK='li';else if(!isN&&sortK==='li')sortK=MODE==='v'?'peh':'chg';RANKED=isN;paintBar();''')
# rows：估值模式另一套排序／篩選
rep('''function rows(){let R=ROWS.filter(''', '''function rows(){return MODE==='v'?rowsV():rowsK()}
function rowsK(){let R=ROWS.filter(''')
# render：估值模式的小卡、統計列、頁尾
rep('''  const R=rows();const all=ROWS.length,nSt=ROWS.filter(r=>r.stale).length;''',
'''  if(MODE==='v')return renderV();
  const R=rows();const all=ROWS.length,nSt=ROWS.filter(r=>r.stale).length;''')
# 放大卡分流
rep('''function fillSheet(){const r=SHR[openI];if(!r)return closeSheet();const last=r.bars[r.bars.length-1];''',
'''function fillSheet(){return MODE==='v'?fillSheetV():fillSheetK()}
function fillSheetK(){const r=SHR[openI];if(!r)return closeSheet();const last=r.bars[r.bars.length-1];''')

VAL_JS = r'''
// ================= 估值掃描（2026-11-07 beta，方案①） =================
// MODE：'k' K 線掃描（原本）／'v' 估值掃描。RV：小卡畫本益比（pe）或淨值比（pb）河流。
let MODE='k',RV='pe',SK_K='chg',SK_V='peh';const VSK=new Set(['peh','pel','pbh','pbl']),VF={pe80:false,pe20:false,pb80:false,pb20:false};
const VAL={},VCUR={};let PRE=new Set(),SUM=null,VTOK=0,VERR='',VBUSY=0,VLIM=60,VLOADED=new Set();
const FM='https://api.finmindtrade.com/api/v4/data';
async function valInit(){try{const [ix,sm]=await Promise.all([fetch('data/index.json?t='+Math.floor(Date.now()/36e5)).then(r=>r.ok?r.json():[]).catch(()=>[]),fetch('data/summary.json?t='+Math.floor(Date.now()/36e5)).then(r=>r.ok?r.json():null).catch(()=>null)]);
  PRE=new Set((ix||[]).map(x=>x.id));SUM=sm&&sm.d?sm:null}catch(e){}}
// 與估值看板 index.html 同一套：bands（歷史 2／20／40／60／80／98% 分位 → 6 條色帶）、pct（高於幾 % 的月份）、band（目前在哪一帶）
function vBands(vals){const v=vals.filter(x=>x>0).sort((a,b)=>a-b);if(v.length<6)return [1,2,3,4,5,6];const nice=x=>x>=10?Math.round(x):Math.round(x*10)/10;const out=[];for(const p of [.02,.2,.4,.6,.8,.98]){let x=nice(v[Math.round(p*(v.length-1))]);if(out.length&&x<=out[out.length-1])x=nice(out[out.length-1]*1.05+(x>=10?1:0.1));out.push(x)}return out}
const vPct=(arr,v)=>{const a=arr.filter(x=>x!=null&&x>0);return a.length&&v>0?Math.round(a.filter(x=>x<=v).length/a.length*100):null};
const vBand=(ms,v)=>{for(let i=ms.length-1;i>=0;i--)if(v>=ms[i])return i===ms.length-1?`${ms[i]} 倍以上`:`${ms[i]}–${ms[i+1]} 倍`;return `${ms[0]} 倍以下`};
const pcls=p=>p==null?'p0':p>=80?'p4':p>=50?'p3':p>20?'p2':'p1';
async function fm(dataset,id,start){const r=await fetch(`${FM}?dataset=${dataset}&data_id=${id}&start_date=${start}`);let js={};try{js=await r.json()}catch(e){}
  if(r.status===402||js.status===402)throw Object.assign(new Error('FinMind 免費查詢額度已用完，請一小時後再試'),{quota:true});if(!r.ok)throw new Error(`FinMind ${r.status}`);return js.data||[]}
// 月底一筆：[YYYY-MM, 收盤, EPS(=收盤÷PE), 每股淨值(=收盤÷PB), PE, PB]（與 fetch.py／index.html 的 riv 同格式）
async function rivLive(c){const y=new Date().getFullYear(),start=`${y-6}-01-01`;const [px,per]=await Promise.all([fm('TaiwanStockPrice',c,start),fm('TaiwanStockPER',c,start)]);
  const ml=rows=>{const m={};rows.slice().sort((a,b)=>a.date<b.date?-1:1).forEach(r=>m[r.date.slice(0,7)]=r);return m};const pm=ml(px),em=ml(per),riv=[];
  Object.keys(pm).sort().forEach(k=>{if(!em[k])return;const cl=pm[k].close,pe=em[k].PER,pb=em[k].PBR;riv.push([k,cl,pe?+(cl/pe).toFixed(2):null,pb?+(cl/pb).toFixed(2):null,pe,pb])});return riv}
async function valGet(c){if(VAL[c])return VAL[c];let d=null,riv=null,cyc=false,src='';
  if(PRE.has(c)){try{const r=await fetch(`data/${c}.json?t=${Math.floor(Date.now()/36e5)}`);if(r.ok)d=await r.json()}catch(e){}}
  if(d&&d.riv){riv=d.riv;cyc=!!d.cyclical;src='排程'}
  if(!riv){const l=store.get('live5_'+c);if(l&&l.d&&l.d.riv&&l.d.riv.length){riv=l.d.riv;cyc=!!l.d.cyclical;src='個股頁快取'}}
  if(!riv){const cc=store.get('rivc_'+c);if(cc&&cc.r&&Date.now()-cc.t<24*3600e3){riv=cc.r;src='快取'}}
  if(!riv){riv=await rivLive(c);src='FinMind';if(riv.length)store.set('rivc_'+c,{t:Date.now(),r:riv})}
  riv=(riv||[]).filter(r=>r&&r[1]>0);if(riv.length<12)throw new Error('歷史不足');
  const last=riv[riv.length-1],S=SUM&&SUM.d[c];let pe=S&&S[2]!=null?S[2]:last[4],pb=S&&S[3]!=null?S[3]:last[5],px=S&&S[0]!=null?S[0]:last[1];
  if(!(pe>0))pe=null;if(!(pb>0))pb=null;
  const pes=riv.map(r=>r[4]),pbs=riv.map(r=>r[5]);
  return VAL[c]={c,riv,cyc,src,px,pe,pb,pem:vBands(pes),pbm:vBands(pbs),pePct:pe?vPct(pes,pe):null,pbPct:pb?vPct(pbs,pb):null,yrs:(riv.length/12).toFixed(1)}}
// 依目前畫面順序讀，3 檔同時；每檔讀完就補那張小卡；全部讀完重排一次。超過 VLIM 檔沒讀過的先讀前 VLIM 檔（FinMind 額度）
async function valKick(){const tok=++VTOK;VERR='';const order=rows().map(r=>r.c);const need=order.filter(c=>!VAL[c]&&!VCUR[c]&&VCUR[c]!==null);
  const batch=need.slice(0,VLIM);if(!batch.length){renderV();return}batch.forEach(c=>VCUR[c]=2);VBUSY=1;valCnt();
  let i=0;const run=async()=>{while(i<batch.length&&tok===VTOK&&!VERR){const c=batch[i++];VCUR[c]=1;try{await valGet(c);VLOADED.add(c)}catch(e){if(e.quota){VERR=e.message;delete VCUR[c]}else{VAL[c]=null;VCUR[c]=null}}
      if(tok!==VTOK)return;valPatch(c);valCnt()}};
  await Promise.all([run(),run(),run()]);if(tok!==VTOK)return;batch.forEach(c=>{if(VCUR[c]===2)delete VCUR[c]});VBUSY=0;const top=scrollY;renderV();scrollTo(0,top)}
function vInfo(c){const v=VAL[c];return v||null}
function vStat(c){const v=VAL[c];if(!v){const e=VCUR[c];return `<span class="pv off"><i>${VAL[c]===null?'讀不到':e===1?'讀取中…':e===2?'等待…':'未讀'}</i></span>`}
  const one=(lab,x,p,on)=>`<span class="pv${on?'':' off'}" title="${lab==='PE'?'本益比':'淨值比'}：目前 ${x==null?'—':x} 倍，高於近 ${v.yrs} 年 ${p==null?'—':p+'%'} 的月份"><i>${lab}</i>${x==null?'<b class="p0">'+(lab==='PE'?'虧損':'—')+'</b>':`${on?(x>=100?Math.round(x):x.toFixed(1)):''}<b class="${pcls(p)}">${p==null?'—':p+'%'}</b>`}</span>`;
  return one('PE',v.pe,v.pePct,RV==='pe')+one('PB',v.pb,v.pbPct,RV==='pb')}
function valPatch(c){const el=$('grid').querySelector(`article[data-c="${c}"]`);if(!el)return;el.querySelector('.km-s').innerHTML=vStat(c);el.classList.toggle('vld',!VAL[c]);const cv=el.querySelector('canvas');if(VAL[c]&&cv.clientWidth){drawRiver(cv,VAL[c],{mini:true,kind:RV});cv.dataset.done=1}}
function rowsV(){let R=ROWS.filter(r=>{const v=VAL[r.c];if(!VF.pe80&&!VF.pe20&&!VF.pb80&&!VF.pb20)return true;if(!v)return false;
    return (!VF.pe80||(v.pePct!=null&&v.pePct>=80))&&(!VF.pe20||(v.pePct!=null&&v.pePct<=20))&&(!VF.pb80||(v.pbPct!=null&&v.pbPct>=80))&&(!VF.pb20||(v.pbPct!=null&&v.pbPct<=20))});
  const ck=CHGK(),g=(r,k)=>{const v=VAL[r.c];return v&&v[k]!=null?v[k]:null};
  const key={li:r=>-r.li,chg:r=>(r[ck]??-9),peh:r=>g(r,'pePct')??-1,pel:r=>{const p=g(r,'pePct');return p==null?-1:100-p},pbh:r=>g(r,'pbPct')??-1,pbl:r=>{const p=g(r,'pbPct');return p==null?-1:100-p}}[sortK]||(r=>g(r,'pePct')??-1);
  return R.sort((a,b)=>key(b)-key(a)||(b.chg??0)-(a.chg??0))}
function valCnt(){const all=ROWS.length,n=ROWS.filter(r=>VAL[r.c]).length,bad=ROWS.filter(r=>VAL[r.c]===null).length,wait=ROWS.filter(r=>!VAL[r.c]&&VAL[r.c]!==null).length;
  const cntP=(k,f)=>ROWS.filter(r=>VAL[r.c]&&VAL[r.c][k]!=null&&f(VAL[r.c][k])).length;
  const unl=ROWS.filter(r=>VAL[r.c]===undefined&&!VCUR[r.c]).length,more=unl>0&&!VBUSY?`・<button id="vMore">${VERR?'再試':'再讀'} ${Math.min(VLIM,unl)} 檔</button>`:'';
  $('cnt').innerHTML=all?`<b>${rows().length}</b>／${all} 檔${wait?`・已讀 <b>${n}</b>${bad?`・${bad} 檔讀不到`:''}・<span class="miss">${wait} 檔${VERR?'停止':'讀取中'}</span>${more}`:bad?`・${bad} 檔讀不到`:''}${VERR?`・<span class="miss">${esc(VERR)}</span>`:''}・PE≥80% <b class="up">${cntP('pePct',p=>p>=80)}</b> 檔・PE≤20% <b class="dn">${cntP('pePct',p=>p<=20)}</b> 檔・PB≥80% <b class="up">${cntP('pbPct',p=>p>=80)}</b> 檔・點小卡放大`:'';
  const mb=$('vMore');if(mb)mb.onclick=()=>{valKick()}}
function renderV(){const R=rows();if(!R.length){$('grid').innerHTML=`<div class="empty">${ROWS.length?'沒有符合篩選條件的股票（估值資料還沒讀完的不算）':'這個清單讀不到資料'}</div>`;valCnt();return}
  $('grid').innerHTML=R.map((r,i)=>{const v=VAL[r.c];return `<article class="km${v?'':' vld'}${v&&(RV==='pe'?v.pePct:v.pbPct)>=80?' hot':''}" data-i="${i}" data-c="${esc(r.c)}" role="button" tabindex="0">
    <div class="km-h"><span class="rk">${i+1}</span><b>${esc(r.n)}</b><span class="cd">${esc(r.c)}</span>${v&&v.cyc?'<span class="tg cy" style="margin-left:auto" title="循環股：EPS 高峰時本益比偏低、谷底時偏高，請看淨值比">循</span>':''}${nbadge(r.c)}</div>
    <div class="km-s">${vStat(r.c)}</div>
    <canvas class="km-cv"></canvas></article>`}).join('');
  const io=new IntersectionObserver(es=>{es.forEach(e=>{if(!e.isIntersecting)return;const el=e.target,cv=el.querySelector('canvas'),v=VAL[el.dataset.c];if(!cv.dataset.done&&v){drawRiver(cv,v,{mini:true,kind:RV});cv.dataset.done=1}io.unobserve(el)})},{rootMargin:'300px 0px'});
  $('grid').querySelectorAll('.km').forEach(el=>{io.observe(el);el.onclick=()=>openSheet(R,+el.dataset.i);el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();openSheet(R,+el.dataset.i)}}});
  valCnt();
  $('foot').innerHTML=`<b>估值掃描（beta）</b>：小卡＝近 3 年的<b>${RV==='pe'?'本益比':'淨值比'}河流圖</b>（色帶＝${RV==='pe'?'近四季 EPS':'每股淨值'} × 歷史 2／20／40／60／80／98% 分位倍數，粗線＝月底收盤價，最右一點＝最新收盤；跟個股頁同一套算法），小卡數字＝目前本益比／淨值比與<b>高於近 N 年幾 % 的月份</b>：<span class="pv"><b class="p4">≥80%</b></span> 歷史偏貴、<span class="pv"><b class="p3">50–80%</b></span> 偏高、<span class="pv"><b class="p2">20–50%</b></span> 中間、<span class="pv"><b class="p1">≤20%</b></span> 歷史偏便宜；紅框＝目前畫的那種分位 ≥80%。「虧損」＝近四季虧損、本益比不適用。<b>循</b>＝循環股（目前只標 2344、6488）：EPS 谷底時本益比會偏高，請以淨值比為主。排序 <b>PE貴</b>／<b>PB貴</b>＝分位高→低，<b>PE便宜</b>／<b>PB便宜</b>＝低→高；篩選可疊加。目前倍數用證交所／櫃買當日本益比、淨值比（每日收盤後更新），歷史月資料：有排程的三檔與個股頁看過的股票直接用，其他每檔即時向 FinMind 查 2 次（免費額度每小時有限，一次最多先讀 ${VLIM} 檔，讀過的會留在手機 24 小時）。⚠ 分位是「跟自己的歷史比」，產業整體重估時高分位不代表該賣；新上市不滿 1 年的不算。`}
// 迷你／完整河流圖：kind 'pe'（EPS × 倍數）或 'pb'（每股淨值 × 倍數）
function drawRiver(cv,v,opt){const dpr=window.devicePixelRatio||1,W=cv.clientWidth,Hh=cv.clientHeight;if(!W||!Hh)return;
  cv.width=Math.round(W*dpr);cv.height=Math.round(Hh*dpr);const g=cv.getContext('2d');g.setTransform(dpr,0,0,dpr,0,0);g.clearRect(0,0,W,Hh);
  const mini=!!opt.mini,kind=opt.kind||'pe',col=kind==='pe'?2:3,ms=kind==='pe'?v.pem:v.pbm,cols=['--b1','--b2','--b3','--b4','--b5'].map(css),mu=css('--muted'),ln=css('--grid'),pc=css('--price');
  let rr=v.riv.filter(r=>r[col]!=null&&r[col]>0);if(mini)rr=rr.slice(-36);const m=rr.length;
  if(m<3){g.fillStyle=mu;g.font='600 10px '+css('--f-body');g.textAlign='center';g.textBaseline='middle';g.fillText(kind==='pe'?'近四季虧損・無本益比':'無資料',W/2,Hh/2);return}
  const padL=0,padR=mini?0:40,top=mini?2:6,bot=mini?2:14;
  let lo=Infinity,hi=-Infinity;rr.forEach(r=>{lo=Math.min(lo,r[col]*ms[0],r[1]);hi=Math.max(hi,r[col]*ms[ms.length-1],r[1])});
  if(!(hi>lo)){hi=lo*1.1||1;lo=0}lo=Math.max(0,lo*0.97);hi*=1.02;
  const X=j=>padL+(W-padL-padR)*(m===1?0:j/(m-1)),Y=p=>top+(hi-p)/(hi-lo)*(Hh-top-bot);
  for(let i=1;i<ms.length;i++){g.fillStyle=cols[i-1];g.beginPath();rr.forEach((r,j)=>{const y=Y(r[col]*ms[i]);j?g.lineTo(X(j),y):g.moveTo(X(j),y)});for(let j=m-1;j>=0;j--)g.lineTo(X(j),Y(rr[j][col]*ms[i-1]));g.closePath();g.fill()}
  g.strokeStyle=ln;g.lineWidth=1;if(!mini){g.font='10px '+css('--f-num');g.textBaseline='middle';g.fillStyle=mu;g.textAlign='left';[0,.25,.5,.75,1].forEach(f=>{const p=lo+(hi-lo)*(1-f),y=Y(p);g.beginPath();g.moveTo(padL,y);g.lineTo(W-padR,y);g.stroke();g.fillText(pxFmt(p),W-padR+4,y)})}
  g.strokeStyle=pc;g.lineWidth=mini?1.6:2.2;g.lineJoin='round';g.beginPath();rr.forEach((r,j)=>{j?g.lineTo(X(j),Y(r[1])):g.moveTo(X(j),Y(r[1]))});g.stroke();
  {const r=rr[m-1],y=Y(r[1]);g.fillStyle=pc;g.beginPath();g.arc(X(m-1),y,mini?2:3,0,Math.PI*2);g.fill();if(!mini){g.fillRect(W-padR+1,y-7,padR-2,14);g.fillStyle=css('--card');g.textAlign='left';g.font='600 10px '+css('--f-num');g.fillText(pxFmt(r[1]),W-padR+4,y)}}
  if(!mini){g.fillStyle=mu;g.font='10px '+css('--f-num');g.textAlign='center';g.textBaseline='bottom';let ly='';rr.forEach((r,j)=>{const yy=r[0].slice(2,4);if(yy!==ly){ly=yy;if(j>0)g.fillText(yy+'年',X(j),Hh-1)}})}}
function fillSheetV(){const r=SHR[openI];if(!r)return closeSheet();const v=VAL[r.c],S=SUM&&SUM.d[r.c];
  const line=(lab,x,p,ms)=>x==null?`<div class="sh-t"><b>${lab}</b>：${lab==='本益比'?'近四季虧損，本益比不適用':'—'}</div>`:`<div class="sh-t"><b>${lab}</b> 目前 <b>${x} 倍</b>，位在 <span class="pill">${vBand(ms,x)}</span> 帶，高於近 ${v.yrs} 年 <b class="${p>=80?'up':p<=20?'dn':''}">${p==null?'—':p+'%'}</b> 的月份</div>`;
  $('sh').innerHTML=`<div class="sh-h"><b>${esc(r.n)}</b><span class="cd">${esc(r.c)}</span>${v&&v.cyc?'<span class="ntag" style="background:var(--warm)">循環股</span>':''}<span class="px ${cls(r.chg)}">${pxFmt(v?v.px:r.px)}</span><span class="chg ${cls(r.chg)}">${pct(r.chg,2)}</span><button class="x" id="shX" aria-label="關閉">×</button></div>
    ${v?`${line('本益比',v.pe,v.pePct,v.pem)}<canvas class="sh-cv rv" id="shPe"></canvas><div class="leg" style="margin-bottom:6px"><span>色帶＝近四季 EPS × ${v.pem.join('／')} 倍</span></div>
    ${line('淨值比',v.pb,v.pbPct,v.pbm)}<canvas class="sh-cv rv" id="shPb"></canvas><div class="leg"><span>色帶＝每股淨值 × ${v.pbm.join('／')} 倍</span>${S&&S[4]!=null?`<span>殖利率 ${S[4]}%</span>`:''}${S&&S[5]!=null?`<span>營收年增 ${S[5]}%</span>`:''}</div>
    ${v.cyc?'<div class="sh-t" style="color:var(--muted)">循環股：EPS 高峰時本益比會偏低、谷底時偏高，請以淨值比河流圖為主</div>':''}<div class="sh-t" style="color:var(--muted);font-size:11px">資料：${esc(v.src)}・月底收盤 ${esc(v.riv[v.riv.length-1][0])}${S?'・目前倍數＝證交所／櫃買 '+esc(String(SUM.pxAsof||''))：''}</div>`
    :`<div class="empty">${VCUR[r.c]==null&&VAL[r.c]===null?'讀不到這檔的估值歷史':'估值資料讀取中…'}</div>`}
    <div class="sh-seg"><a href="index.html#${esc(r.c)}">財報・估值 →</a></div>
    <div class="sh-nav"><button id="shPrev" ${openI<=0?'disabled style="visibility:hidden"':''}>‹ ${openI>0?esc(SHR[openI-1].n):''}</button><span>${openI+1}／${SHR.length}</span><button id="shNext" ${openI>=SHR.length-1?'disabled style="visibility:hidden"':''}>${openI<SHR.length-1?esc(SHR[openI+1].n):''} ›</button></div>`;
  if(v){drawRiver($('shPe'),v,{kind:'pe'});drawRiver($('shPb'),v,{kind:'pb'})}
  $('shX').onclick=closeSheet;$('shPrev').onclick=()=>{openI--;fillSheet()};$('shNext').onclick=()=>{openI++;fillSheet()};
}
'''
rep('''// ---- 放大卡 ----
let SHR=[];''', VAL_JS + '''// ---- 放大卡 ----
let SHR=[];''')
# 分享給 liveRefresh 的重繪：估值模式下 render() 會走 renderV，OK。
# 頁尾／標題
rep('<title>產業 K 線掃描</title>', '<title>產業 K 線／估值掃描（beta）</title>')
rep('<span class="t">K線掃描</span>', '<span class="t">掃描<small>beta</small></span>')

# 排序鍵在估值模式下 `${S?...：''}` 有個全形冒號錯字保護
s = s.replace("+esc(String(SUM.pxAsof||''))：''}", "+esc(String(SUM.pxAsof||'')):''}")
open(dst, 'w', encoding='utf-8').write(s)
print('ok', len(s))
