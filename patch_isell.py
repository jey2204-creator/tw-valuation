#!/usr/bin/env python3
"""2026-11-20 掃描頁：新增名單「📉 投信賣超前20」（方案 ①）。
起因：11/20 22:09 世杰在「投信買超前20」開空方模式，說想看投信賣超前 20；22:12 選「照 ① 出 beta」。
資料：itrust/top_extract.py 多寫 lists.is／hist[日].is（賣超金額 ≥0.5 億、依賣超佔股本％取前 20；來源同買超榜 itrust/data.js）。
做法：
  1. 名單鈕 isell（排在 🤝 土洋同買後面；「全部▾」在「⭐ 自選・訊號籌碼」），沿用買超榜那一套：日期選單、榜序、榜N、K 棒底下的上榜日點（綠）。
  2. 進這個名單自動切到「空」（破月／破季／投賣3、綠虛線＝前 20 日低、券／平盤下標記）；離開時若沒手動動過多空鈕就切回「多」。
  3. 日期選單只列有這個榜的日子（賣超榜從 10/22 起才有）。
  4. 左上「← 估值看板」：首頁沒有這個主題，直接回首頁。
用法：python3 patch_isell.py → beta_scan_isell.html；python3 patch_isell.py prod → scan.html。只能對 v1120g 跑一次。
"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
s = open('scan.html', encoding='utf-8').read()
E = [
 ("const AUTO_IDS=['e50','itop','ftop','btop','natt',", "const AUTO_IDS=['e50','itop','ftop','btop','isell','natt',"),
 ("[['itop','📈 投信買超前20','it'],['ftop','🌐 外資買超前20','fi'],['btop','🤝 土洋同買前20','both']].forEach(",
  "[['itop','📈 投信買超前20','it'],['ftop','🌐 外資買超前20','fi'],['btop','🤝 土洋同買前20','both'],['isell','📉 投信賣超前20','is']].forEach("),
 ("const TKEY={itop:'it',ftop:'fi',btop:'both'},TLAB={it:'📈 投信買超前20',fi:'🌐 外資買超前20',both:'🤝 土洋同買前20',",
  "const TKEY={itop:'it',ftop:'fi',btop:'both',isell:'is'},TLAB={it:'📈 投信買超前20',fi:'🌐 外資買超前20',both:'🤝 土洋同買前20',is:'📉 投信賣超前20',"),
 ("TCOL={it:'var(--ma20)',fi:'var(--accent)',both:'var(--warm)',", "TCOL={it:'var(--ma20)',fi:'var(--accent)',both:'var(--warm)',is:'var(--down)',"),
 # 進賣超榜自動切「空」；離開時若是自動切的就切回「多」
 ("async function pick(sel){if(!cur||cur.id!==sel.id||cur.kind!==sel.kind)OVF='a';cur=sel;",
  "async function pick(sel){{const a=sel.kind==='t'&&sel.id==='isell',b=!!cur&&cur.kind==='t'&&cur.id==='isell';if(a&&!b){if(SIDE!=='s'){SIDE='s';SAUTO=1;REVS='';shLoad()}}else if(!a&&b&&SAUTO){SIDE='l';SAUTO=0;REVS=''}}if(!cur||cur.id!==sel.id||cur.kind!==sel.kind)OVF='a';cur=sel;"),
 ("    if(b.id==='sideB'){SIDE=SIDE==='s'?'l':'s';REVS='';", "    if(b.id==='sideB'){SAUTO=0;SIDE=SIDE==='s'?'l':'s';REVS='';"),
 ("let SIDE='l',SHT=null,SHP=null;", "let SIDE='l',SAUTO=0,SHT=null,SHP=null;"),
 # 日期選單只列有這個榜的日子
 ("DAYS=isF?FDAYS:isR?RDAYS:isT?TDAYS:NDAYS,", "DAYS=isF?FDAYS:isR?RDAYS:isT?TDAYS.filter(d=>THIST[d][TKEY[sel.id]]):NDAYS,"),
 ("if(!NDATE||!(isF?FH.d:isR?RK.hist:isT?THIST:HIST)[NDATE])NDATE=D0;", "if(!NDATE||!(isF?FH.d:isR?RK.hist:isT?THIST:HIST)[NDATE]||(isT&&!DAYS.includes(NDATE)))NDATE=D0;"),
 # 首頁沒有這個主題
 ("sel.id!=='fire'&&!(sel.id in RKEY)?'index.html#t/'", "sel.id!=='fire'&&sel.id!=='isell'&&!(sel.id in RKEY)?'index.html#t/'"),
 ("紅框＝今天上漲且觸及前 20 日高；",
  "紅框＝今天上漲且觸及前 20 日高；<b>📉 投信賣超前20</b>＝投信當天賣超金額 ≥0.5 億、依賣超佔股本％取前 20 (榜序第 1 名＝賣最兇)，進這個名單會自動切到「空」；"),
 # K 棒底下的上榜日點：賣超榜用綠色
 ("css(k==='it'?'--ma20':k==='fi'||k==='q'?'--accent':'--warm')", "css(k==='it'?'--ma20':k==='is'?'--down':k==='fi'||k==='q'?'--accent':'--warm')"),
 ("v1120g", "v1120h"),
]
for a, b in E:
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)
if not prod:
    s = s.replace('<title>', '<title>[beta] ', 1)
open('scan.html' if prod else 'beta_scan_isell.html', 'w', encoding='utf-8').write(s)
print('ok')
