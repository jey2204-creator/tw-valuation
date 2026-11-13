"""2026-11-13：掃描頁漲幅鈕改成跟注意頁一樣的「日·週·月」（選中的加粗底線，連點循環），一眼看出可以切換
用法：python3 patch_scanchg.py [prod]   （預設 scan.html → beta_scan_chg.html）"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
s = open('scan.html', encoding='utf-8').read()
def rep(a, b):
    global s
    assert s.count(a) == 1, a[:60]
    s = s.replace(a, b)
rep(".sb button[aria-pressed=true]{background:var(--sel);color:var(--selfg);border-color:var(--sel);font-weight:700}",
    ".sb button[aria-pressed=true]{background:var(--sel);color:var(--selfg);border-color:var(--sel);font-weight:700}\n"
    ".sb button[data-k=chg]{flex:1.7 1 0}\n"
    ".sb button[data-k=chg] i{font-style:normal;font-weight:400;opacity:.45}\n"
    ".sb button[data-k=chg] i.on{font-weight:800;opacity:1;text-decoration:underline;text-underline-offset:2px}")
rep("cb.textContent={d:'日漲',w:'週漲',m:'月漲'}[CHGP];",
    "cb.innerHTML=[['d','日'],['w','週'],['m','月']].map(([k,n])=>`<i class=\"${k===CHGP?'on':''}\">${n}</i>`).join('·');")
open('scan.html' if prod else 'beta_scan_chg.html', 'w', encoding='utf-8').write(s)
