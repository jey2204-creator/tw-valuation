#!/usr/bin/env python3
"""2026-11-22 17:51 📦 ETF 規模自動更新（世杰說「🥉 規模自動更新 做給我看」）。
資料：data/etfnav.json 的 d[代號][6]＝規模億元＝發行單位數 × 預估淨值（證交所 all_etf.txt，etfnav.yml 每個交易日盤後更新）。
網頁載入 etfnav.json 後：
  ETFJ.aum[c] 換成當天規模（沒有的沿用 fetch_rank.py 手填的 11/20 值）、ETFJ.aumAsof＝etfnav 的資料日；
  ETFJ.stocks 在每個類別內依當天規模由大到小重排（類別順序不變：市值→高息→科技→債券→國外；名單本身不變）。
頁尾說明改成「每個交易日自動更新」。
用法：python3 patch_etfaum2.py       → beta_etfa.html（beta.html 目前是另一個 session 的熱力圖 beta，所以用獨立檔名）
      python3 patch_etfaum2.py prod  → index.html
頁尾版本用正規式換成 v1122q；其餘錨點都要剛好出現一次。
"""
import re, sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'

E = [
    ("Object.entries(ETFJ.px).forEach(([c,p])=>{const v=NAVJ.d[c];p[10]=v?v[2]:null})}}catch(e){}",
     "Object.entries(ETFJ.px).forEach(([c,p])=>{const v=NAVJ.d[c];p[10]=v?v[2]:null});"
     # 規模自動更新：當天規模覆蓋手填值，類別內依規模重排
     "if(ETFJ.aum&&ETFJ.stocks){let k=0;ETFJ.stocks.forEach(([c])=>{const v=NAVJ.d[c];if(v&&v[6]){ETFJ.aum[c]=v[6];k++}});"
     "if(k){ETFJ.aumAsof=NAVJ.asof||ETFJ.aumAsof;ETFJ.aumLive=1;const cat=x=>x[1].split('｜')[0],CO=[...new Set(ETFJ.stocks.map(cat))];"
     "ETFJ.stocks=ETFJ.stocks.map((x,i)=>[x,i]).sort((a,b)=>CO.indexOf(cat(a[0]))-CO.indexOf(cat(b[0]))||(ETFJ.aum[b[0][0]]||0)-(ETFJ.aum[a[0][0]]||0)||a[1]-b[1]).map(x=>x[0])}}"
     "}}catch(e){}"),
    ("規模 (淨值×受益權單位數)，${ETFJ&&ETFJ.aumAsof?+ETFJ.aumAsof.slice(4,6)+'/'+ +ETFJ.aumAsof.slice(6):''} 的數字 (玩股網排行，00892 取證交所)，<b>不會每天自動更新</b>，排名變動時告訴 Claude 調整；",
     "規模＝發行單位數 × 預估淨值，${ETFJ&&ETFJ.aumAsof?+ETFJ.aumAsof.slice(4,6)+'/'+ +ETFJ.aumAsof.slice(6):''} 的數字，${ETFJ&&ETFJ.aumLive?'<b>每個交易日盤後自動更新</b> (證交所「ETF 盤中預估淨值」彙總)，同類別內的順序也跟著規模自動重排':'目前是手填的玩股網排行 (自動資料讀取失敗)'}；名單本身 (哪幾檔) 不會自動換，要增減告訴 Claude；"),
]

s = open('index.html', encoding='utf-8').read()
for a, b in E:
    assert s.count(a) == 1, (s.count(a), a[:60])
    s = s.replace(a, b)
s, nv = re.subn(r'<span style="opacity:\.5">v1122[a-z]</span>', '<span style="opacity:.5">v1122q</span>', s)
assert nv == 1, nv
if not prod:
    s = s.replace('<title>', '<title>[beta] ', 1)
dst = 'index.html' if prod else 'beta_etfa.html'
open(dst, 'w', encoding='utf-8').write(s)
print('ok', dst)
