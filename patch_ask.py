#!/usr/bin/env python3
"""「🔍 問AI」鈕：看到個股大漲／大跌，一鍵開 Google AI 模式（udm=50）並自動帶好問題
（名稱 代號 日期 漲跌幅 → 原因？新聞來源、法人買賣超、是否被列注意或處置）。
個股頁：標頭漲跌幅右邊；掃描頁：K 線／估值放大卡「財報・估值 →」左邊。
用法：python3 patch_ask.py index.html beta.html
      python3 patch_ask.py scan.html beta_scan_ask.html
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
n0 = len(s)

def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (s.count(old), old[:80])
    s = s.replace(old, new)

# 共用：組問題＋網址。pct＝漲跌幅（%），md＝「11/11」；|漲跌| ≥5% 寫大漲／大跌，不到 0.5% 只問近期股價
ASK = r"""function askUrl(name,code,pct,md){name=String(name||'').replace(/\*$/,'');
  const a=pct==null||!isFinite(pct)?0:Math.abs(pct),w=a<0.5?'':(a>=5?'大':pct>0?'上':'下')+(pct>0?'漲':'跌');
  const q=`${name} ${code} `+(w?`${md?md+' ':''}${w} ${a.toFixed(2)}% 的原因？`:'近期股價漲跌的原因？')+'請列出新聞來源、法人買賣超、是否被列注意股或處置股';
  return 'https://www.google.com/search?udm=50&hl=zh-TW&q='+encodeURIComponent(q)}
"""

if 'id="valStrip"' in s:   # ---- 個股頁 ----
    rep('<span class="foot" id="asof">載入中…</span><span class="chg" id="chg"></span>',
        '<span class="foot" id="asof">載入中…</span><span class="chgw"><span class="chg" id="chg"></span><a class="askai" id="askAi" href="https://www.google.com/search?udm=50" target="_blank" rel="noopener" aria-label="問 Google AI 今天漲跌原因">🔍 問AI</a></span>')
    rep('.chg{font-family:var(--f-num);font-size:13px;color:var(--up)}',
        '.chg{font-family:var(--f-num);font-size:13px;color:var(--up)}\n'
        '.chgw{display:inline-flex;align-items:center;gap:8px;white-space:nowrap}\n'
        '.askai{flex:none;font-size:12px;font-weight:700;line-height:24px;height:26px;padding:0 10px;border:1px solid var(--accent);border-radius:13px;color:var(--accent);background:var(--card);text-decoration:none;-webkit-tap-highlight-color:transparent}\n'
        '.askai:active{background:var(--accent);color:#fff}')
    rep("function header(){\n", ASK + "function header(){\n")
    rep("  $('px').style.color=col;$('chg').style.color=col;\n",
        "  $('px').style.color=col;$('chg').style.color=col;\n"
        "  {const a=$('askAi'),mk=()=>askUrl($('nm').textContent||D.name||D.id,D.id,L.prev?chp:null,+L.date.slice(5,7)+'/'+ +L.date.slice(8,10));a.onclick=()=>{try{a.href=mk()}catch(e){}};try{a.href=mk()}catch(e){}}\n")
else:                      # ---- 掃描頁 ----
    rep('.sh-seg a{margin-left:auto;background:var(--accent);border-color:var(--accent);color:#fff;font-weight:700}',
        '.sh-seg a{margin-left:auto;background:var(--accent);border-color:var(--accent);color:#fff;font-weight:700}\n'
        '.sh-seg a.askai{background:var(--card);color:var(--accent);padding:0 7px;white-space:nowrap;flex:none}\n'
        '.sh-seg button[data-n]{padding:0 8px;white-space:nowrap;flex:none}\n'
        '.sh-seg a.askai+a{margin-left:0;white-space:nowrap;flex:none}')
    rep('<a href="index.html#${esc(r.c)}">財報・估值 →</a></div>`;',
        '${askA(r)}<a href="index.html#${esc(r.c)}">財報・估值 →</a></div>`;', 2)
    rep("function shCnt(long){",
        ASK + "function askA(r){return `<a class=\"askai\" target=\"_blank\" rel=\"noopener\" aria-label=\"問 Google AI 漲跌原因\" href=\"${esc(askUrl(r.n,r.c,r.chg==null?null:r.chg*100,r.d?md(r.d):''))}\">🔍AI</a>`}\n"
        "function shCnt(long){")

open(dst, 'w', encoding='utf-8').write(s)
print('ok', n0, '->', len(s))
