#!/usr/bin/env python3
"""排序加「榜序」：買超前 20／注意處置名單依名單原本順序（第 1～20 名）排，進這些清單時預設用它（2026-10-30）
需先套過 patch_tophist.py。用法：python3 patch_rank.py beta_scan.html beta_scan.html
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()

def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

rep('<div class="r" title="排序"><button data-k="chg" aria-pressed="true">日漲</button>',
    '<div class="r" title="排序"><button data-k="li" id="sortLi" hidden title="照名單順序（第 1～20 名）">榜序</button><button data-k="chg" aria-pressed="true">日漲</button>')
# 進榜單清單預設榜序、離開時改回日漲
rep("  const past=isN&&NDATE&&DAYS[0]&&NDATE!==DAYS[0];TOPK=isT?TKEY[sel.id]:'';",
    "  const past=isN&&NDATE&&DAYS[0]&&NDATE!==DAYS[0];TOPK=isT?TKEY[sel.id]:'';\n  $('sortLi').hidden=!isN;if(isN&&!RANKED)sortK='li';else if(!isN&&sortK==='li')sortK='chg';RANKED=isN;paintBar();")
rep("let CHGP='d',", "let RANKED=false,CHGP='d',")
rep("  CUR_IDS=ids;ROWS=ids.map(c=>build(c)).filter(Boolean);",
    "  CUR_IDS=ids;ROWS=ids.map((c,i)=>{const r=build(c);if(r)r.li=i;return r}).filter(Boolean);")
rep("const key={chg:r=>r[ck]??-9,", "const key={li:r=>-r.li,chg:r=>r[ck]??-9,")
rep("「日漲」鈕連點循環日／週（5 日）／月（20 日）漲幅排序；",
    "「榜序」＝照名單原本順序（買超前 20 的第 1～20 名、注意股連續天數、處置剩餘日），只在這些名單出現、進入時預設；「日漲」鈕連點循環日／週（5 日）／月（20 日）漲幅排序；")
open(dst, 'w', encoding='utf-8').write(s)
print('ok')
