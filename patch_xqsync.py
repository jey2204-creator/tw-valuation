"""2026-11-13：首頁注意股主題表、掃描頁注意股按鈕也跟 XQ 同步（接續 patch_nxq.py 的注意／處置頁）
規則同注意頁：最新名單日 >= 今天（台北）且有 data/notice/prev.json → 預設用前一份（今日適用，同 XQ），最新那份是「🆕 明日」。
  首頁：五個自動主題用今日適用的名單；主題頁名單日那行寫「今日適用」，下面一行「🆕 明日新增 N・續列 M・移出 K　看明日 →」（連到注意頁）
  掃描頁：注意股等五顆名單按鈕與小卡「注N／快N／處N」標記用今日適用的名單；日期選單第 1 項＝適用、第 2 項＝🆕 明日
測試：網址加 ?today=YYYYMMDD
用法：python3 patch_xqsync.py [prod]   （預設 index.html→beta.html、scan.html→beta_scan_xq.html）"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
TODAYJS = "(()=>{const q=(location.search.match(/[?&]today=(\\d{8})/)||[])[1];if(q)return q;return new Date(Date.now()+8*3600e3).toISOString().slice(0,10).replace(/-/g,'')})()"
def rep(s, a, b):
    assert s.count(a) == 1, (s.count(a), a[:70])
    return s.replace(a, b)

# ---------------- index.html
s = open('index.html', encoding='utf-8').read()
s = rep(s, "let TOP=null,NT=null;", "let TOP=null,NT=null,NTN=null;   /* NT＝今日適用的名單（同 XQ）；NTN＝今晚新公布、明日才適用的（沒有就是 null） */")
s = rep(s, "if(r.ok)NT=ntDemo(await r.json())}catch(e){}",
        "if(r.ok)NT=ntDemo(await r.json())}catch(e){}\n"
        "  try{if(NT){const TD=" + TODAYJS + ";if(NT.asof>=TD){const rp=await fetch('data/notice/prev.json?t='+Math.floor(Date.now()/3e5));const pv=rp.ok?await rp.json():null;if(pv&&pv.asof&&pv.asof<NT.asof){NTN=NT;NT=pv}}}}catch(e){}")
s = rep(s, "<span class=\"asof\">🔄 名單日 ${NT.asof.slice(0,4)}/${NT.asof.slice(4,6)}/${NT.asof.slice(6)}・每個交易日 17:25 後自動更新，不可編輯、不佔自選額度</span><br>${(t.id==='natt'||t.id==='npre')&&ntStale(NT)?`<b style=\"color:#b45309\">${ntStale(NT)}</b><br>`:''}",
        "<span class=\"asof\">🔄 ${NTN?`今日適用（${+NT.asof.slice(4,6)}/${+NT.asof.slice(6)} 公布，同 XQ）`:`名單日 ${NT.asof.slice(0,4)}/${NT.asof.slice(4,6)}/${NT.asof.slice(6)}`}・每個交易日 17:25 後自動更新，不可編輯、不佔自選額度</span><br>${ntNxLine(t.id)}")
FN = '''function ntNxLine(id){const k={natt:'att',npre:'pre',ndis:'dis'}[id];if(!k)return '';
  if(!NTN){const w=(id==='natt'||id==='npre')?ntStale(NT):'';return w?`<b style="color:#b45309">${w}</b><br>`:''}
  const a=NT[k]||[],b=NTN[k]||[],A=new Set(a.map(x=>x.c)),B=new Set(b.map(x=>x.c)),m=NTN.mkAsof||{},L=['上市','上櫃'].filter(q=>!m[q]||m[q]<NTN.asof),mm=k!=='dis'&&NTN.mkAsof&&L.length===1?L[0]:'';
  const add=b.filter(x=>!A.has(x.c)).length,keep=a.filter(x=>B.has(x.c)).length,out=a.filter(x=>!B.has(x.c)&&x.m!==mm).length,wait=mm?a.filter(x=>!B.has(x.c)&&x.m===mm).length:0;
  return `<b style="color:var(--accent)">🆕 明日新增 ${add}・續列 ${keep}・移出 ${out}${wait?`・${mm}待公布 ${wait}`:''}</b>　<a href="notice.html#${k}">看明日 →</a><br>`}
'''
j = s.rfind('<script>', 0, s.index("function noticeThemes")) + len('<script>')
s = s[:j] + '\n' + FN + s[j:]
open('index.html' if prod else 'beta.html', 'w', encoding='utf-8').write(s)

# ---------------- scan.html
c = open('scan.html', encoding='utf-8').read()
c = rep(c, "NOTICE=null,NMAP={},", "NOTICE=null,NXT=null,NDAYS=[],NMAP={},")
c = rep(c, "const [L,T,TOP,NT]=await Promise.all([", "const [L,T,TOP,NT0,PV]=await Promise.all([")
c = rep(c, "fetch('data/notice.json?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null)]);\n  NOTICE=NT;NMAP={};",
        "fetch('data/notice.json?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null),fetch('data/notice/prev.json?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null)]);\n"
        "  // 2026-11-13：跟 XQ 同步——最新名單日 >= 今天且有前一份快照 → NT＝前一份（今日適用），NXT＝最新那份（🆕 明日）\n"
        "  let NT=NT0;NXT=null;{const TD=" + TODAYJS + ";if(NT0&&PV&&PV.asof&&PV.asof<NT0.asof&&NT0.asof>=TD){NXT=NT0;NT=PV}}\n"
        "  NOTICE=NT;NMAP={};")
c = rep(c, "HDAYS=Object.keys(HIST).filter(d=>HIST[d].att&&HIST[d].att.length).sort().reverse().slice(0,30);",
        "HDAYS=Object.keys(HIST).filter(d=>HIST[d].att&&HIST[d].att.length).sort().reverse().slice(0,30);NDAYS=NXT?[NXT.asof,NT.asof,...HDAYS.filter(d=>d<NT.asof)]:HDAYS;")
c = rep(c, "DAYS=isT?TDAYS:HDAYS,isN=", "DAYS=isT?TDAYS:NDAYS,D0=(!isT&&NXT?NOTICE.asof:DAYS[0])||'',isN=")   # D0＝預設那天（適用）；選單順序是 明日→適用→更早
c = rep(c, "NDATE=DAYS[0]||'';", "NDATE=D0;")
c = rep(c, "const past=isN&&NDATE&&DAYS[0]&&NDATE!==DAYS[0];", "const past=isN&&NDATE&&D0&&NDATE!==D0;")
c = rep(c, "`<option value=\"${d}\">📅 ${md(d)} 名單・", "`<option value=\"${d}\">${!isT&&NXT&&d===NXT.asof?'🆕 明日':!isT&&NXT&&d===D0?'✅ 適用':'📅'} ${md(d)} 名單・")
c = rep(c, "名單・${d===DAYS[0]?(isT?", "名單・${d===D0?(isT?")
open('scan.html' if prod else 'beta_scan_xq.html', 'w', encoding='utf-8').write(c)
