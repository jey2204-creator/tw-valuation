"""2026-11-13：注意／處置頁加日期切換（看前幾天的名單，方便跟 XQ 對）＋漲幅鈕連點循環 日→週→月
歷史名單由 data/notice/hist.json（每日注意代號）＋ dis_hist.json（處置起迄）回推，跟掃描頁日期選單同一套邏輯；
K 線、漲跌、量比永遠是最新交易日（跟掃描頁一致）。
用法：python3 patch_nday.py [prod]   （預設 notice.html → beta_notice.html；prod 直接改 notice.html）"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
t = open('notice.html', encoding='utf-8').read()
def rep(a, b, n=1):
    global t
    assert t.count(a) == n, (t.count(a), a[:70])
    t = t.replace(a, b)

# ---- 版面：第 1 行＝日期＋市場，第 2 行＝排序（不橫向捲動）
rep('.sb{display:flex;gap:4px;align-items:center;font-size:12px;color:var(--muted);padding:4px 8px 0;overflow-x:auto;scrollbar-width:none}',
    '.sb{display:flex;flex-wrap:wrap;gap:4px;align-items:center;font-size:12px;color:var(--muted);padding:4px 8px 0}\n'
    '.sb .brk{flex-basis:100%;height:0}\n'
    '.sb select{flex:none;height:26px;padding:0 4px;border-radius:13px;border:1px solid var(--accent);background:var(--card);color:var(--fg);font-size:16px;font-weight:500;max-width:40vw}\n'
    '.sb select.old{background:#fef3c7;border-color:#b45309;color:#7c2d12}\n'
    '.sb #chgBtn i{font-style:normal;font-weight:400;opacity:.45;padding:0 1px}\n'
    '.sb #chgBtn i.on{font-weight:800;opacity:1;text-decoration:underline;text-underline-offset:2px}')
rep('''  <span class="lab">市場</span><button data-m="" aria-pressed="true">全部</button><button data-m="上市">上市</button><button data-m="上櫃">上櫃</button>
  <span class="sep"></span>
  <span class="lab">排序</span>''',
    '''  <select id="daySel" aria-label="名單日期"><option value="">最新</option></select>
  <span class="sep"></span><button data-m="" aria-pressed="true">全部</button><button data-m="上市">上市</button><button data-m="上櫃">上櫃</button><a class="sc" id="scanLink" href="scan.html#natt">📈 掃 K 線</a><button id="noteBtn" aria-pressed="false" aria-label="說明">ⓘ</button>
  <span class="brk"></span>
  ''')
rep('<button data-s="chg">漲幅</button>', '<button data-s="chg" id="chgBtn">漲幅</button>')
rep('\n  <a class="sc" id="scanLink" href="scan.html#natt">📈 掃 K 線</a><button id="noteBtn" aria-pressed="false" aria-label="說明">ⓘ</button>', '')
rep("toStats?'📊 處置後統計':'📈 掃 K 線'", "toStats?'📊 統計':'📈 掃 K 線'")
# ② 提醒縮成一行
rep("return `⚠️ ${k}名單還停在 ${m[k]?f(m[k]):'前一日'}（${k==='上櫃'?'櫃買':'證交所'}尚未公布 ${f(a)}），目前只有${k==='上櫃'?'上市':'上櫃'}，稍晚自動補上`}", "return `⚠️ ${k}還停在 ${m[k]?f(m[k]):'前一日'}，目前只有${k==='上櫃'?'上市':'上櫃'}`}")
rep('font-weight:600;margin-bottom:2px">${stl}</div>', 'font-weight:600;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${stl}</div>')

# ---- 狀態與歷史名單
rep("let D=null,TAB='att',MK='',SORT='def',SHARD={},K={},LR=[];",
    "let D=null,TAB='att',MK='',SORT='def',SHARD={},K={},LR=[];\n"
    "let DAY='',HIST=null,DH=null,NAMES={},HR=null,CHGP='d';   // DAY=''＝最新；HR＝選定日回推的五名單；CHGP＝漲幅鈕 d／w／m\n"
    "const LST=k=>(DAY&&HR?HR[k]:D[k])||[];const CHGK=()=>CHGP==='w'?'w':CHGP==='m'?'mo':'chg';\n"
    "const WK='日一二三四五六';const wkd=d=>WK[new Date(+d.slice(0,4),+d.slice(4,6)-1,+d.slice(6)).getDay()];\n"
    "function wdCount(a,b){if(!a||!b||a>=b)return 0;let n=0;const x=new Date(+a.slice(0,4),+a.slice(4,6)-1,+a.slice(6));for(let i=0;i<120;i++){x.setDate(x.getDate()+1);const s=x.getFullYear()+String(x.getMonth()+1).padStart(2,'0')+String(x.getDate()).padStart(2,'0');if(s>b)break;if(x.getDay()%6)n++}return n}\n"
    "// 用 hist.json＋dis_hist.json 回推選定日的五名單（原因全文只有最新一天有；快達處置一律用次數估算）\n"
    "function histAll(day){const nm=c=>(NAMES[c]||[])[0]||c,mk=c=>(NAMES[c]||[])[1]||'';\n"
    "  const days=Object.keys(HIST).filter(d=>d<=day&&(HIST[d].att||[]).length).sort(),att=d=>(HIST[d]||{}).att||[];\n"
    "  const cnt=(c,w)=>days.slice(-w).filter(d=>att(d).includes(c)).length,streak=c=>{let n=0;for(let i=days.length-1;i>=0&&att(days[i]).includes(c);i--)n++;return n};\n"
    "  const DHv=Object.values(DH||{}).filter(v=>v&&v.c&&v.end);\n"
    "  const act={};DHv.filter(v=>v.start<=day&&day<v.end).forEach(v=>{if(!act[v.c]||v.end>act[v.c].end)act[v.c]=v});\n"
    "  const dz=v=>({c:v.c,n:v.n||nm(v.c),m:v.m||mk(v.c),r:v.r||'',start:v.start,end:v.end,startMd:md(v.start),endMd:md(v.end),measure:v.measure||'',left:wdCount(day,v.end),n30:cnt(v.c,30)});\n"
    "  const dis=Object.values(act).map(dz).sort((a,b)=>a.end<b.end?-1:a.end>b.end?1:0);\n"
    "  const post={};DHv.filter(v=>v.end<=day&&wdCount(v.end,day)<=10&&!act[v.c]).forEach(v=>{if(!post[v.c]||v.end>post[v.c].end)post[v.c]=v});\n"
    "  const a=att(day).map(c=>{const n10=cnt(c,10),n30=cnt(c,30);return {c,n:nm(c),m:mk(c),r:`${md(day)} 被列注意（原因全文只保留最新一天）`,streak:streak(c),n10,n30,warn:!act[c]&&(n10>=5||n30>=11)}});\n"
    "  const set=new Set();days.slice(-30).forEach(d=>att(d).forEach(c=>set.add(c)));\n"
    "  const pre=[...set].filter(c=>!act[c]).map(c=>({c,n:nm(c),m:mk(c),n10:cnt(c,10),n30:cnt(c,30),est:true})).filter(x=>x.n10>=5||x.n30>=11).map(x=>({...x,r:`估算：到 ${md(day)} 近 10 日 ${x.n10} 次、近 30 日 ${x.n30} 次列注意`}));\n"
    "  return {att:a,dis,pre,dend:dis.filter(x=>x.left<=3),dpost:Object.values(post).map(v=>({...dz(v),ago:wdCount(v.end,day)}))}}\n"
    "function tabCnt(){$('nAtt').textContent=LST('att').length;$('nDis').textContent=LST('dis').length;$('nPre').textContent=LST('pre').length;$('nEnd').textContent=LST('dend').length;$('nPost').textContent=LST('dpost').length}\n"
    "async function ensureK(){const codes=[...new Set(['att','dis','pre','dend','dpost'].flatMap(k=>LST(k).map(x=>x.c)))];\n"
    "  await Promise.all([...new Set(codes.map(c=>c.slice(0,2)))].map(g=>loadShard(g)));codes.forEach(c=>{if(K[c]===undefined)K[c]=kinfo(c)})}\n"
    "async function setDay(d){DAY=d&&d!==D.asof?d:'';$('daySel').classList.toggle('old',!!DAY);\n"
    "  if(DAY){if(!HIST){const [h,dh,ls]=await Promise.all(['data/notice/hist.json','data/notice/dis_hist.json','data/list.json'].map(u=>fetch(u+'?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null)));HIST=h||{};DH=dh||{};(ls||[]).forEach(r=>NAMES[r[0]]=[r[1],r[2]])}\n"
    "    HR=histAll(DAY);$('list').innerHTML='<div class=\"empty\">讀取中…</div>';await ensureK()}else HR=null;\n"
    "  tabCnt();paint()}\n"
    "async function fillDays(){try{const r=await fetch('data/notice/hist.json?t='+Math.floor(Date.now()/3e5));if(!r.ok)return;HIST0=await r.json()}catch(e){return}\n"
    "  const ds=Object.keys(HIST0).filter(d=>d<D.asof&&(HIST0[d].att||[]).length).sort().reverse().slice(0,40);\n"
    "  $('daySel').innerHTML=`<option value=\"\">${md(D.asof)}（${wkd(D.asof)}）</option>`+ds.map(d=>`<option value=\"${d}\">${md(d)}（${wkd(d)}）</option>`).join('');\n"
    "  $('daySel').onchange=e=>setDay(e.target.value)}\n"
    "let HIST0=null;")

rep("  $('nAtt').textContent=D.att.length;$('nDis').textContent=D.dis.length;$('nPre').textContent=D.pre.length;\n  $('nEnd').textContent=(D.dend||[]).length;$('nPost').textContent=(D.dpost||[]).length;\n",
    "  tabCnt();fillDays();\n")
rep("if(b.dataset.m!=null)MK=b.dataset.m;else if(b.dataset.s)SORT=b.dataset.s;paint()});",
    "if(b.dataset.m!=null)MK=b.dataset.m;else if(b.dataset.s){if(b.dataset.s==='chg'&&SORT==='chg')CHGP=CHGP==='d'?'w':CHGP==='w'?'m':'d';SORT=b.dataset.s}paint()});")
# kinfo：加週（5 個交易日前）、月（上個月同一天，休市取前一交易日；跟首頁動能、XQ 一致）
rep("  return {bars,px:last.c,d:last.d,chg:prev.c?last.c/prev.c-1:null,vr:v5?last.v/v5:null,c6,",
    "  const w=bars[n-6]?last.c/bars[n-6].c-1:null;\n"
    "  const ld=last.d,tm=new Date(+ld.slice(0,4),+ld.slice(4,6)-2,1),eom=new Date(tm.getFullYear(),tm.getMonth()+1,0).getDate(),tg=''+tm.getFullYear()+String(tm.getMonth()+1).padStart(2,'0')+String(Math.min(+ld.slice(6),eom)).padStart(2,'0');\n"
    "  let bi=-1;bars.forEach((b,j)=>{if(b.d<=tg)bi=j});const mo=bi>=0?last.c/bars[bi].c-1:null;\n"
    "  return {bars,px:last.c,d:last.d,w,mo,chg:prev.c?last.c/prev.c-1:null,vr:v5?last.v/v5:null,c6,")
rep("function rows(){let R=(D[TAB]||[]).filter(x=>!MK||x.m===MK);", "function rows(){let R=LST(TAB).filter(x=>!MK||x.m===MK);")
rep("const key={def,chg:x=>k(x.c).chg??-9,", "const key={def,chg:x=>k(x.c)[CHGK()]??-9,")
rep("  $('defBtn').textContent=T[TAB].def;", "  $('defBtn').textContent=T[TAB].def;$('chgBtn').innerHTML='漲幅 '+[['d','日'],['w','週'],['m','月']].map(([k,n])=>`<i class=\"${k===CHGP?'on':''}\">${n}</i>`).join('·');$('chgBtn').title='連點切換 日→週→月';")
rep("  $('scanLink').href=toStats?'stats.html':'scan.html#n'+TAB;", "  $('scanLink').href=toStats?'stats.html':'scan.html#n'+TAB;")
rep("const R=rows(),all=(D[TAB]||[]).length;LR=R;", "const R=rows(),all=LST(TAB).length;LR=R;")
rep("ntDemo(D);const stl=(TAB==='att'||TAB==='pre')?ntStale(D):'';",
    "ntDemo(D);const stl=DAY?`📅 ${md(DAY)} 名單・K 線與漲跌為最新（${md(D.asof)}）`:(TAB==='att'||TAB==='pre')?ntStale(D):'';")
rep("檔・名單 ${md(D.asof)}・今日上漲", "檔・名單 ${md(DAY||D.asof)}・今日上漲")
rep("    if(k){if(k.c6!=null&&!['dend','dpost'].includes(TAB))",
    "    if(k&&CHGP!=='d'&&k[CHGK()]!=null)tags.push(`<span class=\"tg\">${CHGP==='w'?'週':'月'} <b class=\"${cls(k[CHGK()])}\">${pct(k[CHGK()])}</b></span>`);\n"
    "    if(k){if(k.c6!=null&&!['dend','dpost'].includes(TAB))")
rep("本頁不構成投資建議。`;", "漲幅鈕連點＝日→週→月（週＝5 個交易日前、月＝上個月同一天）。本頁不構成投資建議。 v1113d`;")
open('notice.html' if prod else 'beta_notice.html', 'w', encoding='utf-8').write(t)
