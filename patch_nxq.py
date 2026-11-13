"""2026-11-13：注意／處置頁名單跟 XQ 同步（方案③）
XQ 顯示「前一晚公布、今天盤中適用」的名單；本站原本預設顯示今晚剛公布的（明天才適用）。
→ 預設改成「目前適用」（前一份，完整快照 data/notice/prev.json），今晚新公布的放日期選單第 2 項「🆕 明日」，
  並標出差異：目前適用頁每張卡「明日續列／明日移出」＋一行「明日新增 N・續列 M・移出 K」；明日頁新進的標「🆕 新增」。
規則：最新名單日 >= 今天（台北日期）→ 它是「明日」；過了午夜就變成「目前適用」。測試可加 ?today=YYYYMMDD。
fetch_notice.py：名單日換日時把舊的 notice.json 存成 data/notice/prev.json。
用法：python3 patch_nxq.py [prod]   （預設 notice.html → beta_notice.html）"""
import sys, re
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
t = open('notice.html', encoding='utf-8').read()
def rep(a, b):
    global t
    assert t.count(a) == 1, (t.count(a), a[:70])
    t = t.replace(a, b)
def resub(pat, b):
    global t
    t, n = re.subn(pat, lambda m: b, t, count=1, flags=re.S)
    assert n == 1, pat[:50]

rep(".sb select.old{background:#fef3c7;border-color:#b45309;color:#7c2d12}",
    ".sb select.old{background:#fef3c7;border-color:#b45309;color:#7c2d12}\n.sb select.nx{background:#dbeafe;border-color:#1d4ed8;color:#1e3a8a}")
rep("const LST=k=>(DAY&&HR?HR[k]:D[k])||[];",
    "let PREV=null,CURD='',NEXTD='';   // CURD＝目前適用的名單日（同 XQ）；NEXTD＝今晚新公布、下個交易日才適用的名單日（沒有就是 ''）\n"
    "const TODAY=(()=>{const q=(location.search.match(/[?&]today=(\\d{8})/)||[])[1];if(q)return q;return new Date(Date.now()+8*3600e3).toISOString().slice(0,10).replace(/-/g,'')})();\n"
    "const SRC=()=>(DAY===D.asof?D:PREV&&DAY===PREV.asof?PREV:HR)||D;\n"
    "const LST=k=>SRC()[k]||[];\n"
    "const missMk=()=>{const m=D.mkAsof;if(!m)return '';const L=['上市','上櫃'].filter(k=>!m[k]||m[k]<D.asof);return L.length===1?L[0]:''};\n"
    "// 目前適用 vs 明日：同一頁籤的代號差異（上櫃還沒公布時，上櫃股不算移出，標待公布）\n"
    "function nxInfo(k){if(!NEXTD||!PREV||!['att','dis','pre'].includes(k))return null;const a=PREV[k]||[],b=D[k]||[],A=new Set(a.map(x=>x.c)),B=new Set(b.map(x=>x.c)),mm=k==='dis'?'':missMk();\n"
    "  return {A,B,mm,add:b.filter(x=>!A.has(x.c)).length,keep:a.filter(x=>B.has(x.c)).length,out:a.filter(x=>!B.has(x.c)&&x.m!==mm).length,wait:mm?a.filter(x=>!B.has(x.c)&&x.m===mm).length:0}}\n")
resub(r"async function setDay\(d\)\{.*?\n  tabCnt\(\);paint\(\)\}",
    "async function setDay(d){DAY=d||CURD;const sel=$('daySel');sel.value=DAY;sel.classList.toggle('nx',!!NEXTD&&DAY===NEXTD);sel.classList.toggle('old',DAY!==CURD&&DAY!==NEXTD);\n"
    "  if(DAY!==D.asof&&!(PREV&&DAY===PREV.asof)){if(!HIST){const [h,dh,ls]=await Promise.all(['data/notice/hist.json','data/notice/dis_hist.json','data/list.json'].map(u=>fetch(u+'?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null)));HIST=h||{};DH=dh||{};(ls||[]).forEach(r=>NAMES[r[0]]=[r[1],r[2]])}\n"
    "    HR=histAll(DAY);$('list').innerHTML='<div class=\"empty\">讀取中…</div>'}else HR=null;\n"
    "  await ensureK();tabCnt();paint()}")
resub(r"async function fillDays\(\)\{.*?\$\('daySel'\)\.onchange=e=>setDay\(e\.target\.value\)\}",
    "async function fillDays(){const sel=$('daySel');const head=()=>`<option value=\"${CURD}\">適用 ${md(CURD)}</option>`+(NEXTD?`<option value=\"${NEXTD}\">🆕明日 ${md(NEXTD)}</option>`:'');\n"
    "  sel.innerHTML=head();sel.value=DAY;sel.onchange=e=>setDay(e.target.value);\n"
    "  try{const r=await fetch('data/notice/hist.json?t='+Math.floor(Date.now()/3e5));if(!r.ok)return;HIST0=await r.json()}catch(e){return}\n"
    "  const ds=Object.keys(HIST0).filter(d=>d<CURD&&(HIST0[d].att||[]).length).sort().reverse().slice(0,40);\n"
    "  sel.innerHTML=head()+ds.map(d=>`<option value=\"${d}\">${md(d)}（${wkd(d)}）</option>`).join('');sel.value=DAY}")
rep("  const r=await fetch('data/notice.json?t='+Math.floor(Date.now()/3e5)).catch(()=>null);\n  D=r&&r.ok?await r.json():null;",
    "  const [r,rp]=await Promise.all(['data/notice.json','data/notice/prev.json'].map(u=>fetch(u+'?t='+Math.floor(Date.now()/3e5)).catch(()=>null)));\n"
    "  D=r&&r.ok?await r.json():null;try{PREV=rp&&rp.ok?await rp.json():null}catch(e){PREV=null}")
rep("  tabCnt();fillDays();\n",
    "  ntDemo(D);if(PREV&&!(PREV.asof&&PREV.asof<D.asof))PREV=null;\n"
    "  if(PREV&&D.asof>=TODAY){CURD=PREV.asof;NEXTD=D.asof}else{CURD=D.asof;NEXTD=''}\n"
    "  DAY=CURD;tabCnt();fillDays();\n"
    "  $('cnt').addEventListener('click',e=>{if(e.target.closest('#toNx')){e.preventDefault();setDay(NEXTD)}});\n")
rep("  const codes=[...new Set([...D.att,...D.dis,...D.pre,...(D.dend||[]),...(D.dpost||[])].map(x=>x.c))];\n  await Promise.all([...new Set(codes.map(c=>c.slice(0,2)))].map(g=>loadShard(g)));\n  codes.forEach(c=>K[c]=kinfo(c));\n  paint();",
    "  await ensureK();\n  paint();")
rep("ntDemo(D);const stl=DAY?`📅 ${md(DAY)} 名單・K 線與漲跌為最新（${md(D.asof)}）`:(TAB==='att'||TAB==='pre')?ntStale(D):'';",
    "const ni=nxInfo(TAB),stale=(DAY===D.asof&&(TAB==='att'||TAB==='pre'))?ntStale(D):'';let stl='',stc='#b45309';\n"
    "  if(stale)stl=stale;\n"
    "  else if(DAY===CURD){if(ni){stc='var(--accent)';stl=`🆕 明日新增 <b>${ni.add}</b>・續列 ${ni.keep}・移出 ${ni.out}${ni.wait?`・${ni.mm}待公布 ${ni.wait}`:''}　<a href=\"#\" id=\"toNx\" style=\"font-weight:800\">看明日 ›</a>`}}\n"
    "  else if(DAY===NEXTD){stc='var(--accent)';stl=`🆕 ${md(NEXTD)} 公布・下個交易日適用（XQ 明天才顯示）`}\n"
    "  else stl=`📅 ${md(DAY)} 名單・K 線與漲跌為最新（${md(D.asof)}）`;")
rep('<div style="color:#b45309;font-weight:600;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${stl}</div>',
    '<div style="color:${stc};font-weight:600;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${stl}</div>')
rep("檔・名單 ${md(DAY||D.asof)}・今日上漲 <b>${up}</b> 檔・點卡片展開原因・ⓘ 看說明`;",
    "檔・${md(DAY)} 公布${DAY===CURD&&NEXTD?'（今日適用）':''}・今日上漲 <b>${up}</b> 檔`;")
rep("    if(TAB==='att'){tags.push(`<span class=\"tg y\">連 <b>${x.streak||1}</b> 天</span>`);",
    "    if(ni&&DAY===CURD)tags.push(ni.B.has(x.c)?'<span class=\"tg g\">明日續列</span>':ni.mm&&x.m===ni.mm?'<span class=\"tg g\">明日待公布</span>':'<span class=\"tg a\">明日移出</span>');\n"
    "    if(ni&&DAY===NEXTD&&!ni.A.has(x.c))tags.push('<span class=\"tg r\">🆕 新增</span>');\n"
    "    if(TAB==='att'){tags.push(`<span class=\"tg y\">連 <b>${x.streak||1}</b> 天</span>`);")
rep("本頁不構成投資建議。 v1113d`;", "預設顯示「目前適用」的名單（前一晚公布、今天盤中適用，跟 XQ 同步）；當晚新公布的在日期選單「🆕 明日」。本頁不構成投資建議。 v1113e`;")
open('notice.html' if prod else 'beta_notice.html', 'w', encoding='utf-8').write(t)

p = open('fetch_notice.py', encoding='utf-8').read()
if 'prev.json' not in p:
    a = "OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(\",\", \":\")))\n"
    assert p.count(a) == 1
    p = p.replace(a, "# 2026-11-13：名單日換日時，把上一份完整名單留成 prev.json（注意頁預設顯示「目前適用」＝前一晚公布的，跟 XQ 同步）\n"
                     "_old = load(OUT, {})\n"
                     "if _old.get(\"asof\") and _old[\"asof\"] < ASOF:\n"
                     "    _old.pop(\"diag\", None)\n"
                     "    (NDIR / \"prev.json\").write_text(json.dumps(_old, ensure_ascii=False, separators=(\",\", \":\")))\n" + a)
    open('fetch_notice.py', 'w', encoding='utf-8').write(p)
