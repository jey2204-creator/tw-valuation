"""2026-11-15：首頁主力訊號區加「📊 統計」入口 → fstats.html（上榜後 N 日報酬統計）
最新那天：控制列日期選單旁一顆「📊 統計」；頁尾說明最前面也放一個連結（舊日期控制列放不下時用）
用法：python3 patch_fslink.py   （直接改 index.html）"""
s = open('index.html', encoding='utf-8').read()
assert 'fstats.html' not in s
def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)
rep("+(isNow?'':`<button type=\"button\" id=\"fhMode\" class=\"ntm\">",
    "+(isNow?'<a class=\"ntm\" href=\"fstats.html\" style=\"text-decoration:none\">📊 統計</a>':`<button type=\"button\" id=\"fhMode\" class=\"ntm\">")
rep("是「有資金在推」的訊號，不是買進訊號，要搭配估值位階看。`\n    +(hasH?",
    "是「有資金在推」的訊號，不是買進訊號，要搭配估值位階看。<a href=\"fstats.html\">📊 上榜後勝率統計 ›</a>`\n    +(hasH?")
rep("<span style=\"opacity:.5\">v1115b</span>", "<span style=\"opacity:.5\">v1115c</span>")
open('index.html', 'w', encoding='utf-8').write(s)
print('ok')
