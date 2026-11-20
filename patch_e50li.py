#!/usr/bin/env python3
"""2026-11-20 掃描頁：🏆 0050成份股 進名單預設「榜序」（市值由大到小），跟買超前20／排行名單同一套規則：
進去時預設榜序、在名單內手動換排序會保留、離開時若仍是榜序就改回日漲。世杰 15:51 要求，直接上正式版。
用法：python3 patch_e50li.py（改 scan.html，只能對 v1120c 跑一次）"""
s = open('scan.html', encoding='utf-8').read()
E = [
 ("  if(isN&&!RANKED)sortK='li';else if(!isN&&sortK==='li'&&(RANKED||!isTh))sortK=MODE==='v'?'peh':'chg';RANKED=isN;paintBar();",
  "  const isRk=isN||(sel.kind==='t'&&sel.id==='e50');   // 2026-11-20：0050 成份股也預設榜序\n"
  "  if(isRk&&!RANKED)sortK='li';else if(!isRk&&sortK==='li'&&(RANKED||!isTh))sortK=MODE==='v'?'peh':'chg';RANKED=isRk;paintBar();"),
 ("v1120c", "v1120d"),
]
for a, b in E:
    assert s.count(a) == 1, (s.count(a), a[:60])
    s = s.replace(a, b)
open('scan.html', 'w', encoding='utf-8').write(s)
print('ok')
