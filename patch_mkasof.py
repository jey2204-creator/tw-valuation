"""2026-11-12：注意股名單「上市／上櫃各自的名單日」——櫃買開放資料常比證交所晚更新，
名單日已換成今天但上櫃還停在前一天時，頁面標出「目前只有上市」。
fetch_notice.py → notice.json 多 mkAsof={"上市":YYYYMMDD,"上櫃":YYYYMMDD}
用法：python3 patch_mkasof.py            （index.html→beta.html、notice.html→beta_notice.html，fetch_notice.py 就地改）
      python3 patch_mkasof.py prod       （直接改 index.html／notice.html）"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
FN = '''function ntStale(N){const a=N&&N.asof,m=N&&N.mkAsof;if(!a||!m)return '';const f=d=>(+d.slice(4,6))+'/'+(+d.slice(6));const L=['上市','上櫃'].filter(k=>!m[k]||m[k]<a);if(L.length!==1)return '';const k=L[0];return `⚠️ ${k}名單還停在 ${m[k]?f(m[k]):'前一日'}（${k==='上櫃'?'櫃買':'證交所'}尚未公布 ${f(a)}），目前只有${k==='上櫃'?'上市':'上櫃'}，稍晚自動補上`}
function ntDemo(N){if(N&&N.asof&&/[?&]stale=1/.test(location.search)){const d=new Date(+N.asof.slice(0,4),+N.asof.slice(4,6)-1,+N.asof.slice(6)-1);N.mkAsof={'上市':N.asof,'上櫃':''+d.getFullYear()+String(d.getMonth()+1).padStart(2,'0')+String(d.getDate()).padStart(2,'0')}}return N}
'''
def rep(s, a, b):
    assert s.count(a) == 1, a[:60]
    return s.replace(a, b)

if not prod or 'mkAsof' not in open('fetch_notice.py', encoding='utf-8').read():
    p = open('fetch_notice.py', encoding='utf-8').read()
    p = rep(p, '''att = {v["c"]: v for v in att if (v["d"] or ASOF) == ASOF}''',
            '''MK_ASOF = {}                                                                     # 2026-11-12：上市／上櫃各自最新的注意名單日（櫃買常晚更新）
for v in att:
    if v.get("d"):
        MK_ASOF[v["m"]] = max(MK_ASOF.get(v["m"], ""), v["d"])
att = {v["c"]: v for v in att if (v["d"] or ASOF) == ASOF}''')
    p = rep(p, '''out = {"updated": NOW.strftime("%Y-%m-%dT%H:%MZ"), "asof": ASOF,''',
            '''out = {"updated": NOW.strftime("%Y-%m-%dT%H:%MZ"), "asof": ASOF, "mkAsof": MK_ASOF,''')
    open('fetch_notice.py', 'w', encoding='utf-8').write(p)

s = open('index.html', encoding='utf-8').read()
s = rep(s, "if(r.ok)NT=await r.json()}catch(e){}", "if(r.ok)NT=ntDemo(await r.json())}catch(e){}")
s = rep(s, "不可編輯、不佔自選額度</span><br>${t.desc}。<b>列注意不是買進",
        "不可編輯、不佔自選額度</span><br>${(t.id==='natt'||t.id==='npre')&&ntStale(NT)?`<b style=\"color:#b45309\">${ntStale(NT)}</b><br>`:''}${t.desc}。<b>列注意不是買進")
j = s.rfind('<script>', 0, s.index("function noticeThemes")) + len('<script>')
s = s[:j] + '\n' + FN + s[j:]
open('index.html' if prod else 'beta.html', 'w', encoding='utf-8').write(s)

t = open('notice.html', encoding='utf-8').read()
a = "$('cnt').innerHTML=`<b>${R.length}</b>／${all} 檔・名單"
t = rep(t, a, "ntDemo(D);const stl=(TAB==='att'||TAB==='pre')?ntStale(D):'';\n  $('cnt').innerHTML=(stl?`<div style=\"color:#b45309;font-weight:600;margin-bottom:2px\">${stl}</div>`:'')+`<b>${R.length}</b>／${all} 檔・名單")
j = t.rfind('<script>', 0, t.index("TAB==='dis'")) + len('<script>')
t = t[:j] + '\n' + FN + t[j:]
open('notice.html' if prod else 'beta_notice.html', 'w', encoding='utf-8').write(t)
