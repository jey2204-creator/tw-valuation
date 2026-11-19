#!/usr/bin/env python3
"""2026-11-20 自動主題「🏆 0050成份股」（首頁產業主題表第 1 位＋掃描頁同名名單）。
世杰選：照 ① 出 beta、排第 1 位、依市值排序、只做 0050。
資料：data/e50.json（fetch_e50.py，e50.yml 每個交易日跟在「更新股票資料」後面跑；成份股已依市值排好）。
用法：python3 patch_e50.py       → beta.html＋beta_scan_e50.html
      python3 patch_e50.py prod  → index.html＋scan.html
只能對舊版（index v1120a、scan v1119a）跑一次。
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


E50T = ("function e50Theme(){if(!E50||!(E50.stocks||[]).length)return [];const a=E50.asof||'',md=a?`${+a.slice(4,6)}/${+a.slice(6)}`:'';\n"
        "  return [{id:'e50',name:`🏆 0050成份股${md?` (${md})`:''}`,auto:true,e50:true,desc:'元大台灣50 (0050) 目前持有的成份股，依市值由大到小排序',stocks:E50.stocks.map(([c,w])=>[c,w!=null?`權重${(+w).toFixed(2)}%`:''])}]}\n")
E50SUM = ("  else if(t.e50)$('tSum').innerHTML=`<span class=\"asof\">🔄 持股日 ${E50.asof.slice(0,4)}/${E50.asof.slice(4,6)}/${E50.asof.slice(6)}・盤後自動更新，換股會自動跟上</span><br>"
          "${t.desc}；每年 3/6/9/12 月換股。股名下方「權重59.34%」＝占 0050 淨值的比重；台積電一檔就占約六成，所以這裡的中位數不代表 0050 本身的表現，比較適合拿來一次掃大型股。"
          "${(()=>{const c=E50.chg;if(!c||!c.d)return '';const U=d=>Date.UTC(+d.slice(0,4),+d.slice(4,6)-1,+d.slice(6));if((U(E50.asof)-U(c.d))/864e5>45)return '';"
          "const nm=a=>(a||[]).map(nameOf).join('、')||'無';return `<br>🔁 最近換股 ${+c.d.slice(4,6)}/${+c.d.slice(6)}：納入 <strong>${nm(c.in)}</strong>・剔除 <strong>${nm(c.out)}</strong>`})()}<br>`+$('tSum').innerHTML;\n")

index_edits = [
    # 自動主題清單：e50 排最前面
    ("const AUTO_IDS=['itop','ftop','btop','natt','npre','ndis','nend','npost'];const FAVT='_fav';",
     "const AUTO_IDS=['e50','itop','ftop','btop','natt','npre','ndis','nend','npost'];const FAVT='_fav';let E50=null;const lowT=id=>id===FAVT||id==='e50';   /* lowT＝找「這檔屬於哪個主題」時最後才考慮的主題 */"),
    ("function autoThemes(){\n  if(!TOP||!TOP.lists)return [];",
     "// ---- 0050 成份股自動主題（2026-11-20）：data/e50.json 由 e50.yml 每個交易日抓；成份股已依市值排好，備註＝權重\n"
     + E50T + "function autoThemes(){\n  if(!TOP||!TOP.lists)return e50Theme();"),
    ("  return [...mk('itop','📈 投信買超前20','it',", "  return [...e50Theme(),...mk('itop','📈 投信買超前20','it',"),
    ("  try{const r=await fetch('data/itrust_top.json?t='+Date.now());if(r.ok)TOP=await r.json()}catch(e){}\n",
     "  try{const r=await fetch('data/itrust_top.json?t='+Date.now());if(r.ok)TOP=await r.json()}catch(e){}\n"
     "  try{const r=await fetch('data/e50.json?t='+Math.floor(Date.now()/3e5));if(r.ok)E50=await r.json()}catch(e){}\n"),
    # 主題頁說明
    ("  else if(t.auto)$('tSum').innerHTML=`<span class=\"asof\">🔄 名單日 ${TOP.asof.slice(0,4)}",
     E50SUM + "  else if(t.auto)$('tSum').innerHTML=`<span class=\"asof\">🔄 名單日 ${TOP.asof.slice(0,4)}"),
    # 編輯主題頁的小字
    ("${t.favt?'・跟著 ⭐ 自選':t.auto?'・每天自動換名單':''}", "${t.favt?'・跟著 ⭐ 自選':t.e50?'・換股時自動更新':t.auto?'・每天自動換名單':''}"),
    # 個股頁「← 主題」、薪資／AI 名次：優先用產業主題，0050 跟自選一樣只當備援
    ("const mine=THEMES.filter(t=>t.stocks.some(x=>x[0]===id)),t=mine.find(x=>x.id===last)||mine.find(x=>x.id!==FAVT)||mine[0];return t?'t/'+t.id:''}",
     "const mine=THEMES.filter(t=>t.stocks.some(x=>x[0]===id)),t=mine.find(x=>x.id===last)||mine.find(x=>!lowT(x.id))||mine.find(x=>x.id!==FAVT)||mine[0];return t?'t/'+t.id:''}"),
    ("  const bt=mine.find(t=>t.id===last)||mine.find(t=>t.id!==FAVT)||mine[0];",
     "  const bt=mine.find(t=>t.id===last)||mine.find(t=>!lowT(t.id))||mine.find(t=>t.id!==FAVT)||mine[0];"),
    # 首頁 🔥 表的主題名
    ("(THEMES.find(t=>t.id!==FAVT&&t.stocks.some(x=>x[0]===id))||{name:'⭐ 自選'}).name",
     "(THEMES.find(t=>!lowT(t.id)&&t.stocks.some(x=>x[0]===id))||THEMES.find(t=>t.id!==FAVT&&t.stocks.some(x=>x[0]===id))||{name:'⭐ 自選'}).name"),
    ('<span style="opacity:.5">v1120a</span>', '<span style="opacity:.5">v1120b</span>'),
]
RANK_OLD = "const t=mine.find(x=>x.id===last)||mine.find(x=>x.id!==FAVT)||mine[0];\n"
RANK_NEW = "const t=mine.find(x=>x.id===last)||mine.find(x=>!lowT(x.id))||mine.find(x=>x.id!==FAVT)||mine[0];\n"

scan_edits = [
    ("const AUTO_IDS=['itop','ftop','btop','natt','npre','ndis','nend','npost'];", "const AUTO_IDS=['e50','itop','ftop','btop','natt','npre','ndis','nend','npost'];"),
    ("  const [AJ0,L,T,TOP,NT0,PV]=await Promise.all([", "  const [E50,AJ0,L,T,TOP,NT0,PV]=await Promise.all([fetch('data/e50.json?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null),"),
    ("  if(TOP&&TOP.hist){THIST=TOP.hist;",
     "  // 0050 成份股（2026-11-20，與首頁同一份 data/e50.json，已依市值排好）：當一般主題處理，「榜序」＝市值由大到小\n"
     "  if(E50&&(E50.stocks||[]).length){const a=E50.asof||'';T.themes=[{id:'e50',name:`🏆 0050成份股${a?` (${+a.slice(4,6)}/${+a.slice(6)})`:''}`,stocks:E50.stocks.map(x=>[x[0],''])},...(T.themes||[])]}\n"
     "  if(TOP&&TOP.hist){THIST=TOP.hist;"),
    # 「全部▾」面板：放在「⭐ 自選・訊號籌碼」那一組
    ("const A=THEMES.filter(t=>t.id==='_fav'||t.id==='fire'||", "const A=THEMES.filter(t=>t.id==='_fav'||t.id==='e50'||t.id==='fire'||"),
    ("v1119a", "v1120b"),
]

if __name__ == '__main__':
    s0 = open('index.html', encoding='utf-8').read()
    assert s0.count(RANK_OLD) == 2, s0.count(RANK_OLD)          # 薪資名次、AI 名次兩處寫法相同
    open('index.html.tmp', 'w', encoding='utf-8').write(s0.replace(RANK_OLD, RANK_NEW))
    patch('index.html.tmp', 'index.html' if prod else 'beta.html', index_edits,
          beta_extra=[("$('tScan').href='scan.html#'+encodeURIComponent(t.id);", "$('tScan').href='beta_scan_e50.html?v=1#'+encodeURIComponent(t.id);")])
    import os
    os.remove('index.html.tmp')
    patch('scan.html', 'scan.html' if prod else 'beta_scan_e50.html', scan_edits)
