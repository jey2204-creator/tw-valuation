#!/usr/bin/env python3
"""2026-11-20 掃描頁：① 篩選加「外資連買／連賣 ≥3」② 「空」模式小卡與放大卡加做空資訊（data/short.json，見 fetch_short.py）。
起因：11/20 21:27 世杰說「篩選加外賣≥3、小卡加券源、融券、平盤下可否放空的標記，做給我看」。接續 patch_ls.py（多空切換）。
① 篩選第 5 顆：多＝外買3（外資連買 ≥3 天）、空＝外賣3。第 3 行變 5 顆放不下「≥」→ 投連≥3／投賣≥3 一併改名 投買3／投賣3；量≥1.2 那顆加寬；排行名單的市場鈕「合併 上市 上櫃」改短字「合 市 櫃」。
② 空模式小卡：K 線左上角疊一行（不佔版面高度）「[標籤] 券{融券餘額} 比{券資比}% 回{停券起日＝最後回補日}」。標籤：
   可空（綠）＝可融券且在平盤下可空名單；平✗（灰）＝可融券但平盤以下不能空（不在名單，或前一日跌停）；停券（橘）＝暫停融券賣出／停券期間；
   券滿（橘）＝融券餘額 ≥ 限額 98%；無券（灰）＝不是信用交易股；可券（藍）＝可融券但該市場的平盤下名單沒抓到。
   放大卡多一行：標籤＋說明、融券餘額（增減）、限額使用率、券資比、停券期間、資料日。
   「券源」＝各券商自己的庫存，公開資料查不到；這裡只有「融券限額用了多少」。
用法：python3 patch_sh.py → beta_scan_sh.html；python3 patch_sh.py prod → scan.html。只能對 v1120f 跑一次。
"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
s = open('scan.html', encoding='utf-8').read()
E = [
 # ---------- ① 外資連買／連賣 ≥3 ----------
 ("FL={ma20:false,ma60:false,ts3:false,vr12:false}", "FL={ma20:false,ma60:false,ts3:false,fs3:false,vr12:false}"),
 ('<button class="f" data-f="ts3" title="投信連買 ≥3 天">投連≥3</button>',
  '<button class="f" data-f="ts3" title="投信連買 ≥3 天">投買3</button><button class="f" data-f="fs3" title="外資連買 ≥3 天">外買3</button>'),
 ("['ts3','投連≥3','投賣≥3','投信連買 ≥3 天','投信連賣 ≥3 天']]", "['ts3','投買3','投賣3','投信連買 ≥3 天','投信連賣 ≥3 天'],['fs3','外買3','外賣3','外資連買 ≥3 天','外資連賣 ≥3 天']]"),
 ("&&(!FL.ts3||(S?r.ts<=-3:r.ts>=3))&&", "&&(!FL.ts3||(S?r.ts<=-3:r.ts>=3))&&(!FL.fs3||(S?r.fs<=-3:r.fs>=3))&&"),
 ("投信連賣≥3 <b>${ROWS.filter(r=>r.ts<=-3).length}</b> 檔`:", "投信連賣≥3 <b>${ROWS.filter(r=>r.ts<=-3).length}</b> 檔・外資連賣≥3 <b>${ROWS.filter(r=>r.fs<=-3).length}</b> 檔`:"),
 ("投信連買≥3 <b>${ROWS.filter(r=>r.ts>=3).length}</b> 檔`}・", "投信連買≥3 <b>${ROWS.filter(r=>r.ts>=3).length}</b> 檔・外資連買≥3 <b>${ROWS.filter(r=>r.fs>=3).length}</b> 檔`}・"),
 # ---------- ② 做空資訊 ----------
 ("/* 2026-11-20：多｜空 切換 */\n",
  "/* 2026-11-20：篩選 5 顆；空模式做空資訊 */\n"
  ".sb .f[data-f=vr12]{flex:1.25 1 0}\n"
  ".km-x{position:absolute;left:4px;margin-top:2px;z-index:1;font:600 8.5px var(--f-num);line-height:12px;color:var(--fg);background:color-mix(in srgb,var(--card) 80%,transparent);border-radius:3px;padding-right:2px;white-space:nowrap;pointer-events:none;letter-spacing:-.02em;max-width:calc(100% - 8px);overflow:hidden}\n"
  ".km-x b,.sh-m b.xt{color:#fff;border-radius:3px;padding:0 3px;margin-right:2px;font-weight:700}\n"
  ".xg{background:var(--down)}.xn{background:var(--chip);color:var(--muted)!important}.xw{background:#d9731a}.xm{background:var(--muted)}.xa{background:var(--accent)}\n"
  "/* 2026-11-20：多｜空 切換 */\n"),
 ("let SIDE='l';",
  "let SIDE='l',SHT=null,SHP=null;\n"
  "function shLoad(){if(!SHP)SHP=fetch('data/short.json',{cache:'no-cache'}).then(r=>r.json()).then(j=>{SHT=j;if(sideS())render()}).catch(()=>{SHP=null});return SHP}\n"
  "// 做空資訊：s[代號]＝[融券餘額, 融券限額, 融券增減, 融資餘額, 標記]（F 平盤下可空名單／X 暫停融券賣出／B 暫停借券／L 前一日跌停／N 融資融券表註記停券）\n"
  "function shInfo(c){if(!SHT||!SHT.s)return null;const v=SHT.s[c],hasF=!!(SHT.fd&&SHT.fd[MKT[c]==='上櫃'?'tpex':'twse']),T=new Date(Date.now()+8*3600e3).toISOString().slice(0,10).replace(/-/g,''),rr=SHT.r&&SHT.r[c]&&SHT.r[c][1]>=T?SHT.r[c]:null;\n"
  "  if(!v)return {t:'無券',k:'n',d:'不是信用交易股，不能融券放空',rr};\n"
  "  const m=v[4]||'',u=v[1]?v[0]/v[1]:null,o={v,u,rr,rm:v[3]?v[0]/v[3]:null};\n"
  "  if(/[XN]/.test(m)||(rr&&rr[0]<=T))return {...o,t:'停券',k:'w',d:'暫停融券賣出'};\n"
  "  if(u!=null&&u>=.98)return {...o,t:'券滿',k:'w',d:'融券餘額已達限額'};\n"
  "  if(m.includes('L'))return {...o,t:'平✗',k:'m',d:'前一日跌停，今天平盤以下不能放空'};\n"
  "  if(!hasF)return {...o,t:'可券',k:'a',d:'可融券；平盤下可空名單沒抓到'};\n"
  "  return m.includes('F')?{...o,t:'可空',k:'g',d:'可融券，平盤以下也能放空'}:{...o,t:'平✗',k:'m',d:'可融券，但平盤以下不能放空'}}\n"
  "const shNum=n=>n>=1e4?(n/1e4).toFixed(n>=1e5?0:1)+'萬':String(n);\n"
  "function shTag(r){const i=shInfo(r.c);if(!i)return '';return `<span class=\"km-x\"><b class=\"x${i.k}\">${i.t}</b>${i.v?`券${shNum(i.v[0])}${i.rr?' 回'+md(i.rr[0]):i.rm>=.01?' 比'+(i.rm*100).toFixed(i.rm<.1?1:0)+'%':''}`:i.rr?'回'+md(i.rr[0]):''}</span>`}\n"
  "function shLine(c){const i=shInfo(c);if(!i)return `<div class=\"sh-m\"><span>做空資訊讀取中…</span></div>`;const v=i.v;return `<div class=\"sh-m\"><span><b class=\"xt x${i.k}\">${i.t}</b>${i.d}</span>${v?`<span>融券 <b>${fmt(v[0])}</b> 張 (<b class=\"${cls(v[2])}\">${v[2]>0?'+':''}${fmt(v[2])}</b>)</span>${i.u>=.01?`<span>限額使用 <b>${(i.u*100).toFixed(0)}%</b></span>`:''}<span>券資比 <b>${i.rm==null?'—':(i.rm*100).toFixed(1)+'%'}</b></span>`:''}${i.rr?`<span>停券 <b>${md(i.rr[0])}～${md(i.rr[1])}</b> (${md(i.rr[0])} 前要回補${i.rr[2]?'・'+esc(i.rr[2]):''})</span>`:''}<span>融券 ${md(SHT.md)}・平盤下名單 ${md((SHT.fd||{})[MKT[c]==='上櫃'?'tpex':'twse']||'')||'—'}</span></div>`}\n"),
 ("SIDE=SIDE==='s'?'l':'s';REVS='';paintBar()", "SIDE=SIDE==='s'?'l':'s';REVS='';if(SIDE==='s')shLoad();paintBar()"),
 ("<canvas class=\"km-cv\"></canvas></article>`).join('');fitS();", "${sideS()?shTag(r):''}<canvas class=\"km-cv\"></canvas></article>`).join('');fitS();"),
 ("・60日區間<b>${r.pos60==null?'—':Math.round(r.pos60*100)+'%'}</b></span></div>\n",
  "・60日區間<b>${r.pos60==null?'—':Math.round(r.pos60*100)+'%'}</b></span></div>${!r.ov&&sideS()?shLine(r.c):''}\n"),
 ("重新整理回到「多」；已選中的排序鈕再點一次＝反向；",
  "重新整理回到「多」；空模式 K 線左上角＝做空資訊：<b>可空</b>＝可融券且平盤以下能放空、<b>平✗</b>＝可融券但平盤以下不能放空 (不在名單或前一日跌停)、<b>停券</b>＝暫停融券賣出、<b>券滿</b>＝融券餘額達限額、<b>無券</b>＝不是信用交易股；後面＝融券餘額 (張)、比＝券資比 (融券÷融資，≥1% 才顯示)、回＝停券起日 (最後回補日)；資料為前一晚公布，各券商實際券源查不到，下單前以券商為準；已選中的排序鈕再點一次＝反向；"),
 # 排行名單第 3 行多一顆篩選鈕 → 市場鈕在 K 線模式也用短字「合 市 櫃」（估值模式本來就是）
 ("b.style.flex=V?'1 1 0':'';", "b.style.flex=V?'1 1 0':'1.5 1 0';"),
 ("[['a',V?'合':'合併'],['L',V?'市':'上市'],['O',V?'櫃':'上櫃']]", "[['a','合'],['L','市'],['O','櫃']]"),
 ("b.classList.toggle('sm',V);", "b.classList.add('sm');b.title='合併／上市／上櫃';"),
 ("v1120f", "v1120g"),
]
for a, b in E:
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)
if not prod:
    s = s.replace('<title>', '<title>[beta] ', 1)
open('scan.html' if prod else 'beta_scan_sh.html', 'w', encoding='utf-8').write(s)
print('ok')
