#!/usr/bin/env python3
"""2026-11-20 首頁入口清單「💰 成交值排行」那一列加第三顆「轉」（→ scan.html#ttop 週轉率前50）。
世杰選 ①A：同列加鈕、摘要只留榜首（拿掉「・🆕N」）讓出寬度，列名改「💰 成交排行」。
用法：python3 patch_rkhub3.py → beta.html；python3 patch_rkhub3.py prod → index.html
"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
s = open('index.html', encoding='utf-8').read()


def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new)


rep('<b>💰 成交值排行</b><span id="rkSub">成交值/量前 50</span>', '<b>💰 成交排行</b><span id="rkSub">值/量/週轉率前 50</span>')
rep('<a class="rkbt" href="scan.html#qtop" aria-label="成交量前 50">量</a></div>',
    '<a class="rkbt" href="scan.html#qtop" aria-label="成交量前 50">量</a><a class="rkbt" href="scan.html#ttop" aria-label="週轉率前 50">轉</a></div>')
rep("+`${f}億`+(t[3]!=null?`・🆕${t[3]}`:'');", "+`${f}億`;")
rep("成交值第 1 名；🆕＝前一個交易日不在前 50 的檔數`", "成交值第 1 名${t[3]!=null?'；新上榜 '+t[3]+' 檔':''}；右邊三顆＝成交值/成交量/週轉率前 50`")
rep('<span style="opacity:.5">v1118f</span>', '<span style="opacity:.5">v1120a</span>')
if not prod:
    s = s.replace('<title>', '<title>[beta] ', 1)
open('index.html' if prod else 'beta.html', 'w', encoding='utf-8').write(s)
print('ok')
