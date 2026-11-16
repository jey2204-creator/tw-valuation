#!/usr/bin/env python3
"""2026-11-17 主題清單加自動主題「⭐ 自選股」（id _fav，與 scan.html 的自選同 id）：
成份股＝⭐ 自選（localStorage fav），預設排在 🛰️ 低軌衛星上方；不可在主題編輯頁改，
主題頁右上「✏️ 編輯」連到 #f（編輯自選）。個股頁的「← 主題」與同業名次仍優先用產業主題。
用法：python3 patch_favt.py → beta.html；python3 patch_favt.py prod → index.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
s=open('index.html',encoding='utf-8').read()
def rep(old,new,n=1):
    global s
    assert s.count(old)==n,(s.count(old),old[:60]);s=s.replace(old,new)

# 1) _fav 視為自動主題（不可編輯、不吃 themeCfg.themes），但不放進 AUTO_IDS（不強制排最上面）
rep("const isAuto=id=>AUTO_IDS.includes(id);",
    "const FAVT='_fav';const isAuto=id=>AUTO_IDS.includes(id)||id===FAVT;\n"
    "function favTheme(){const f=(store.get('fav')||[]).filter(x=>/^\\d{4,6}[A-Z]?$/.test(x));\n"
    "  return {id:FAVT,name:'⭐ 自選股',auto:true,favt:true,desc:'你的 ⭐ 自選',stocks:f.map(x=>[x,''])}}")

# 2) allThemes：加入 _fav；沒被手動排序過時插在低軌衛星上方（沒有 leo 就放在自動主題之後）
rep("const c=cfgGet(),bm=Object.fromEntries(BASE.map(t=>[t.id,t]));",
    "const c=cfgGet(),bm=Object.fromEntries([...BASE,favTheme()].map(t=>[t.id,t]));")
rep("a.indexOf(v)===i&&(bm[v]||c.themes[v]));   // 自動主題沒被手動排序過時放最上面",
    "a.indexOf(v)===i&&(bm[v]||c.themes[v]));   // 自動主題沒被手動排序過時放最上面\n"
    "  if(!ids.includes(FAVT)){const k=ids.indexOf('leo'),j=k>=0?k:ids.findIndex(i=>!AUTO_IDS.includes(i));ids.splice(j<0?ids.length:j,0,FAVT)}   // ⭐ 自選股：預設在低軌衛星上方")

# 3) 主題頁：編輯鈕連到 #f、不顯示角色備註列、說明文字
rep("$('tEdit').href='#e/'+t.id;$('tEdit').hidden=!!t.auto;",
    "$('tEdit').href=t.favt?'#f':'#e/'+t.id;$('tEdit').hidden=!!t.auto&&!t.favt;")
rep("$('tTbl').dataset.note=t.auto?'1':'';",
    "$('tTbl').dataset.note=t.auto&&!t.favt?'1':'';")
rep("  else if(t.auto)$('tSum').innerHTML=`<span class=\"asof\">🔄 名單日",
    "  else if(t.favt)$('tSum').innerHTML=`<span class=\"asof\">⭐ 自選 ${ids.length}／30 檔・${store.get('syncCode')?'已開雲端同步':'只存在這支手機'}</span><br>${ids.length?'在個股頁按「☆ 加入自選」就會進來；按右上「✏️ 編輯」可拖曳排序、移除。':'還沒有自選：搜尋股票進個股頁，按「☆ 加入自選」就會出現在這裡。'}<br>`+(ids.length?$('tSum').innerHTML:'');\n"
    "  else if(t.auto)$('tSum').innerHTML=`<span class=\"asof\">🔄 名單日")

# 3b) 自選不是同一個產業：不標 👑 龍頭、不排 #1～#3 市值名次
rep("RANK=ranks(ids);\n  const lead=(()=>{","RANK=t.favt?null:ranks(ids);\n  const lead=t.favt?'':(()=>{")

# 4) 編輯主題清單的小字
rep("${t.auto?'・每天自動換名單':''}","${t.favt?'・跟著 ⭐ 自選':t.auto?'・每天自動換名單':''}")

# 5) 自選一變動就重算主題清單
rep("  const h=decodeURIComponent(location.hash.slice(1));bkTrack(h);\n  const show=",
    "  const h=decodeURIComponent(location.hash.slice(1));bkTrack(h);try{applyCfg()}catch(e){}\n  const show=")
rep("else f=[...f,id];store.set('fav',f);stockExtras(id)});",
    "else f=[...f,id];store.set('fav',f);applyCfg();stockExtras(id)});")

# 6) 個股頁的返回主題／主題內名次／🔥 表的主題名：優先產業主題，自選股只當備援
rep("mine.find(x=>x.id===last)||mine[0]","mine.find(x=>x.id===last)||mine.find(x=>x.id!==FAVT)||mine[0]",3)
rep("mine.find(t=>t.id===last)||mine[0]","mine.find(t=>t.id===last)||mine.find(t=>t.id!==FAVT)||mine[0]")
rep("(THEMES.find(t=>t.stocks.some(x=>x[0]===id))||{name:'⭐ 自選'}).name",
    "(THEMES.find(t=>t.id!==FAVT&&t.stocks.some(x=>x[0]===id))||{name:'⭐ 自選'}).name")

rep('<span style="opacity:.5">v1115o</span>','<span style="opacity:.5">v1117a</span>')
if not prod:s=s.replace('<title>','<title>[beta] ',1)
open('index.html' if prod else 'beta.html','w',encoding='utf-8').write(s);print('ok')
