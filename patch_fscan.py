#!/usr/bin/env python3
"""2026-11-15 掃描頁加「🔥 主力訊號」名單（方案 B）＋K 棒標上榜日。
- 名單鈕「🔥 主力訊號」（★ 自選後面第一顆）；預設範圍＝產業主題＋自選（跟首頁同一份），篩選列最後「全市場」鈕可切全市場
- 日期選單（data/fire_hist.json 的每個交易日）、榜序＝🆕 新進在前 → 連續天數少→多
- 小卡標 🔥新／🔥N（連 N 天）、橘底 ⚠＝這個進場時機過去抱 10 日輸大盤 ≥2 點、短＝當天列注意股（定義同首頁 patch_fwarn）
- K 棒底下紅點＝那天有 🔥，每段連續上榜的第 1 天畫大點；黃色注意日的點往上移一列
- 放大卡：標題標籤、統計說明、舊日期多「上榜後 x%」、圖例
用法：python3 patch_fscan.py            → beta_scan_fire.html
      python3 patch_fscan.py prod       → scan.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
src='scan.html';dst='scan.html' if prod else 'beta_scan_fire.html'
s=open(src,encoding='utf-8').read()
def rep(old,new,n=1):
    global s;assert s.count(old)==n,(s.count(old),old[:90]);s=s.replace(old,new)

# ---- CSS ----
rep('''.tg.ny{background:#b88600}''','''.tg.ff{background:var(--up)}.tg.fw{background:#e8590c}.km-h .tg+.tg{margin-left:2px}
.sb button#fAll[aria-pressed=true]{background:var(--up);border-color:var(--up);color:#fff}
.cnt a{color:var(--accent);font-weight:700;text-decoration:none}
.tg.ny{background:#b88600}''')

# ---- 控制列第 3 行（篩選列）最後：全市場切換 ----
rep('''<button class="f" data-f="vr12" title="量比 ≥1.2">量≥1.2</button>''',
    '''<button class="f" data-f="vr12" title="量比 ≥1.2">量≥1.2</button><button id="fAll" hidden aria-pressed="false" title="🔥 名單範圍：預設＝產業主題＋自選（跟首頁同一份）；按下＝全市場">全市場</button>''')

# ---- 狀態 ----
rep('''let MISS=[],RANKED=false,''','''let FH=null,FS=null,FDAYS=[],FALL=false,FPOOL=new Set(),FIRE=false,PAST=false;
let MISS=[],RANKED=false,''')

# ---- 載入 fire_hist / fire_stats ----
rep('''  valInit();
  const [AJ0,''','''  valInit();
  const FHP=Promise.all(['data/fire_hist.json','data/fire_stats.json'].map(u=>fetch(u+'?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null)));
  const [AJ0,''')
rep('''  THEMES=themesAll(T.themes||[]);''','''  THEMES=themesAll(T.themes||[]);
  // 2026-11-15：🔥 主力訊號名單（data/fire_hist.json，全市場每天的 🔥；預設只取產業主題＋自選，跟首頁同一份）
  {const [fj,fs]=await FHP;if(fj&&fj.d&&fj.days&&fj.days.length){FH=fj;FS=fs&&fs.s?fs:null;FDAYS=fj.days.slice().reverse();try{FALL=localStorage.getItem('scanFireAll')==='1'}catch(e){}
    FPOOL=new Set(THEMES.flatMap(t=>t.stocks.map(x=>x[0])));
    THEMES.splice(THEMES[0]&&THEMES[0].id==='_fav'?1:0,0,{id:'fire',name:`🔥 主力訊號（${md(FDAYS[0])}）`,stocks:fireList(FDAYS[0]).map(x=>[x.c,''])})}}''')

# ---- 按鈕事件 ----
rep('''  $('sortBar').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;''',
    '''  $('sortBar').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
    if(b.id==='fAll'){FALL=!FALL;try{localStorage.setItem('scanFireAll',FALL?'1':'0')}catch(e){}fireSync();pick(cur);return}''')

# ---- pick() ----
rep('''  if(!(sel.kind==='t'&&(NSET.has(sel.id)||(sel.id in TKEY))))NDATE='';''',
    '''  if(!(sel.kind==='t'&&(NSET.has(sel.id)||(sel.id in TKEY)||sel.id==='fire')))NDATE='';''')
rep('''sel.kind==='t'&&sel.id!=='_fav'?'index.html#t/'+''','''sel.kind==='t'&&sel.id!=='_fav'&&sel.id!=='fire'?'index.html#t/'+''')
rep('''  const isT=sel.kind==='t'&&(sel.id in TKEY)&&!!THIST,DAYS=isT?TDAYS:NDAYS,D0=(!isT&&NXT?NOTICE.asof:DAYS[0])||'',isN=sel.kind==='t'&&(NSET.has(sel.id)||isT);''',
    '''  const isF=sel.kind==='t'&&sel.id==='fire'&&!!FH;$('fAll').hidden=!isF;$('fAll').setAttribute('aria-pressed',String(FALL));
  const isT=sel.kind==='t'&&(sel.id in TKEY)&&!!THIST,DAYS=isF?FDAYS:isT?TDAYS:NDAYS,D0=(isF?FDAYS[0]:!isT&&NXT?NOTICE.asof:DAYS[0])||'',isN=sel.kind==='t'&&(NSET.has(sel.id)||isT||isF);''')
rep('''  if(isN){if(!NDATE||!(isT?THIST:HIST)[NDATE])NDATE=D0;
    $('ndSel').innerHTML=DAYS.map(''','''  if(isN){if(!NDATE||!(isF?FH.d:isT?THIST:HIST)[NDATE])NDATE=D0;
    $('ndSel').innerHTML=isF?DAYS.map(d=>`<option value="${d}">🔥 ${md(d)}・${fireList(d).length} 檔</option>`).join(''):DAYS.map(''')
rep('''  const past=isN&&NDATE&&D0&&NDATE!==D0;TOPK=isT?TKEY[sel.id]:'';''',
    '''  const past=isN&&NDATE&&D0&&NDATE!==D0;TOPK=isT?TKEY[sel.id]:'';FIRE=isF;PAST=!!past;''')
rep('''  const PL=past?histList(sel.id,NDATE):null;PMAP=past?Object.fromEntries(PL.map(x=>[x.c,x])):null;
  const ids=past?PL.map(x=>x.c):''','''  const PL=past||isF?histList(sel.id,NDATE):null;PMAP=PL?Object.fromEntries(PL.map(x=>[x.c,x])):null;
  const ids=PL?PL.map(x=>x.c):''')
rep('''const name=past?`${NLAB[sel.id]||TLAB[TKEY[sel.id]]}（''','''const name=past?`${isF?'🔥 主力訊號'+(FALL?'・全市場':''):NLAB[sel.id]||TLAB[TKEY[sel.id]]}（''')

# ---- 名單回推 ----
rep('''function histList(id,D){
''','''// ---- 2026-11-15：🔥 主力訊號名單（某一天）；統計警示的定義與首頁 patch_fwarn 相同（隔天收盤買、抱 10 日超額 ≤ −2% 且 ≥50 筆才警示） ----
const FMIN=50,FBAD=-0.02,fsP=(x,d=1)=>(x>0?'+':'')+(x*100).toFixed(d)+'%',fsBk=n=>n>=6?'d6':n>=4?'d45':'d'+n;
function fsC(g,k,h){if(!FS)return null;const s=g==='streak'?FS.s:FS.cuts&&FS.cuts[g]&&FS.cuts[g].s,c=s&&s.e1&&s.e1[k]&&s.e1[k][h];return c&&c.n>=FMIN&&c.ex!=null?c:null}
const fsTxt=(c,h)=>`抱 ${h} 日勝率 ${(c.win*100).toFixed(0)}%、平均 ${fsP(c.avg)}、${c.ex>=0?'贏':'輸'}大盤 ${Math.abs(c.ex*100).toFixed(1)} 點`;
function fireList(D){if(!FH||!FH.d[D])return [];const ds=FH.days,i=ds.indexOf(D),has=(k,c)=>!!(FH.d[ds[k]]&&FH.d[ds[k]][c]);
  const nsrc=NXT&&NXT.asof===D?NXT:NOTICE&&NOTICE.asof===D?NOTICE:null,att=new Set(HIST&&HIST[D]&&HIST[D].att?HIST[D].att:nsrc?(nsrc.att||[]).map(x=>x.c):[]);   // 事件當天公布的注意名單（跟統計同定義）
  const per=FS?`${md(FS.from)}～${md(FS.to)}`:'';
  const nI=(()=>{const c5=fsC('nt','att','5'),c10=fsC('nt','att','10');if(!c5||!c10)return null;const bad=c10.ex<=FBAD,short=!bad&&c5.ex>0.01&&c10.ex<0;return bad||short?{bad,txt:`當天列注意股：過去約 ${c5.n} 筆 ${fsTxt(c5,5)}；但${fsTxt(c10,10)}。${bad?'過去追進去多半吃虧':'短線動能，不宜久抱'}`}:null})();
  return Object.keys(FH.d[D]).filter(c=>/^\\d{4}$/.test(c)&&(FALL||FPOOL.has(c))).map(c=>{let n=1,k=i-1;while(k>=0&&has(k,c)){n++;k--}const plus=k<0;
    const c5=fsC('streak',fsBk(n),'5'),c10=fsC('streak',fsBk(n),'10'),bad=!!(c10&&c10.ex<=FBAD),nt=nI&&att.has(c)?(nI.bad?'w':'s'):'';
    return {c,k:'f',n,plus,bad,nt,m:FH.d[D][c][1],r:`${md(D)} 🔥 ${n===1&&!plus?'🆕 新進（前一個交易日還沒有）':'已連 '+n+(plus?'+':'')+' 個交易日'}`+(c5&&c10?`。📊 這個時機過去 ${c10.n} 筆（${per}，隔天收盤買）：${fsTxt(c5,5)}；${fsTxt(c10,10)}；最差 10% 抱 10 日 ${fsP(c10.p10)}`:'')+(nt?'。'+nI.txt:'')}})
    .sort((a,b)=>a.n-b.n||(b.m??-99)-(a.m??-99))}
function fireSync(){const t=THEMES.find(x=>x.id==='fire');if(!t||!FH)return;t.stocks=fireList(FDAYS[0]).map(x=>[x.c,'']);const sp=document.querySelector('#themes button[data-t=fire] span');if(sp)sp.textContent=` ${t.stocks.length}・${md(FDAYS[0])}`}
function histList(id,D){
  if(id==='fire')return fireList(D);
''')

# ---- build()：每檔的 🔥 上榜日（2＝一段連續上榜的第 1 天、1＝續）＋上榜後% ----
rep('''  return {c,n:NAME[c]||c,bars,nd,dp,''','''  const fd={};if(FIRE&&FH){let pv=false;FH.days.forEach(d=>{const on=!!(FH.d[d]&&FH.d[d][c]);if(on)fd[d]=pv?1:2;pv=on})}
  const fsince=FIRE&&PAST&&NDATE?(b=>b&&b.rc?last.rc/(b.rc*adjF(b.d,last.d))-1:null)(bars.find(x=>String(x.d)===NDATE)):null;
  return {c,n:NAME[c]||c,bars,nd,fd,fsince,dp,''')

# ---- drawK ----
rep('''  const pad=(hi-lo)*0.05;hi+=pad;lo-=pad;''','''  const hasFd=!!(r.fd&&Object.keys(r.fd).length);
  const pad=(hi-lo)*0.05;hi+=pad;lo-=pad*(hasFd?(mini?3.4:2.6):1);   // 🔥 名單：底部多留一點放上榜日的點''')
rep('''  if(NDATE&&PMAP){const j=vis.findIndex(''','''  if(NDATE&&PMAP&&PAST){const j=vis.findIndex(''')
rep('''const y0=top+priceH-(mini?2:4);vis.forEach((x,j)=>{const k=r.nd[x.d];if(!k)return;''',
    '''const y0=top+priceH-(mini?2:4)-(hasFd?(mini?5.5:8.5):0);vis.forEach((x,j)=>{const k=r.nd[x.d];if(!k)return;''')
rep('''  if(axisH){g.fillStyle=mu;g.font='10px '+css('--f-num');g.textAlign='center';g.textBaseline='bottom';let lastM='';''',
    '''  // 2026-11-15：🔥 上榜日＝紅點，每段連續上榜的第 1 天畫大點
  if(hasFd){const y1=top+priceH-(mini?3:4.5);g.fillStyle=up;vis.forEach((x,j)=>{const k=r.fd[x.d];if(!k)return;g.beginPath();g.arc(X(j),y1,k===2?(mini?2.6:4):(mini?1.3:2.2),0,Math.PI*2);g.fill()})}
  if(axisH){g.fillStyle=mu;g.font='10px '+css('--f-num');g.textAlign='center';g.textBaseline='bottom';let lastM='';''')

# ---- 小卡標記 ----
rep('''if(!m)return '';return TLAB[m.k]?''','''if(!m)return '';return m.k==='f'?`<span class="tg ${m.bad?'fw':'ff'}" title="${esc(m.r)}">🔥${m.n===1&&!m.plus?'新':m.n+(m.plus?'+':'')}${m.bad?'⚠':''}</span>${m.nt?`<span class="tg ${m.nt==='w'?'fw':'ny'}" title="當天列注意股">${m.nt==='w'?'⚠注':'短'}</span>`:''}`:TLAB[m.k]?''')

# ---- 統計列 ----
rep('''  $('cnt').innerHTML=all?`<b>${R.length}</b>／${all} 檔''','''  const fz=FIRE&&PMAP?(v=>{const nw=v.filter(x=>x.n===1&&!x.plus).length,bd=v.filter(x=>x.bad).length,nt=v.filter(x=>x.nt).length;return `🔥 <b>🆕 ${nw}</b>・續 ${v.length-nw}${bd?`・<b style="color:#e8590c">⚠ ${bd}</b> 連太多天`:''}${nt?`・<b>${nt}</b> 注意股（短線）`:''}・<a href="fstats.html">統計 ›</a><br>`})(ROWS.map(r=>PMAP[r.c]).filter(Boolean)):'';
  $('cnt').innerHTML=all?fz+`<b>${R.length}</b>／${all} 檔''')

# ---- 放大卡 ----
rep('''<span class="ntag" style="background:${TLAB[nm.k]?TCOL[nm.k]:''','''<span class="ntag" style="background:${nm.k==='f'?(nm.bad?'#e8590c':'var(--up)'):TLAB[nm.k]?TCOL[nm.k]:''')
rep('''">${TLAB[nm.k]?'第 '+nm.rank+' 名・連 '+nm.n+' 天上榜':''','''">${nm.k==='f'?'🔥 '+(nm.n===1&&!nm.plus?'新進':'連'+nm.n+(nm.plus?'+':'')+'天')+(nm.bad?'⚠':'')+(nm.nt?(nm.nt==='w'?'・⚠注意股':'・短線'):''):TLAB[nm.k]?'第 '+nm.rank+' 名・連 '+nm.n+' 天上榜':''')
rep('''<span>${esc(nm.r||'')}</span></div>`:''}<div class="leg">''','''<span>${r.fsince!=null?`<b>上榜後 <span class="${cls(r.fsince)}">${pct(r.fsince)}</span></b>（${md(NDATE)} 收盤→最新）・`:''}${esc(nm.r||'')}</span></div>`:''}<div class="leg">''')
rep('''${r.dp&&r.dp.length?'<span><i style="width:12px;height:9px;background:var(--up);opacity:.18"></i>處置期間</span>':''}${NDATE&&PMAP?''',
    '''${r.fd&&Object.keys(r.fd).length?'<span><i style="width:8px;height:8px;border-radius:50%;background:var(--up)"></i>🔥首日<i style="width:4px;height:4px;border-radius:50%;background:var(--up);margin-left:5px"></i>續</span>':''}${r.dp&&r.dp.length?'<span><i style="width:12px;height:9px;background:var(--up);opacity:.18"></i>處置期間</span>':''}${NDATE&&PMAP&&PAST?''')

# ---- 頁尾說明 ----
rep('''分片資料與估值看板個股頁同一份。`;''','''分片資料與估值看板個股頁同一份。<br><b>🔥 主力訊號</b>名單＝月漲幅 &gt; 0、量比 ≥ 1.5、投信或外資 5 日買超 ≥ 5 日成交量 1%（跟首頁同一份；預設範圍＝產業主題＋自選，篩選列最後「全市場」可切換）。小卡 <b>🔥新</b>＝前一個交易日還沒有、<b>🔥N</b>＝連 N 天；<span style="color:#e8590c"><b>橘底 ⚠</b></span>＝這個進場時機過去抱 10 日輸大盤 2 點以上；<b>短</b>＝當天同時列注意股（過去 5 日有超額、10 日倒輸）。K 棒底下紅點＝那天有 🔥，大點＝每段連續上榜的第 1 天（${FH?md(FH.days[0]):'9/16'} 起才有紀錄，更早的 K 棒沒有點不代表沒訊號）；黃點＝列注意日。榜序＝🆕 新進在前、連續天數少→多。畫面上只有「上榜」的股票，漲不上去掉出名單的不在這裡——勝率請看 <a href="fstats.html">📊 統計頁</a>。 <span style="opacity:.5">v1115f</span>`;''')

if not prod:
    s=s.replace('<title>','<title>[beta] ',1)
open(dst,'w',encoding='utf-8').write(s);print('ok',dst,len(s))
