#!/usr/bin/env python3
"""2026-11-17 ⭐ 自選股：每檔顯示「加入 N 天」與「加入後漲跌」。
favMeta = {代號:[加入日 YYYYMMDD, 加入時的最新收盤, 該收盤的日期]}（localStorage，雲端同步多帶 fm 欄）。
顯示在：自選股主題頁（股名下方）、編輯自選頁（每列小字）。首頁最上面的自選表不顯示（維持兩行高度）。
用法：python3 patch_fdays.py → beta.html；python3 patch_fdays.py prod → index.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
s=open('index.html',encoding='utf-8').read()
assert "id=\"fQ\"" in s,'要先有 patch_favt.py＋patch_fadd.py'
def rep(old,new,n=1):
    global s
    assert s.count(old)==n,(s.count(old),old[:60]);s=s.replace(old,new)

# 1) favMeta：補登記／清掉已移除的；備註文字
rep("function favTheme(){const f=(store.get('fav')||[]).filter(x=>/^\\d{4,6}[A-Z]?$/.test(x));\n"
    "  return {id:FAVT,name:'⭐ 自選股',auto:true,favt:true,desc:'你的 ⭐ 自選',stocks:f.map(x=>[x,''])}}",
    "// ---- 自選加入紀錄（2026-11-17）：favMeta={代號:[加入日,加入時最新收盤,該收盤日期]}；沒紀錄的（舊自選）從第一次看到的那天起算 ----\n"
    "const twToday=()=>new Date(Date.now()+8*3600e3).toISOString().slice(0,10).replace(/-/g,'');\n"
    "function favMetaFix(){const f=store.get('fav')||[],m=store.get('favMeta')||{},o={};let ch=false;\n"
    "  f.forEach(id=>{if(m[id])o[id]=m[id];else if(typeof S!=='undefined'&&S&&S.d){o[id]=[twToday(),sv(id,'close')??null,S.pxAsof||null];ch=true}});\n"
    "  if(Object.keys(m).some(k=>!o[k])&&(typeof S!=='undefined'&&S&&S.d||!f.length))ch=true;else if(!ch)return m;\n"
    "  if(ch)store.set('favMeta',o);return o}\n"
    "function favNote(id,lead){const m=favMetaFix()[id];if(!m)return '';\n"
    "  const U=d=>Date.UTC(+d.slice(0,4),+d.slice(4,6)-1,+d.slice(6)),n=Math.round((U(twToday())-U(m[0]))/864e5),md=d=>`${+d.slice(4,6)}/${+d.slice(6)}`;\n"
    "  const c1=sv(id,'close'),px=S&&S.pxAsof,v=m[1]&&m[2]&&c1&&px&&px>m[2]?(c1/(m[1]*adjF(id,m[2],px))-1)*100:null;\n"
    "  const tip=`${md(m[0])} 加入自選`+(m[1]&&m[2]?`；漲跌＝${md(m[2])} 收盤 ${m[1]} → 最新收盤（已還原除權息）`:'');\n"
    "  return (lead?'・':'<span style=\"white-space:nowrap\">')+`<span class=\"dtip\" data-tip=\"${tip}\">${n<=0?'今天加入':lead?`加入 ${n} 天`:`${n}天`}</span>${v==null?'':` <span class=\"${sign(v)}\">${pct(v)}</span>`}`+(lead?'':'</span>')}\n"
    "function favTheme(){const f=(store.get('fav')||[]).filter(x=>/^\\d{4,6}[A-Z]?$/.test(x));\n"
    "  return {id:FAVT,name:'⭐ 自選股',auto:true,favt:true,desc:'你的 ⭐ 自選',stocks:f.map(x=>[x,favNote(x)])}}")

# 2) 主題頁：顯示備註列（緊湊模式也要）＋說明
rep("$('tTbl').dataset.note=t.auto&&!t.favt?'1':'';","$('tTbl').dataset.note=t.auto?'1':'';")
rep("按右上「✏️ 編輯」可搜尋加入、拖曳排序、移除；個股頁按 ☆ 也會進來。",
    "按右上「✏️ 編輯」可搜尋加入、拖曳排序、移除；個股頁按 ☆ 也會進來。股名下方「28天 +5.2%」＝加入自選幾天、加入後的漲跌（點一下看基準日）。")

# 2b) 還原係數（data/adj.json）是 ntLoad 才載的：進自選股主題時載一次再重畫
rep("  if(t.notice)$('tSum').innerHTML=`${ntHead(t.id)}",
    "  if(t.favt&&!NLOAD)ntLoad().then(()=>{if(decodeURIComponent(location.hash.slice(1))==='t/'+tid){applyCfg();showTheme(tid)}}).catch(()=>{});\n"
    "  if(t.notice)$('tSum').innerHTML=`${ntHead(t.id)}")

# 3) 編輯自選頁每列小字；✕ 之後復原要還原加入日
rep("'・市值 '+capTxt(cap(id)):''}</small>`:''}</a><button type=\"button\" class=\"ib\" data-del",
    "'・市值 '+capTxt(cap(id)):''}${favNote(id,1)}</small>`:`<small>${favNote(id,1).slice(1)}</small>`}</a><button type=\"button\" class=\"ib\" data-del")
rep("favUndo=[id,i];store.set('fav',f.filter(x=>x!==id));renderFav();",
    "favUndo=[id,i,(store.get('favMeta')||{})[id]];store.set('fav',f.filter(x=>x!==id));renderFav();")
rep("if(!f.includes(id))f.splice(i,0,id);store.set('fav',f);favUndo=null;",
    "if(!f.includes(id))f.splice(i,0,id);if(favUndo[2]){const m=store.get('favMeta')||{};m[id]=favUndo[2];store.set('favMeta',m)}store.set('fav',f);favUndo=null;")

# 4) 雲端同步多帶 fm（加入紀錄）；合併時同一檔取較早的加入日
rep("const local=()=>({fav:store.get('fav')||[],cfg:store.get('themeCfg')||null});",
    "const local=()=>({fav:store.get('fav')||[],cfg:store.get('themeCfg')||null,fm:store.get('favMeta')||{}});")
rep("if(code&&(k==='fav'||k==='themeCfg')){","if(code&&(k==='fav'||k==='themeCfg'||k==='favMeta')){")
rep("      raw('fav',fav);if(cfg)raw('themeCfg',cfg);",
    "      {const fm={...(R.fm||{})};Object.entries(L.fm||{}).forEach(([k,v])=>{if(!fm[k]||v[0]<fm[k][0])fm[k]=v});raw('favMeta',fm)}\n"
    "      raw('fav',fav);if(cfg)raw('themeCfg',cfg);")

rep('<span style="opacity:.5">v1117b</span>','<span style="opacity:.5">v1117c</span>')
if not prod:s=s.replace('<title>','<title>[beta] ',1)
open('index.html' if prod else 'beta.html','w',encoding='utf-8').write(s);print('ok')
