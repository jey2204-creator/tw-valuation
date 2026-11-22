#!/usr/bin/env python3
"""2026-11-22 主題「📦 ETF」（首頁產業主題表排在 0050成份股前面＋掃描頁同名名單）。
世杰選方案 ②：固定名單 13 檔（市值／高息／科技／債券），備註「類別｜說明」。
資料：data/etf.json（fetch_rank.py 的 build_etf，rank.yml 每個交易日跟在「更新股票資料」後面跑；不另外發請求）。
     名單改 fetch_rank.py 的 ETF_THEME。K 線：rank.json 的 xk 一律包含這 13 檔。
用法：python3 patch_etf.py       → beta.html＋beta_scan_etft.html
      python3 patch_etf.py prod  → index.html＋scan.html
只能對舊版（index v1121a、scan v1121a）跑一次。
"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'


def patch(src, dst, edits, beta_extra=()):
    s = open(src, encoding='utf-8').read()
    for old, new in list(edits) + ([] if prod else list(beta_extra)):
        assert s.count(old) == 1, (src, s.count(old), old[:80])
        s = s.replace(old, new)
    if not prod:
        s = s.replace('<title>', '<title>[beta] ', 1)
    open(dst, 'w', encoding='utf-8').write(s)
    print('ok', dst)


ETFT = r"""// ---- 📦 ETF 主題（2026-11-22）：data/etf.json 由 fetch_rank.py 每個交易日盤後算；固定名單、已依類別＋近 20 日均成交值排好，備註＝類別｜說明
function etfTheme(){if(!ETFJ||!(ETFJ.stocks||[]).length)return [];const a=ETFJ.asof||'',md=a?`${+a.slice(4,6)}/${+a.slice(6)}`:'';
  return [{id:'etf',name:`📦 ETF${md?` (${md})`:''}`,auto:true,etf:true,desc:'常見台股 ETF 固定名單：市值型、高股息、科技/半導體、債券',stocks:ETFJ.stocks.map(([c,n])=>[c,n])}]}
const etfPx=(c,k)=>{const p=ETFJ&&ETFJ.px&&ETFJ.px[c];return p?p[k]:null};   // [收, 日%, 週%, 月%, 季%, 量比, 成交值億, 20日均值億]
function etfStat(t){const ids=t.stocks.map(x=>x[0]);return {t,n:ids.length,y:null,pe:null,ey:null,pg:null,mm:median(ids.map(i=>etfPx(i,3))),nf:0,a3:null,a2:null}}
let ETS='';
function etfPage(){const t=THEMES.find(x=>x.id==='etf');if(!t||!ETFJ)return;const a=ETFJ.asof,ids=t.stocks.map(x=>x[0]),g=k=>median(ids.map(i=>etfPx(i,k)));
  const s=(v,d=1)=>`<strong class="${sign(v)}">${pct(v,d)}</strong>`;
  $('tSum').innerHTML=`<span class="asof">📦 收盤日 ${a.slice(0,4)}/${a.slice(4,6)}/${a.slice(6)}・固定 ${ids.length} 檔・盤後更新</span><br>${ids.length} 檔中位數：日 ${s(g(1),2)}・週 ${s(g(2))}・月 ${s(g(3))}・季 ${s(g(4))}<br>ETF 沒有 EPS、本益比、AI 成分，所以首頁主題表只有「月漲」有數字。漲跌<b>未還原配息</b>：跨除息日會偏低 (高股息季配、月配最明顯)。<b>折溢價、殖利率本站還沒有</b>：買高股息 ETF 前先看投信官網或券商 App 的折溢價，溢價買進等於多付錢。點一列看 K 線 (掃描頁)。`;
  $('tUS').innerHTML='';
  const el=$('tTbl'),[k,d]=ETS.split(':'),col={px:0,d:1,w:2,m:3,v:6};let rows=t.stocks.slice();
  if(k)rows.sort((x,y)=>{const p=etfPx(x[0],col[k]),q=etfPx(y[0],col[k]);return p==null?1:q==null?-1:(p-q)*(+d)});
  const th=(key,lb)=>{const on=!!key&&k===key;return `<th data-ek="${key}" class="${on?'on':''}">${lb}${on?(+d>0?' ▲':' ▼'):''}</th>`};
  const nm=c=>(ETFJ.nm&&ETFJ.nm[c]||[c])[0];
  el.classList.add('mo');
  el.innerHTML=`<thead><tr>${th('','ETF')}${th('d','收盤')}${th('w','週')}${th('m','月')}${th('v','成交值')}</tr></thead><tbody>`+rows.map(([c,role])=>{
    const cl=etfPx(c,0),dd=etfPx(c,1),w=etfPx(c,2),m=etfPx(c,3),q=etfPx(c,4),vr=etfPx(c,5),v=etfPx(c,6);
    return `<tr data-id="${c}"><td><span class="nm">${esc(nm(c))}</span><span class="cd">${c}</span>${role?`<div class="role">${esc(role)}</div>`:''}</td>
      <td>${fmt(cl,cl!=null&&cl<100?2:1)}<span class="sub ${sign(dd)}">${pct(dd,2)}</span></td>
      <td class="${sign(w)}">${pct(w)}</td><td class="${sign(m)}">${pct(m)}<span class="sub ${sign(q)}">季${pct(q)}</span></td>
      <td>${v==null?'—':fmt(v,v>=100?0:1)+'億'}<span class="sub" style="${vr!=null&&vr>=1.5?'color:var(--warm)':''}">量比${fmt(vr,2)}</span></td></tr>`}).join('')+'</tbody>';
  el.onclick=e=>{const h=e.target.closest('th[data-ek]');if(h){const nk=h.dataset.ek;ETS=!nk?'':k!==nk?nk+':-1':d==='-1'?nk+':1':'';etfPage();return}
    if(e.target.closest('tr[data-id]'))location.href='scan.html#etf'};
  $('tFoot').innerHTML=`名單順序＝類別 (市值→高息→科技→債券)，同類別內依近 20 個交易日平均成交值由大到小；本站沒有 ETF 規模 (受益權單位×淨值) 資料，所以不是依規模。點欄位標題排序 (再點一次反向、第三次回名單順序)；「ETF」標題＝回名單順序。<br>收盤下方＝日漲跌；週/月/季＝對比 5/20/60 個交易日前收盤，<b>未還原配息</b>；成交值＝收盤×成交張數的估算，量比＝今日張數 ÷ 前 5 日均張，≥1.5 標橘色。資料：證交所、櫃買中心每日收盤行情 (跟掃描頁成交值排行同一份)。名單要增減告訴 Claude。`;
}
"""

index_edits = [
    ("const AUTO_IDS=['e50','hp50',", "const AUTO_IDS=['etf','e50','hp50',"),
    ("let E50=null,HP50=null;const lowT=id=>id===FAVT||id==='e50'||id==='hp50';",
     "let E50=null,HP50=null,ETFJ=null;const lowT=id=>id===FAVT||id==='e50'||id==='hp50'||id==='etf';"),
    ("function autoThemes(){\n  if(!TOP||!TOP.lists)return [...e50Theme(),...hp50Theme()];",
     ETFT + "function autoThemes(){\n  if(!TOP||!TOP.lists)return [...etfTheme(),...e50Theme(),...hp50Theme()];"),
    ("  return [...e50Theme(),...hp50Theme(),...mk('itop',", "  return [...etfTheme(),...e50Theme(),...hp50Theme(),...mk('itop',"),
    ("  try{const r=await fetch('data/e50.json?t='+Math.floor(Date.now()/3e5));if(r.ok)E50=await r.json()}catch(e){}\n",
     "  try{const r=await fetch('data/e50.json?t='+Math.floor(Date.now()/3e5));if(r.ok)E50=await r.json()}catch(e){}\n"
     "  try{const r=await fetch('data/etf.json?t='+Math.floor(Date.now()/3e5));if(r.ok)ETFJ=await r.json()}catch(e){}\n"),
    ("const nameOf=id=>{const it=LIST.find(s=>s[0]===id);return it?it[1].replace(/\\*$/,''):id};",
     "const nameOf=id=>{const it=LIST.find(s=>s[0]===id);return it?it[1].replace(/\\*$/,''):(ETFJ&&ETFJ.nm&&ETFJ.nm[id]?ETFJ.nm[id][0]:id)};"),
    ("function themeStat(t){const ids=", "function themeStat(t){if(t.etf)return etfStat(t);const ids="),
    ("const k=ids.indexOf('e50');ids.splice(k<0?0:k+1,0,'hp50')}   // 2026-11-21：高價股前50 接在 0050 後面\n",
     "const k=ids.indexOf('e50');ids.splice(k<0?0:k+1,0,'hp50')}   // 2026-11-21：高價股前50 接在 0050 後面\n"
     "  if(c.order.length&&!c.order.includes('etf')&&ids.includes('etf')){ids.splice(ids.indexOf('etf'),1);const k=ids.indexOf('e50');ids.splice(k<0?0:k,0,'etf')}   // 2026-11-22：📦 ETF 排在 0050成份股前面\n"),
    ("t.favt?'・跟著 ⭐ 自選':t.e50?'・換股時自動更新'", "t.favt?'・跟著 ⭐ 自選':t.etf?'・固定名單・每日更新報價':t.e50?'・換股時自動更新'"),
    ("// ---- 主題頁上下主題切換（‹ N/M ▾ ›）",
     "{const _st=showTheme;showTheme=function(tid){_st(tid);if(tid==='etf')etfPage();else $('tTbl').classList.toggle('mo',MODE==='m')}}   // 2026-11-22：📦 ETF 主題頁用自己的表\n// ---- 主題頁上下主題切換（‹ N/M ▾ ›）"),
    ('<span style="opacity:.5">v1121a</span>', '<span style="opacity:.5">v1122a</span>'),
]

scan_edits = [
    ("const AUTO_IDS=['e50','hp50',", "const AUTO_IDS=['etf','e50','hp50',"),
    ("  const [HP50,E50,AJ0,L,T,TOP,NT0,PV]=await Promise.all([fetch('data/hp50.json?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null),",
     "  const [ETFJ,HP50,E50,AJ0,L,T,TOP,NT0,PV]=await Promise.all([fetch('data/etf.json?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null),fetch('data/hp50.json?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null),"),
    ("  if(HP50&&(HP50.stocks||[]).length){",
     "  // 📦 ETF（2026-11-22，與首頁同一份 data/etf.json）：排在 0050成份股前面；K 線靠 rank.json 的 xk（一律包含這幾檔）\n"
     "  if(ETFJ&&(ETFJ.stocks||[]).length){const a=ETFJ.asof||'';Object.entries(ETFJ.nm||{}).forEach(([c,[n,m]])=>{NAME[c]=NAME[c]||n;MKT[c]=MKT[c]||m});"
     "T.themes=[{id:'etf',name:`📦 ETF${a?` (${+a.slice(4,6)}/${+a.slice(6)})`:''}`,stocks:ETFJ.stocks.map(x=>[x[0],''])},...(T.themes||[])]}\n"
     "  if(HP50&&(HP50.stocks||[]).length){"),
    ("const A=THEMES.filter(t=>t.id==='_fav'||t.id==='e50'||", "const A=THEMES.filter(t=>t.id==='_fav'||t.id==='etf'||t.id==='e50'||"),
    ("const isRk=isN||(sel.kind==='t'&&(sel.id==='e50'||sel.id==='hp50'));",
     "const isRk=isN||(sel.kind==='t'&&(sel.id==='e50'||sel.id==='hp50'||sel.id==='etf'));   // 2026-11-22：📦 ETF 也預設榜序（＝首頁名單順序）"),
    ('<span style="opacity:.5">v1121a</span>', '<span style="opacity:.5">v1122a</span>'),
]

# beta 互連：首頁 beta 的 ETF「掃描」鈕／點列 → 掃描 beta；掃描 beta 的「‹ 掃描」回首頁 beta
I_BETA = [("$('tScan').href='scan.html#'+encodeURIComponent(t.id);", "$('tScan').href=(t.id==='etf'?'beta_scan_etft.html?v=1#':'scan.html#')+encodeURIComponent(t.id);"),
          ("location.href='scan.html#etf'", "location.href='beta_scan_etft.html?v=1#etf'")]
S_BETA = [("?'index.html#t/'+encodeURIComponent(sel.id):'index.html';", "?(sel.id==='etf'?'beta.html?v=18#t/':'index.html#t/')+encodeURIComponent(sel.id):'index.html';")]
patch('index.html', 'index.html' if prod else 'beta.html', index_edits, I_BETA)
patch('scan.html', 'scan.html' if prod else 'beta_scan_etft.html', scan_edits, S_BETA)
