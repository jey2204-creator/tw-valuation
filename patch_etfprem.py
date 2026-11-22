#!/usr/bin/env python3
"""2026-11-22 17:42 📦 ETF 折溢價（世杰說「🥈 折溢價 做給我看」）。
資料：data/etfnav.json（fetch_etfnav.py，證交所 ETF 盤中預估淨值 all_etf.txt；etfnav.yml 每天跟在「更新股票資料」後面跑）
      d＝{代號:[市價, 預估淨值, 折溢價%, 前日淨值, 時間]}；載入後併到 ETFJ.px[c][10]＝折溢價%。
主題頁：
  收盤欄下方第二行「溢0.18%」「折0.27%」，|折溢價| ≥1% 橘色粗體；
  「收盤」標題連點：日▼→日▲→溢▼→溢▲→名單順序；
  說明列「折溢價中位 −0.2%」＋「⚠️ 溢價 ≥1%：…」（有才顯示），「折溢價本站還沒有」那句換掉；頁尾說明。
用法：python3 patch_etfprem.py       → beta_etfp.html（另一個 session 同時在用 beta.html 做主題熱力圖，所以用獨立檔名）
      python3 patch_etfprem.py prod  → index.html
頁尾版本用正規式換成 v1122p（不管目前是 v1122h 或熱力圖的 v1122i），只能跑一次（其餘錨點都要剛好出現一次）。
"""
import re, sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'

PS = "const premS=v=>v==null?'':`${v>0?'溢':v<0?'折':'平'}${fmt(Math.abs(v),2)}%`;"

E = [
    ("let ETS='',ETC='a',EXD=null;", "let ETS='',ETC='a',EXD=null,NAVJ=null;" + PS),
    ("  try{const r=await fetch('data/exdiv.json?t='+Math.floor(Date.now()/3e5));if(r.ok)EXD=await r.json()}catch(e){}\n",
     "  try{const r=await fetch('data/exdiv.json?t='+Math.floor(Date.now()/3e5));if(r.ok)EXD=await r.json()}catch(e){}\n"
     "  try{const r=await fetch('data/etfnav.json?t='+Math.floor(Date.now()/3e5));if(r.ok){NAVJ=await r.json();if(ETFJ&&ETFJ.px&&NAVJ.d)Object.entries(ETFJ.px).forEach(([c,p])=>{const v=NAVJ.d[c];p[10]=v?v[2]:null})}}catch(e){}   // 2026-11-22：折溢價併進 px[10]\n"),
    ("col={px:0,d:1,w:2,m:3,v:6,y:8};", "col={px:0,d:1,w:2,m:3,v:6,y:8,p:10};"),
    ("${th('d','收盤')}", "${k==='p'?`<th data-ek=\"d\" class=\"on\">溢${+d>0?' ▲':' ▼'}</th>`:th('d','收盤')}"),
    ("ETS=!nk?'':nk==='w'?",
     "ETS=!nk?'':nk==='d'?(ETS==='d:-1'?'d:1':ETS==='d:1'?'p:-1':ETS==='p:-1'?'p:1':ETS==='p:1'?'':'d:-1'):nk==='w'?"),
    ("<span class=\"sub ${sign(dd)}\">${pct(dd,2)}</span></td>",
     "<span class=\"sub ${sign(dd)}\">${pct(dd,2)}</span>${(()=>{const p=etfPx(c,10);if(p==null)return '';const n=NAVJ&&NAVJ.d&&NAVJ.d[c],hi=Math.abs(p)>=1;"
     "return `<span class=\"sub\" style=\"color:${hi?'var(--warm)':'var(--muted)'}${hi?';font-weight:700':''}\" title=\"市價 ${n?n[0]:''} ÷ 預估淨值 ${n?n[1]:''} − 1${n&&n[4]?'・'+n[4]:''}\">${premS(p)}</span>`})()}</td>"),
    ("<b>折溢價本站還沒有</b>：買高股息 ETF 前先看投信官網或券商 App 的折溢價，溢價買進等於多付錢。",
     "${(()=>{const P=ids.map(c=>[c,etfPx(c,10)]).filter(x=>x[1]!=null);if(!P.length)return '<b>折溢價資料還沒產生</b>：買 ETF 前先看投信官網或券商 App 的折溢價，溢價買進等於多付錢。';"
     "const md=median(P.map(x=>x[1])),H=P.filter(x=>x[1]>=1).sort((a,b)=>b[1]-a[1]),a=NAVJ&&NAVJ.asof||'';"
     "return `<b>折溢價</b> (${a?+a.slice(4,6)+'/'+ +a.slice(6)+' ':''}收盤 ÷ 預估淨值) 中位 <strong>${premS(md)}</strong>${H.length?`・<b style=\"color:var(--warm)\">⚠️ 溢價 ≥1%：${H.map(([c,v])=>c+' '+premS(v)).join('、')}</b> (現在買等於多付這麼多)`:'・目前沒有溢價 ≥1% 的'}。`})()}"),
    ("收盤下方＝日漲跌；",
     "收盤下方＝日漲跌，再下面「溢0.18%」「折0.27%」＝<b>折溢價</b>＝收盤 ÷ 預估淨值 − 1 (證交所「ETF 盤中預估淨值」彙總，收盤後的值；|折溢價| ≥1% 標橘色粗體)，溢價＝市價比淨值貴、買進等於多付，折價＝比淨值便宜 (但常是因為海外市場還沒開、或資金在流出)；國外 ETF 的預估淨值是用前一晚海外收盤＋匯率估的，誤差較大；「收盤」標題連點：日▼→日▲→溢▼→溢▲→名單順序；"),
]

s = open('index.html', encoding='utf-8').read()
for a, b in E:
    assert s.count(a) == 1, (s.count(a), a[:60])
    s = s.replace(a, b)
s, nv = re.subn(r'<span style="opacity:\.5">v1122[a-z]</span>', '<span style="opacity:.5">v1122p</span>', s)
assert nv == 1, nv
if not prod:
    s = s.replace('<title>', '<title>[beta] ', 1)
dst = 'index.html' if prod else 'beta_etfp.html'
open(dst, 'w', encoding='utf-8').write(s)
print('ok', dst)
