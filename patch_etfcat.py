#!/usr/bin/env python3
"""2026-11-22 15:47 📦 ETF 分類切換鈕「全 市值 高息 科技 債券 國外」（世杰選方案 ①）。
首頁 ETF 主題頁：說明列下方一排膠囊，點了只顯示那一類，中位數也只算那一類；離開 ETF 主題回到「全」。
掃描頁 ETF 名單：統計列最上面同一排膠囊，只篩小卡；換名單回到「全」（同海外龍頭）。
分類＝data/etf.json 每檔備註「類別｜說明」的類別（fetch_rank.py 的 ETF_THEME）。
用法：python3 patch_etfcat.py       → beta.html＋beta_scan_etfc.html
      python3 patch_etfcat.py prod  → index.html＋scan.html
只能對 index v1122c、scan v1122b 跑一次。
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


CHIP_CSS = ("<style>/* 2026-11-22 ETF 分類切換 */.ecb{display:flex;gap:4px;flex-wrap:nowrap;margin:6px 0 2px;overflow-x:auto;scrollbar-width:none}"
            ".ecb::-webkit-scrollbar{display:none}"
            ".ecb button{flex:none;border:1px solid var(--line);background:none;color:var(--muted);font:500 13px/26px var(--f-body);padding:0 10px;border-radius:14px;white-space:nowrap;-webkit-tap-highlight-color:transparent}"
            ".ecb button[aria-pressed=true]{background:var(--fg);border-color:var(--fg);color:var(--bg);font-weight:700}"
            ".ecb button small{font-size:11px;opacity:.7;margin-left:2px}</style>\n</head>")

# ---- 首頁 ----
I = [
    ("</head>", CHIP_CSS),
    ("let ETS='';", "let ETS='',ETC='a';const etfCat=c=>{const r=ETFJ&&(ETFJ.stocks||[]).find(x=>x[0]===c);return r?r[1].split('｜')[0]:''};"),
    ("function etfPage(){const t=THEMES.find(x=>x.id==='etf');if(!t||!ETFJ)return;const a=ETFJ.asof,ids=t.stocks.map(x=>x[0])",
     "function etfPage(){const t0=THEMES.find(x=>x.id==='etf');if(!t0||!ETFJ)return;"
     "const CS=[...new Set(t0.stocks.map(x=>etfCat(x[0])).filter(Boolean))];if(ETC!=='a'&&!CS.includes(ETC))ETC='a';"
     "const t={...t0,stocks:ETC==='a'?t0.stocks:t0.stocks.filter(x=>etfCat(x[0])===ETC)};"
     "const ecb=`<div class=\"ecb\" id=\"ecb\"><button data-ec=\"a\" aria-pressed=\"${ETC==='a'}\">全<small>${t0.stocks.length}</small></button>${CS.map(k=>`<button data-ec=\"${k}\" aria-pressed=\"${ETC===k}\">${k}<small>${t0.stocks.filter(x=>etfCat(x[0])===k).length}</small></button>`).join('')}</div>`;"
     "const a=ETFJ.asof,ids=t.stocks.map(x=>x[0])"),
    ("・固定 ${ids.length} 檔・盤後更新</span><br>${ids.length} 檔中位數：",
     "・固定 ${t0.stocks.length} 檔・盤後更新</span><br>${ETC==='a'?'':`<b>${ETC}</b> `}${ids.length} 檔中位數："),
    ("溢價買進等於多付錢。點一列看 K 線 (掃描頁)。`;",
     "溢價買進等於多付錢。點一列看 K 線 (掃描頁)。${ETC==='國外'?'<br>🌏 <b>國外 ETF 在台股時段交易、追蹤前一晚的海外市場</b>：日漲跌反映昨晚美股，不能跟台股 ETF 同一天直接比；海外休市時折溢價容易變大。':''}`+ecb;"
     "$('ecb').onclick=e=>{const b=e.target.closest('button[data-ec]');if(b&&b.dataset.ec!==ETC){ETC=b.dataset.ec;etfPage()}};"),
    ("{const _st=showTheme;showTheme=function(tid){_st(tid);if(tid==='etf')etfPage();",
     "{const _st=showTheme;showTheme=function(tid){_st(tid);if(tid!=='etf')ETC='a';if(tid==='etf')etfPage();"),
    ("市值→高息→科技→債券)", "市值→高息→科技→債券→國外)"),
    ("名單＝各類規模前 5 大＋00713、00940、00892；", "名單＝各類規模前 5 大＋00713、00940、00892；上方「全 市值 高息…」可只看一類 (中位數也只算那類，離開 ETF 主題回到「全」)；"),
    ("desc:'台股 ETF 各類規模前 5 大 (市值型、高股息、科技/半導體、債券)＋00713、00940、00892'",
     "desc:'台股掛牌 ETF 各類規模前 5 大 (市值型、高股息、科技/半導體、債券、國外)＋00713、00940、00892'"),
    ('<span style="opacity:.5">v1122c</span>', '<span style="opacity:.5">v1122d</span>'),
]

# ---- 掃描頁 ----
S = [
    ("</head>", CHIP_CSS),
    ("if(!cur||cur.id!==sel.id||cur.kind!==sel.kind)OVF='a';", "if(!cur||cur.id!==sel.id||cur.kind!==sel.kind){OVF='a';ETFC='a'}"),
    ("if(ETFJ&&(ETFJ.stocks||[]).length){const a=ETFJ.asof||'';",
     "if(ETFJ&&(ETFJ.stocks||[]).length){const a=ETFJ.asof||'';ETFJ.stocks.forEach(([c,n])=>{ECAT[c]=(n||'').split('｜')[0]});"),
    ("function rowsK(){const S=sideS();let R=ROWS.filter(r=>(",
     "// 2026-11-22：📦 ETF 分類切換（全 市值 高息 科技 債券 國外）；只在 ETF 名單生效、換名單回到「全」\n"
     "let ETFC='a';const ECAT={};const etfOn=()=>!!cur&&cur.kind==='t'&&cur.id==='etf';\n"
     "function ecBar(){if(!etfOn())return '';const CS=[...new Set(ROWS.map(r=>ECAT[r.c]).filter(Boolean))];if(CS.length<2)return '';if(ETFC!=='a'&&!CS.includes(ETFC))ETFC='a';\n"
     "  return `<div class=\"ecb\"><button data-ec=\"a\" aria-pressed=\"${ETFC==='a'}\">全<small>${ROWS.length}</small></button>${CS.map(k=>`<button data-ec=\"${k}\" aria-pressed=\"${ETFC===k}\">${k}<small>${ROWS.filter(r=>ECAT[r.c]===k).length}</small></button>`).join('')}</div>`}\n"
     "function rowsK(){const S=sideS();let R=ROWS.filter(r=>(!etfOn()||ETFC==='a'||ECAT[r.c]===ETFC)&&("),
    ("  const rz=rkZ();\n", "  const rz=ecBar()+rkZ();\n"),
    ("  $('cnt').addEventListener('click',e=>{",
     "  $('cnt').addEventListener('click',e=>{{const b=e.target.closest('button[data-ec]');if(b){if(b.dataset.ec!==ETFC){ETFC=b.dataset.ec;render()}return}}"),
    ('<span style="opacity:.5">v1122b</span>', '<span style="opacity:.5">v1122d</span>'),
]

I_BETA = [("$('tScan').href='scan.html#'+encodeURIComponent(t.id);", "$('tScan').href=(t.id==='etf'?'beta_scan_etfc.html?v=1#':'scan.html#')+encodeURIComponent(t.id);"),
          ("location.href='scan.html#etf'", "location.href='beta_scan_etfc.html?v=1#etf'")]
S_BETA = [("?'index.html#t/'+encodeURIComponent(sel.id):'index.html';", "?(sel.id==='etf'?'beta.html?v=20#t/':'index.html#t/')+encodeURIComponent(sel.id):'index.html';")]

patch('index.html', 'index.html' if prod else 'beta.html', I, I_BETA)
patch('scan.html', 'scan.html' if prod else 'beta_scan_etfc.html', S, S_BETA)
