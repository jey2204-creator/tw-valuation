"""2026-11-15：首頁動能表「量比」欄在 iPhone 被切（世杰截圖：量比只剩一個字、列入後／投外／大戶／股東數字在螢幕外）
原因：① 集保在停牌換發那週給「1 位股東持有 100%」的佔位資料 → 信昌電 6173「股東 4週 +4495900.0%」把整欄撐到 134pt、整張表比卡片寬 46pt
        （後端 fetch_tdcc.py 已改：股東人數 ≤1 的週不拿來算，data/tdcc.json 已重算）
     ② 即使沒有壞資料，最右欄也只剛好夠寬 → 週／月／季三欄收窄當保險
改動：動能表加 class="mo"；週／月／季 12px、左右留白 4→2pt；股東 4 週變化 ≥100% 不帶小數、≥1000% 視為異常不顯示（前端保險）
用法：python3 patch_vrfit.py [prod]   （預設 index.html → beta.html）"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
def rep(s, a, b, n=1):
    assert s.count(a) == n, (s.count(a), a[:70])
    return s.replace(a, b)
s = open('index.html', encoding='utf-8').read()
s = rep(s, ".lst th[data-k]{cursor:pointer;user-select:none}",
        ".lst th[data-k]{cursor:pointer;user-select:none}\n"
        "/* 動能表：週／月／季收窄，把寬度留給最右「量比」欄（2026-11-15，iPhone 右欄被切） */\n"
        ".lst.mo th:nth-child(n+2):nth-child(-n+4),.lst.mo td:nth-child(n+2):nth-child(-n+4){padding-inline:2px}\n"
        ".lst.mo td:nth-child(n+2):nth-child(-n+4){font-size:12px;letter-spacing:-.2px}\n"
        ".lst.mo td:last-child,.lst.mo th:last-child{padding-right:2px}")
s = rep(s, "  if(md==='m')el.innerHTML=`<thead><tr>${th('cap','股票')}${th('m_w','週')}",
        "  el.classList.toggle('mo',md==='m');\n  if(md==='m')el.innerHTML=`<thead><tr>${th('cap','股票')}${th('m_w','週')}")
s = rep(s, "pm=tv(id,'pplm'),ck=chip(id),up=fire&&ck==='c';",
        "pm=(v=>v!=null&&Math.abs(v)>=1000?null:v)(tv(id,'pplm')),ck=chip(id),up=fire&&ck==='c';   /* ≥1000%＝集保佔位資料造成的假數字，不顯示 */")
s = rep(s, """4週 <span class="${sign(pm)}">${pp(pm,1)}%</span></span>`;""",
        """4週 <span class="${sign(pm)}">${pp(pm,Math.abs(pm)>=100?0:1)}%</span></span>`;""")
open('index.html' if prod else 'beta.html', 'w', encoding='utf-8').write(s)
print('ok →', 'index.html' if prod else 'beta.html')
