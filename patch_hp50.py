#!/usr/bin/env python3
"""2026-11-21 自動主題「💎 高價股前50」（首頁產業主題表接在 0050成份股後面＋掃描頁同名名單）。
世杰 11/21 22:30 選「照方案① 出 beta」：自動主題、收盤價由高到低前 50、上市櫃合併、不含 ETF、掃描頁預設榜序。
資料：data/hp50.json（fetch_summary.py 的 write_hp50，跟著「更新股票資料」每個交易日更新；
      新上榜的股票同一輪就會被 fetch_summary／chip／tdcc／debt 當成主題成份股一起抓）。
用法：python3 patch_hp50.py       → beta.html＋beta_scan_hp50.html
      python3 patch_hp50.py prod  → index.html＋scan.html
只能對舊版（index v1120i、scan v1120h）跑一次。
"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'


def patch(src, dst, edits, beta_extra=()):
    s = open(src, encoding='utf-8').read()
    for old, new in list(edits) + ([] if prod else list(beta_extra)):
        assert s.count(old) == 1, (src, s.count(old), old[:80])
        s = s.replace(old, new)
    if not prod:
        s = s.replace('<title>', '<title>[beta] ', 1)
    open(dst, 'w', encoding='utf-8').write(s)
    print('ok', dst)


HPT = ("// ---- 高價股前50 自動主題（2026-11-21）：data/hp50.json 由 fetch_summary.py 每個交易日盤後算；已依收盤價由高到低排好，備註＝🆕新上榜\n"
       "function hp50Theme(){if(!HP50||!(HP50.stocks||[]).length)return [];const a=HP50.asof||'',md=a?`${+a.slice(4,6)}/${+a.slice(6)}`:'',c=HP50.chg,nw=new Set(c&&c.d===a?c.in||[]:[]);\n"
       "  return [{id:'hp50',name:`💎 高價股前50${md?` (${md})`:''}`,auto:true,hp50:true,desc:'收盤價由高到低前 50 名 (上市櫃合併、不含 ETF)',stocks:HP50.stocks.map(([x])=>[x,nw.has(x)?'🆕新上榜':''])}]}\n")
HPSUM = ("  else if(t.hp50)$('tSum').innerHTML=`<span class=\"asof\">🔄 收盤日 ${HP50.asof.slice(0,4)}/${HP50.asof.slice(4,6)}/${HP50.asof.slice(6)}・每個交易日盤後自動更新，不可編輯、不佔自選額度</span><br>"
         "${t.desc}，第 50 名收盤 ${(HP50.stocks[HP50.stocks.length-1]||[])[1]??'—'} 元。<b>高價不代表貴</b>：股價高低跟股本大小有關，貴不貴請看本益比、PEG。名單每天跟著收盤換，中位數漲跌會受換股影響。"
         "${(()=>{const c=HP50.chg;if(!c||c.d!==HP50.asof||!c.prev)return '';const nm=a=>(a||[]).map(nameOf).join('、')||'無';"
         "return `<br>🔁 ${+c.d.slice(4,6)}/${+c.d.slice(6)} 對比 ${+c.prev.slice(4,6)}/${+c.prev.slice(6)}：新上榜 <strong>${nm(c.in)}</strong>・掉出 <strong>${nm(c.out)}</strong>`})()}<br>`+$('tSum').innerHTML;\n")

index_edits = [
    ("const AUTO_IDS=['e50','itop','ftop','btop','isell','natt','npre','ndis','nend','npost'];const FAVT='_fav';let E50=null;const lowT=id=>id===FAVT||id==='e50';",
     "const AUTO_IDS=['e50','hp50','itop','ftop','btop','isell','natt','npre','ndis','nend','npost'];const FAVT='_fav';let E50=null,HP50=null;const lowT=id=>id===FAVT||id==='e50'||id==='hp50';"),
    ("function autoThemes(){\n  if(!TOP||!TOP.lists)return e50Theme();",
     HPT + "function autoThemes(){\n  if(!TOP||!TOP.lists)return [...e50Theme(),...hp50Theme()];"),
    ("  return [...e50Theme(),...mk('itop','📈 投信買超前20','it',", "  return [...e50Theme(),...hp50Theme(),...mk('itop','📈 投信買超前20','it',"),
    ("  try{const r=await fetch('data/e50.json?t='+Math.floor(Date.now()/3e5));if(r.ok)E50=await r.json()}catch(e){}\n",
     "  try{const r=await fetch('data/e50.json?t='+Math.floor(Date.now()/3e5));if(r.ok)E50=await r.json()}catch(e){}\n"
     "  try{const r=await fetch('data/hp50.json?t='+Math.floor(Date.now()/3e5));if(r.ok)HP50=await r.json()}catch(e){}\n"),
    ("  else if(t.e50)$('tSum').innerHTML=", HPSUM + "  else if(t.e50)$('tSum').innerHTML="),
    # 手動排過順序的手機：hp50 不在 order 裡 → 接在 0050 後面（不跑到最上面）
    ("  if(!ids.includes(FAVT)){const k=ids.indexOf('leo')",
     "  if(c.order.length&&!c.order.includes('hp50')&&ids.includes('hp50')){ids.splice(ids.indexOf('hp50'),1);const k=ids.indexOf('e50');ids.splice(k<0?0:k+1,0,'hp50')}   // 2026-11-21：高價股前50 接在 0050 後面\n"
     "  if(!ids.includes(FAVT)){const k=ids.indexOf('leo')"),
    ('<span style="opacity:.5">v1120i</span>', '<span style="opacity:.5">v1121a</span>'),
]

scan_edits = [
    ("const AUTO_IDS=['e50','itop','ftop','btop','isell','natt','npre','ndis','nend','npost'];", "const AUTO_IDS=['e50','hp50','itop','ftop','btop','isell','natt','npre','ndis','nend','npost'];"),
    ("  const [E50,AJ0,L,T,TOP,NT0,PV]=await Promise.all([",
     "  const [HP50,E50,AJ0,L,T,TOP,NT0,PV]=await Promise.all([fetch('data/hp50.json?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null),"),
    ("  if(TOP&&TOP.hist){THIST=TOP.hist;",
     "  // 高價股前50（2026-11-21，與首頁同一份 data/hp50.json，已依收盤價排好）：當一般主題處理，接在 0050 後面，「榜序」＝股價由高到低\n"
     "  if(HP50&&(HP50.stocks||[]).length){const a=HP50.asof||'',th=T.themes||[],k=th.findIndex(t=>t.id==='e50');th.splice(k+1,0,{id:'hp50',name:`💎 高價股前50${a?` (${+a.slice(4,6)}/${+a.slice(6)})`:''}`,stocks:HP50.stocks.map(x=>[x[0],''])});T.themes=th}\n"
     "  if(TOP&&TOP.hist){THIST=TOP.hist;"),
    ("const A=THEMES.filter(t=>t.id==='_fav'||t.id==='e50'||", "const A=THEMES.filter(t=>t.id==='_fav'||t.id==='e50'||t.id==='hp50'||"),
    ("const isRk=isN||(sel.kind==='t'&&sel.id==='e50');   // 2026-11-20：0050 成份股也預設榜序",
     "const isRk=isN||(sel.kind==='t'&&(sel.id==='e50'||sel.id==='hp50'));   // 2026-11-20：0050 成份股也預設榜序；2026-11-21：高價股前50 也是"),
    ("v1120h</span>", "v1121a</span>"),
]

if __name__ == '__main__':
    patch('index.html', 'index.html' if prod else 'beta.html', index_edits,
          beta_extra=[("$('tScan').href='scan.html#'+encodeURIComponent(t.id);", "$('tScan').href='beta_scan_hp50.html?v=1#'+encodeURIComponent(t.id);")])
    patch('scan.html', 'scan.html' if prod else 'beta_scan_hp50.html', scan_edits)
