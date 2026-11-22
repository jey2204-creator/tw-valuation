#!/usr/bin/env python3
"""2026-11-22 17:09 📦 ETF 除息提醒（世杰說「除息提醒 做給我看」）。
資料：
  已公告＝data/exdiv.json（fetch_exdiv.py：證交所 TWT48U、櫃買 OpenAPI 除權除息預告；exdiv.yml 每天跟在「更新股票資料」後面跑）
  預估  ＝data/etf.json 的 nx＝{代號:[預估除息日, 上次每單位配息]}（過去除息日＋1 年，今年已除過的不算）
主題頁：
  說明列多一行「🔔 除息提醒 (30 天內)」：已公告的粗體＋🔔、預估的「約」；附上次配息與占收盤%，依日期排序，跟著分類切換。
  週欄下方：已公告且 21 天內＝橘色「🔔12/16」，預估 31 天內＝「約12/16」（取代原本的「息MM/DD」過去除息標）。
用法：python3 patch_etfex.py       → beta.html
      python3 patch_etfex.py prod  → index.html
只能對 index v1122g 跑一次。
"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'

HELP = ("let ETS='',ETC='a',EXD=null;"
        "const tdYmd=()=>new Date(Date.now()+8*36e5).toISOString().slice(0,10).replace(/-/g,'');"
        "const ymdD=s=>Date.UTC(+s.slice(0,4),+s.slice(4,6)-1,+s.slice(6));"
        "const etfUp=c=>{const t=tdYmd(),e=EXD&&EXD.ev&&(EXD.ev[c]||[]).find(x=>x[0]>=t);"
        "if(e)return {d:e[0],cash:e[1],conf:1,dd:Math.round((ymdD(e[0])-ymdD(t))/864e5)};"
        "const n=ETFJ&&ETFJ.nx&&ETFJ.nx[c];if(n&&n[0]>=t)return {d:n[0],cash:n[1],conf:0,dd:Math.round((ymdD(n[0])-ymdD(t))/864e5)};return null};"
        "const etfUpOn=u=>!!u&&u.dd<=30;")

E = [
    ("let ETS='',ETC='a';", HELP),
    ("  try{const r=await fetch('data/etf.json?t='+Math.floor(Date.now()/3e5));if(r.ok)ETFJ=await r.json()}catch(e){}\n",
     "  try{const r=await fetch('data/etf.json?t='+Math.floor(Date.now()/3e5));if(r.ok)ETFJ=await r.json()}catch(e){}\n"
     "  try{const r=await fetch('data/exdiv.json?t='+Math.floor(Date.now()/3e5));if(r.ok)EXD=await r.json()}catch(e){}\n"),
    # 週欄：即將除息標優先，取代過去除息標
    ("${(()=>{const L=(ETFJ.div&&ETFJ.div[c])||[],x=L[L.length-1];if(!x)return '';",
     "${(()=>{const u=etfUp(c);if(!etfUpOn(u))return '';const md=`${+u.d.slice(4,6)}/${+u.d.slice(6)}`;"
     "return `<span class=\"sub\" style=\"color:var(--warm)${u.conf?';font-weight:700':''}\" title=\"${u.conf?'已公告除息':'預估除息 (去年同期＋1 年)'} ${md}${u.cash?`，${u.conf?'':'上次'}每單位 ${u.cash} 元`:''}\">${u.conf?'🔔':'約'}${md}</span>`})()}"
     "${(()=>{if(etfUpOn(etfUp(c)))return '';const L=(ETFJ.div&&ETFJ.div[c])||[],x=L[L.length-1];if(!x)return '';"),
    # 說明列：除息提醒一行
    ("溢價買進等於多付錢。點一列看 K 線 (掃描頁)。",
     "溢價買進等於多付錢。點一列看 K 線 (掃描頁)。${(()=>{const U=ids.map(c=>[c,etfUp(c)]).filter(([c,u])=>u&&u.dd<=30).sort((a,b)=>a[1].d<b[1].d?-1:1);if(!U.length)return '';"
     "return '<br>🔔 <b>30 天內除息</b>：'+U.map(([c,u])=>{const p=etfPx(c,0),pc=u.cash&&p?`${u.conf?'':'~'}${fmt(u.cash/p*100,1)}%`:'';"
     "return `${u.conf?'<b>':''}${c} ${u.conf?'🔔':'約'}${+u.d.slice(4,6)}/${+u.d.slice(6)}${pc?' '+pc:''}${u.conf?'</b>':''}`}).join('、')+' (<b>🔔＝已公告</b>、約＝推估；%＝配息占收盤)'})()}"),
    ("再下面「息11/18」＝近 20 個交易日內的除息日 (點住可看配息占比)",
     "再下面「息11/18」＝近 20 個交易日內的除息日 (點住可看配息占比)；<b>除息提醒</b>：說明列「🔔 30 天內除息」與週欄下方橘色粗體「🔔12/16」＝已公告、30 天內除息 (證交所/櫃買除權除息預告表，每個交易日更新，通常只公告到 2～6 週後)，橘色「約12/16」＝還沒公告、依去年同一期 (過去除息日＋1 年) 推估 30 天內除息，「~0.6%」是用上次配息估的、實際以投信公告為準；除息前一個交易日 (最後買進日) 收盤前買進才領得到，除息當天股價會扣掉配息；有提醒時會取代「息MM/DD」"),
    ('<span style="opacity:.5">v1122g</span>', '<span style="opacity:.5">v1122h</span>'),
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
