#!/usr/bin/env python3
"""2026-11-22 16:58 📦 ETF 近 12 月殖利率（世杰選建議清單第 4 項）。
資料：fetch_adj.py 的 cash（ETF 每單位配息，380 天）→ fetch_rank.py build_etf 算 px[8]＝近 12 月殖利率%、px[9]＝配息次數。
主題頁：週欄下方加「殖9.1%」（不配息＝「不配息」），原本的「息11/17」移到第二行小字；
「週」標題連點：週▼→週▲→殖▼→殖▲→回名單順序；說明列中位數多「殖」；頁尾說明。
用法：python3 patch_etfyld.py       → beta.html
      python3 patch_etfyld.py prod  → index.html
只能對 index v1122f 跑一次。
"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'

E = [
    ("col={px:0,d:1,w:2,m:3,v:6};", "col={px:0,d:1,w:2,m:3,v:6,y:8};"),
    ("${th('w','週')}", "${k==='y'?`<th data-ek=\"w\" class=\"on\">殖${+d>0?' ▲':' ▼'}</th>`:th('w','週')}"),
    ("ETS=!nk?'':k!==nk?nk+':-1':d==='-1'?nk+':1':'';etfPage();return}",
     "ETS=!nk?'':nk==='w'?(ETS==='w:-1'?'w:1':ETS==='w:1'?'y:-1':ETS==='y:-1'?'y:1':ETS==='y:1'?'':'w:-1'):k!==nk?nk+':-1':d==='-1'?nk+':1':'';etfPage();return}   // 週 標題連點：週▼ 週▲ 殖▼ 殖▲ 回名單順序"),
    ("<td class=\"${sign(w)}\">${pct(w)}${(()=>{",
     "<td class=\"${sign(w)}\">${pct(w)}${(()=>{const y=etfPx(c,8),n=etfPx(c,9);return y==null?'':y>0?`<span class=\"sub\" style=\"color:var(--fg)\" title=\"近 12 月配息 ${n} 次合計 ÷ 最新收盤\">殖${fmt(y,1)}%</span>`:'<span class=\"sub\" style=\"color:var(--muted)\">不配息</span>'})()}${(()=>{"),
    ("・季 ${s(g(4))}<br>ETF 沒有 EPS", "・季 ${s(g(4))}${(()=>{const y=median(ids.map(i=>etfPx(i,8)).filter(v=>v>0));return y==null?'':`・殖 <strong>${fmt(y,1)}%</strong>`})()}<br>ETF 沒有 EPS"),
    ("週欄下方「息11/18」＝近 20 個交易日內的除息日 (點住可看配息占比)",
     "週欄下方「殖9.1%」＝<b>近 12 月殖利率</b>＝除息日在近 350 天內 (避免去年同月那次重複算) 的每單位配息合計 ÷ 最新收盤 (配息：證交所/櫃買除權息計算結果表的除息前收盤 − 參考價；分割前的配息已換算；上市未滿一年的會偏低；說明列的殖利率中位數不含不配息的)，<b>科技/半導體、海外 ETF 的高殖利率多半來自資本利得 (前一年大漲) 配出來的一次性大額配息</b>，加上最近股價大跌把分母變小，不代表明年配得出一樣多；「不配息」＝近 12 月沒有配息 (例 009816 不配息、配息再投入)；「週」標題連點可改用殖利率排序；再下面「息11/18」＝近 20 個交易日內的除息日 (點住可看配息占比)"),
    ("<b>折溢價、殖利率本站還沒有</b>：", "<b>折溢價本站還沒有</b>："),
    ('<span style="opacity:.5">v1122f</span>', '<span style="opacity:.5">v1122g</span>'),
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
