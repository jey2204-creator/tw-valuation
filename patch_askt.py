#!/usr/bin/env python3
"""首頁／主題頁的產業主題成份股表：點「收盤」欄下面那行漲跌幅 → 開 Google AI 模式問漲跌原因（沿用 patch_ask.py 的 askUrl）。
漲跌幅加虛線底線＋🔍 小圖示表示可點；點同一列其他地方照舊進個股頁。日期用 summary 的收盤日 S.pxAsof。
用法：python3 patch_askt.py index.html beta.html   （index.html 要先套過 patch_ask.py）
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
n0 = len(s)
def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (s.count(old), old[:80])
    s = s.replace(old, new)

assert 'function askUrl(' in s
rep('<span class="sub ${sign(ch)}">${pct(ch,2)}</span></td>',
    '<span class="sub askc ${sign(ch)}" role="link" aria-label="問 Google AI 漲跌原因">${pct(ch,2)}${ch==null?\'\':\'<i>🔍</i>\'}</span></td>', 2)
rep('.lst .sub{display:block;font-size:11px;color:var(--muted)}',
    '.lst .sub{display:block;font-size:11px;color:var(--muted)}\n'
    '.lst .sub.askc{cursor:pointer;text-decoration:underline dotted;text-underline-offset:2px;padding:3px 0 3px 6px;margin:-3px 0 -3px -6px;-webkit-tap-highlight-color:transparent;white-space:nowrap}\n'
    '.lst .sub.askc i{font-style:normal;font-size:9px;margin-left:1px;opacity:.75;text-decoration:none;display:inline-block}\n'
    '.lst .sub.askc:active{opacity:.5}')
rep("    const r=e.target.closest('tr[data-id]');if(r)location.hash=r.dataset.id};\n}",
    "    const r=e.target.closest('tr[data-id]');\n"
    "    const ak=e.target.closest('.askc');if(ak&&r){const id=r.dataset.id,ch=sv(id,'chg');if(ch!=null){e.preventDefault();const d=S&&S.pxAsof?+S.pxAsof.slice(4,6)+'/'+ +S.pxAsof.slice(6,8):'';window.open(askUrl(nameOf(id),id,ch,d),'_blank','noopener');return}}\n"
    "    if(r)location.hash=r.dataset.id};\n}")
open(dst, 'w', encoding='utf-8').write(s)
print('ok', n0, '->', len(s))
