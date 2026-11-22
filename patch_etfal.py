#!/usr/bin/env python3
"""2026-11-22 19:29 📦 ETF 加「主動」「槓桿」兩類（世杰選方案 ①：加進現有 ETF 主題；名單固定 5 檔，規模每天自動更新、類別內重排）。
名單在 fetch_rank.py 的 ETF_THEME（主動：00981A 00406A 00403A 00991A 00982A；槓桿：00631L 00685L 00675L 00670L 00637L）。
這支只改首頁顯示：分組標題 emoji（主動🎯、槓桿⚡）、主題描述、選「主動」「槓桿」時多一行風險提醒、頁尾類別順序。
（分類膠囊、分組標題列、掃描頁膠囊都是從資料自動產生，不用改。）
用法：python3 patch_etfal.py       → beta_etfl.html（beta.html 是另一個 session 的熱力圖 beta）
      python3 patch_etfal.py prod  → index.html
頁尾版本用正規式換成 v1122r；其餘錨點都要剛好出現一次。
"""
import re, sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'

E = [
    ("EM={'市值':'🏛️','高息':'💰','科技':'💻','債券':'🏦','國外':'🌏'}",
     "EM={'市值':'🏛️','高息':'💰','科技':'💻','債券':'🏦','國外':'🌏','主動':'🎯','槓桿':'⚡'}"),
    ("desc:'台股掛牌 ETF 各類規模前 5 大 (市值型、高股息、科技/半導體、債券、國外)＋00713、00940、00892'",
     "desc:'台股掛牌 ETF 各類規模前 5 大 (市值型、高股息、科技/半導體、債券、國外、主動式、槓桿)＋00713、00940、00892'"),
    ("${ETC==='國外'?'<br>🌏 <b>國外 ETF",
     "${ETC==='槓桿'?'<br>⚡ <b>槓桿 ETF 每天重新平衡，只適合短線</b>：盤整或大跌後反彈會有耗損，例如指數跌 22% 時正2 跌約 42～44%，之後指數要漲 28% 回本、正2 要漲約 75%；00670L 是美股、00637L 是陸股，跟台股正2 不同步。':''}"
     "${ETC==='主動'?'<br>🎯 <b>主動式 ETF 由經理人選股，不等於抗跌</b>：多半重壓 AI、高波動股，這個月跌幅比 0050 多 10～18 個百分點；上市都還不到一年半，看不出長期能不能贏大盤。':''}"
     "${ETC==='國外'?'<br>🌏 <b>國外 ETF"),
    ("市值→高息→科技→債券→國外)", "市值→高息→科技→債券→國外→主動→槓桿)"),
    # 膠囊 8 顆會超出畫面：選中的那顆自動捲到看得到
    ("$('ecb').onclick=e=>{", "{const eb=$('ecb'),sb=eb&&eb.querySelector('[aria-pressed=true]');if(sb)eb.scrollLeft=Math.max(0,sb.offsetLeft-eb.clientWidth/2+sb.offsetWidth/2)}$('ecb').onclick=e=>{"),
    ("名單＝各類規模前 5 大＋00713、00940、00892；", "名單＝各類規模前 5 大＋00713、00940、00892 (主動、槓桿兩類 11/22 加入，用 11/20 規模挑的，名單固定)；"),
]

s = open('index.html', encoding='utf-8').read()
for a, b in E:
    assert s.count(a) == 1, (s.count(a), a[:60])
    s = s.replace(a, b)
s, nv = re.subn(r'<span style="opacity:\.5">v1122[a-z]</span>', '<span style="opacity:.5">v1122r</span>', s)
assert nv == 1, nv
if not prod:
    s = s.replace('<title>', '<title>[beta] ', 1)
dst = 'index.html' if prod else 'beta_etfl.html'
open(dst, 'w', encoding='utf-8').write(s)
print('ok', dst)
