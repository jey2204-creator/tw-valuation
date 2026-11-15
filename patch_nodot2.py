#!/usr/bin/env python3
"""注意頁「漲幅 日 週 月」、首頁「數字 最新 當日」（注意股主題表、🔥 主力訊號）也改成沒有「·」＋點哪個字就選哪個（2026-11-15）
跟掃描頁 patch_volcyc.py／patch_nodot.py 同一套樣式。用法：python3 patch_nodot2.py   （直接改 notice.html、index.html）
"""
def patch(path, reps):
    s = open(path, encoding='utf-8').read()
    for old, new in reps:
        assert s.count(old) == 1, (path, s.count(old), old[:80])
        s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)

patch('notice.html', [
    ("`<i class=\"${k===CHGP?'on':''}\">${n}</i>`).join('·');$('chgBtn').title='連點切換 日→週→月';",
     "`<i data-p=\"${k}\" class=\"${k===CHGP?'on':''}\">${n}</i>`).join('');$('chgBtn').title='點字切換 日／週／月漲幅';"),
    ("else if(b.dataset.s){if(b.dataset.s==='chg'&&SORT==='chg')CHGP=CHGP==='d'?'w':CHGP==='w'?'m':'d';SORT=b.dataset.s}",
     "else if(b.dataset.s){if(b.dataset.s==='chg'){const t=e.target.closest('i[data-p]');if(t)CHGP=t.dataset.p;else if(SORT==='chg')CHGP=CHGP==='d'?'w':CHGP==='w'?'m':'d'}SORT=b.dataset.s}"),
    ("#chgBtn i{font-style:normal;font-weight:400;opacity:.45;padding:0 1px}", "#chgBtn i{font-style:normal;font-weight:400;opacity:.45;padding:3px 3px}"),
    ("v1115a", "v1115b"),
])
patch('index.html', [
    ("<i class=\"${NMODE==='now'?'on':''}\">最新</i>·<i class=\"${NMODE==='day'?'on':''}\">",
     "<i data-p=\"now\" class=\"${NMODE==='now'?'on':''}\">最新</i><i data-p=\"day\" class=\"${NMODE==='day'?'on':''}\">"),
    ("<i class=\"${HMODE==='now'?'on':''}\">最新</i>·<i class=\"${HMODE==='day'?'on':''}\">",
     "<i data-p=\"now\" class=\"${HMODE==='now'?'on':''}\">最新</i><i data-p=\"day\" class=\"${HMODE==='day'?'on':''}\">"),
    ("if(b.id==='ntMode')NMODE=NMODE==='day'?'now':'day';",
     "if(b.id==='ntMode'){const t=e.target.closest('i[data-p]');NMODE=t?t.dataset.p:NMODE==='day'?'now':'day'}"),
    ("e.preventDefault();HMODE=HMODE==='day'?'now':'day';hotPaint()",
     "e.preventDefault();{const t=e.target.closest('i[data-p]');HMODE=t?t.dataset.p:HMODE==='day'?'now':'day'}hotPaint()"),
    (".ntm i{font-style:normal;opacity:.45}", ".ntm i{font-style:normal;opacity:.45;padding:3px 3px}"),
    ("v1115i", "v1115j"),
])
print('ok')
