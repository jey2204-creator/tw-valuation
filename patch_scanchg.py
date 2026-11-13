"""2026-11-13：掃描頁漲幅鈕改成跟注意頁一樣的「日·週·月」（選中的加粗底線，連點循環），一眼看出可以切換；月漲幅改日曆日
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
# 月漲幅改日曆日（上個月同一天，休市取前一交易日）——跟首頁動能、注意頁、XQ 一致；欄位名仍叫 chg20
rep("chg20:n>20&&bars[n-21].c?last.c/bars[n-21].c-1:null,", "chg20:calM(bars),")
rep("const CHGK=()=>CHGP==='w'?'chg5':CHGP==='m'?'chg20':'chg';",
    "const CHGK=()=>CHGP==='w'?'chg5':CHGP==='m'?'chg20':'chg';\n"
    "function calM(bars){const n=bars.length;if(n<2)return null;const last=bars[n-1],ld=String(last.d),tm=new Date(+ld.slice(0,4),+ld.slice(4,6)-2,1),eom=new Date(tm.getFullYear(),tm.getMonth()+1,0).getDate(),tg=''+tm.getFullYear()+String(tm.getMonth()+1).padStart(2,'0')+String(Math.min(+ld.slice(6),eom)).padStart(2,'0');\n"
    "  let bi=-1;for(let j=0;j<n;j++){if(String(bars[j].d)<=tg)bi=j}return bi>=0&&bars[bi].c?last.c/bars[bi].c-1:null}")
rep("cb.title='連點切換 日→週→月漲幅';", "cb.title='連點切換 日→週→月漲幅（週＝5 個交易日前、月＝上個月同一天）';")
open('scan.html' if prod else 'beta_scan_chg.html', 'w', encoding='utf-8').write(s)
