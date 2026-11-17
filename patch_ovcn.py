#!/usr/bin/env python3
"""2026-11-18 掃描頁「🌏 海外龍頭」加第四個市場「陸」（接在 patch_ovs／ovus／ovord 之後）

用法：python3 patch_ovcn.py           → 讀 scan.html，輸出 beta_scan_ovcn.html
      python3 patch_ovcn.py prod      → 直接改 scan.html（已套用過會因 assert 中止）

起因：世杰說記憶體的海外龍頭想看長鑫科技（688825，2026/7/27 科創板上市），選「① 新增陸市場」。
做法：
  1. themes.json 主題多一個 cn 欄位＝[[代號, 名稱], …]（滬深 A 股；資料同樣在 data/ovs.json，鍵 cn代號，Yahoo .SS／.SZ）。
     目前只有記憶體有（長鑫科技），排序在 ov：SK海力士→三星電子→MU→長鑫科技→鎧俠→SNDK。
  2. 切換鈕變「全 美 日 韓 陸」（主題有哪幾國就出現哪幾顆）；四國都有時標題列改緊湊版（鈕距縮小、收合只剩箭頭），避免 iPhone 上被切。
  3. 沒有陸股站 → 放大卡右下不放站內連結。
"""
import sys

PROD = len(sys.argv) > 1 and sys.argv[1] == 'prod'
SRC = 'scan.html'
OUT = 'scan.html' if PROD else 'beta_scan_ovcn.html'
VER = 'v1118a'

s = open(SRC, encoding='utf-8').read()
assert 'OVN' in s, '要先套 patch_ovord.py'
assert "cn:'陸'" not in s, '已套用過'


def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (s.count(old), old[:80])
    s = s.replace(old, new)


rep("...(t.kr||b.kr||[]).map(x=>['kr'+x[0],x[1]])];", "...(t.kr||b.kr||[]).map(x=>['kr'+x[0],x[1]]),...(t.cn||b.cn||[]).map(x=>['cn'+x[0],x[1]])];")
rep("const OVMK={us:'美',jp:'日',kr:'韓'};", "const OVMK={us:'美',jp:'日',kr:'韓',cn:'陸'};")
rep("const MK=['us','jp','kr'].filter(", "const MK=['us','jp','kr','cn'].filter(")
# 陸股沒有站內個股頁
rep('`<a href="${r.m}/#${esc(r.lk)}">${r.mk}股站 →</a>`', '(r.m===\'cn\'?\'\':`<a href="${r.m}/#${esc(r.lk)}">${r.mk}股站 →</a>`)')
# 四國都有 → 緊湊版標題列
rep('<div class="ovs-t"><button class="tt"', '<div class="ovs-t${MK.length>3?\' x4\':\'\'}"><button class="tt"')
rep("<button class=\"cl\">${OVC?'展開 ▸':'收合 ▾'}</button>", "<button class=\"cl\" aria-label=\"${OVC?'展開':'收合'}\">${OVC?'展開 ▸':MK.length>3?'▾':'收合 ▾'}</button>")
rep('.ovs-t .cl{margin-left:auto;',
    '.ovs-t.x4{gap:4px;padding-left:7px;padding-right:7px}.ovs-t.x4 .fs{gap:2px}.ovs-t.x4 .fs button{padding:0 5px;letter-spacing:-.02em}.ovs-t.x4 .cl{font-size:13px;padding:0 4px}\n'
    '.ovs-t .cl{margin-left:auto;')

# ---- 版本、頁尾說明 ----
rep('這個主題對應的美股／日股／韓股（跟首頁主題頁的「對應美股／日股／韓股」同一份名單）',
    '這個主題對應的美股／日股／韓股／陸股（美日韓跟首頁主題頁的「對應美股／日股／韓股」同一份名單；陸股＝滬深 A 股，目前只有記憶體的長鑫科技，沒有站內個股頁）')
rep('日韓平日約 15:00 與 17:40、美股約 05:30 與 08:00 更新', '日韓平日約 15:00 與 17:40、陸股約 17:40（15:00 收盤）、美股約 05:30 與 08:00 更新')
rep('<span style="opacity:.5">v1117h</span>', '<span style="opacity:.5">' + VER + '</span>')

if not PROD:
    s = s.replace('<title>', '<title>β ', 1)
open(OUT, 'w', encoding='utf-8').write(s)
print('wrote', OUT, len(s))
