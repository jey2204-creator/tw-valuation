#!/usr/bin/env python3
"""2026-11-20 掃描頁：新增名單「📉 投信賣超前20」（方案 ①）。
起因：11/20 22:09 世杰在「投信買超前20」開空方模式，說想看投信賣超前 20；22:12 選「照 ① 出 beta」。
資料：itrust/top_extract.py 多寫 lists.is／hist[日].is（賣超金額 ≥0.5 億、依賣超佔股本％取前 20；來源同買超榜 itrust/data.js）。
做法：
  1. 名單鈕 isell（排在 🤝 土洋同買後面；「全部▾」在「⭐ 自選・訊號籌碼」），沿用買超榜那一套：日期選單、榜序、榜N、K 棒底下的上榜日點（綠）。
  2. 進這個名單自動切到「空」（破月／破季／投賣3、綠虛線＝前 20 日低、券／平盤下標記）；離開時若沒手動動過多空鈕就切回「多」。
  3. 日期選單只列有這個榜的日子（賣超榜從 10/22 起才有）。
  4. 首頁產業主題表（11/20 22:41 世杰說「首頁產業主題表要加這個主題，做給我看」）：自動主題 isell，排在 🤝 土洋同買後面；
     備註「投賣0.91%・連2」＝賣超佔股本％、連續 2 天在榜上；主題頁「📈 掃 K 線」→ 掃描頁同名名單，掃描頁左上「掃描」→ 首頁這個主題。
用法：python3 patch_isell.py → beta.html＋beta_scan_isell.html（兩個 beta 互相連）；python3 patch_isell.py prod → index.html＋scan.html。
只能對舊版（index v1120b、scan v1120g）跑一次。
"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
BV = '17'   # beta.html?v=
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
 ("紅框＝今天上漲且觸及前 20 日高；",
  "紅框＝今天上漲且觸及前 20 日高；<b>📉 投信賣超前20</b>＝投信當天賣超金額 ≥0.5 億、依賣超佔股本％取前 20 (榜序第 1 名＝賣最兇)，進這個名單會自動切到「空」；"),
 # K 棒底下的上榜日點：賣超榜用綠色
 ("css(k==='it'?'--ma20':k==='fi'||k==='q'?'--accent':'--warm')", "css(k==='it'?'--ma20':k==='is'?'--down':k==='fi'||k==='q'?'--accent':'--warm')"),
 # 「掃描」改成返回鈕（11/21 15:09 世杰選 ①）：原本的「← 估值看板」排在名單橫列最後面（約 5,300px 外）找不到 → 拿掉，
 # 左上固定的「掃描」改成「‹ 掃描」連結，沿用 .hd a.home 的 href 邏輯（主題→首頁該主題頁，其餘→首頁）
 ('<span class="t">掃描</span>', '<a class="t home" href="index.html" title="回估值看板 (首頁對應的主題)">‹ 掃描</a>'),
 ('    <a class="home" href="index.html">← 估值看板</a>\n', ''),
 (".hd a.home{flex:none;font-size:12px;color:var(--muted);margin-left:auto}", ".hd a.home{color:inherit;text-decoration:none;white-space:nowrap}.hd a.home:active{opacity:.5}"),
 ("v1120g", "v1120h"),
]
# beta 才有：兩個 beta 互相連（正式版的 index／scan 還沒有這個主題）
E_BETA = [("?'index.html#t/'+encodeURIComponent(sel.id):'index.html';", "?(sel.id==='isell'?'beta.html?v=" + BV + "#t/':'index.html#t/')+encodeURIComponent(sel.id):'index.html';")]
# ---- 首頁 index.html ----
I = [
 ("const AUTO_IDS=['e50','itop','ftop','btop','natt',", "const AUTO_IDS=['e50','itop','ftop','btop','isell','natt',"),
 ("    const p=k==='both'?`投${r.p}%＋外${r.fp}%`:`${k==='it'?'投':'外'}${r.p}%`;",
  "    const p=k==='both'?`投${r.p}%＋外${r.fp}%`:k==='is'?`投賣${Math.abs(r.p)}%`:`${k==='it'?'投':'外'}${r.p}%`;"),
 ("          ...mk('btop','🤝 土洋同買前20','both','投信買超 (≥0.5 億) 且外資當天也淨買超，排序＝投本比＋外本比'),\n",
  "          ...mk('btop','🤝 土洋同買前20','both','投信買超 (≥0.5 億) 且外資當天也淨買超，排序＝投本比＋外本比'),\n"
  "          ...mk('isell','📉 投信賣超前20','is','投信賣超佔股本前 20 名 (賣超金額 ≥0.5 億、市值不限)，排序＝賣超佔股本％由大到小 (第 1 名＝賣最兇)'),\n"),
 ("${t.desc}。股名下方「投0.77%・連3」＝佔股本％、連續 3 個交易日在這個榜上。",
  "${t.desc}。股名下方「${t.id==='isell'?'投賣0.77%・連3」＝賣超':'投0.77%・連3」＝'}佔股本％、連續 3 個交易日在這個榜上。"),
 ("v1120b", "v1120i"),
]
I_BETA = [("$('tScan').href='scan.html#'+encodeURIComponent(t.id);", "$('tScan').href=(t.id==='isell'?'beta_scan_isell.html?v=3#':'scan.html#')+encodeURIComponent(t.id);")]


def patch(src, dst, edits, beta_extra):
    s = open(src, encoding='utf-8').read()
    for a, b in list(edits) + ([] if prod else list(beta_extra)):
        assert s.count(a) == 1, (src, s.count(a), a[:70])
        s = s.replace(a, b)
    if not prod:
        s = s.replace('<title>', '<title>[beta] ', 1)
    open(dst, 'w', encoding='utf-8').write(s)
    print('ok', dst)


patch('scan.html', 'scan.html' if prod else 'beta_scan_isell.html', E, E_BETA)
patch('index.html', 'index.html' if prod else 'beta.html', I, I_BETA)
