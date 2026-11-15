#!/usr/bin/env python3
"""2026-11-15 掃描頁「全部▾」展開面板：名單橫列往右要滑很久 → 最左釘一顆「全部▾」，
點開後所有名單用 3 欄格子分組列出（🕘 最近用過／⭐ 自選・訊號籌碼／⚠️ 注意・處置／🏭 產業主題／🏛 證交所產業），
分類標題可收合（記在 localStorage scanAllCol；證交所產業預設收起），點了就切換並收起。原橫列順序不動。
用法：python3 patch_tall.py → beta_scan_all.html；python3 patch_tall.py prod → scan.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
s=open('scan.html',encoding='utf-8').read()
def rep(old,new,n=1):
    global s;assert s.count(old)==n,(s.count(old),old[:90]);s=s.replace(old,new)

# ---- CSS
rep('''/* 兩行控制列（2026-10-29 beta）''','''/* 2026-11-15「全部▾」面板：標題＋全部鈕釘在橫列最左；面板從標題列底下展開，3 欄格子、分類可收合 */
.hd .lead{flex:none;position:sticky;left:0;z-index:2;display:flex;align-items:center;gap:5px;background:var(--bg);padding-right:5px;box-shadow:6px 0 6px -4px var(--bg)}
.ch.all{padding:0 9px;background:var(--card);border:1px solid var(--line);font-weight:700}
.ch.all[aria-expanded=true]{background:var(--accent);border-color:var(--accent);color:#fff}
.ap{position:fixed;left:0;right:0;top:var(--ovtop,0);bottom:0;z-index:20;background:rgba(0,0,0,.45)}
.apb{background:var(--card);max-height:100%;overflow:auto;-webkit-overflow-scrolling:touch;padding:2px 8px calc(10px + env(safe-area-inset-bottom));border-radius:0 0 14px 14px;box-shadow:0 6px 20px rgba(0,0,0,.2)}
@supports (height:100dvh){.ap{bottom:auto;height:calc(100dvh - var(--ovtop,0px))}}
.aph{display:flex;align-items:center;gap:6px;width:100%;height:32px;margin-top:4px;font-size:13px;font-weight:700;text-align:left}
.aph i{font-style:normal;font-weight:500;font-size:11px;color:var(--muted)}
.aph span{margin-left:auto;color:var(--muted);font-size:12px;padding:0 4px}
.apg{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px}
.apg button{min-height:40px;padding:3px 5px;border-radius:9px;background:var(--chip);font-size:12.5px;line-height:1.2;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;overflow:hidden}
.apg button b{font-weight:500;max-width:100%;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;word-break:break-all}
.apg button i{font-style:normal;font-size:10.5px;opacity:.6;white-space:nowrap}
.apg button[aria-pressed=true]{background:var(--sel);color:var(--selfg)}
.apg button[aria-pressed=true] b{font-weight:700}
/* 兩行控制列（2026-10-29 beta）''')

# ---- HTML
rep('''    <span class="t">掃描</span>
''','''    <span class="lead"><span class="t">掃描</span><button class="ch all" id="allBtn" aria-expanded="false" title="全部名單（分類可收合）">全部▾</button></span>
''')
rep('''<div class="ov" id="ov" hidden>''','''<div class="ap" id="ap" hidden><div class="apb" id="apb"></div></div>
<div class="ov" id="ov" hidden>''')

# ---- JS：面板
rep('''function paintBar(){''','''// ---- 2026-11-15「全部▾」面板（最近用過＋四個可收合分類；點了就切換並收起）
let APC=store.get('scanAllCol')||{ind:1};
function apSecs(){const cut=t=>{const dm=t.name.match(/^(.*?)\\s*[（(](\\d{1,2}\\/\\d{1,2})[）)]\\s*$/);return {sel:{kind:'t',id:t.id},n:dm?dm[1]:t.name,c:t.stocks.length,sub:dm?dm[2]:''}};
  const A=THEMES.filter(t=>t.id==='_fav'||t.id==='fire'||(t.id in TKEY)),B=THEMES.filter(t=>NSET.has(t.id)),C=THEMES.filter(t=>!A.includes(t)&&!B.includes(t));
  const inds=Object.keys(IND).filter(k=>k&&k!=='其他').sort((a,b)=>IND[b].length-IND[a].length);
  return [['fav','⭐ 自選・訊號籌碼',A.map(cut)],['nt','⚠️ 注意／處置',B.map(cut)],['th','🏭 產業主題',C.map(cut)],['ind','🏛 證交所產業',inds.map(k=>({sel:{kind:'i',id:k},n:k,c:IND[k].length,sub:''}))]].filter(g=>g[2].length)}
function apPaint(){const S=apSecs(),all=S.flatMap(g=>g[2]),same=(a,b)=>a&&b&&a.kind===b.kind&&a.id===b.id;
  const btn=x=>`<button data-ak="${x.sel.kind}" data-ai="${esc(x.sel.id)}" aria-pressed="${same(cur,x.sel)}"><b>${esc(x.n)}</b><i class="num">${x.c}${x.sub?'・'+x.sub:''}</i></button>`;
  const rec=(store.get('scanRecent')||[]).map(r=>all.find(x=>same(x.sel,r))).filter(x=>x&&!same(cur,x.sel)).slice(0,6);
  $('apb').innerHTML=(rec.length?`<div class="aph" style="cursor:default">🕘 最近用過</div><div class="apg">${rec.map(btn).join('')}</div>`:'')+
    S.map(([g,n,L])=>`<button class="aph" data-g="${g}" aria-expanded="${!APC[g]}">${n} <i class="num">${L.length}</i><span>${APC[g]?'展開 ▸':'收起 ▾'}</span></button><div class="apg"${APC[g]?' hidden':''}>${L.map(btn).join('')}</div>`).join('')}
function apOpen(){apPaint();ovTop();$('ap').hidden=false;document.body.style.overflow='hidden';$('allBtn').setAttribute('aria-expanded','true');$('allBtn').textContent='收起▴';$('apb').scrollTop=0}
function apClose(){if($('ap').hidden)return;$('ap').hidden=true;document.body.style.overflow='';$('allBtn').setAttribute('aria-expanded','false');$('allBtn').textContent='全部▾'}
$('allBtn').addEventListener('click',()=>{$('ap').hidden?apOpen():apClose()});
$('ap').addEventListener('click',e=>{if(e.target===$('ap')){apClose();return}
  const h=e.target.closest('button[data-g]');if(h){APC[h.dataset.g]=APC[h.dataset.g]?0:1;store.set('scanAllCol',APC);apPaint();return}
  const b=e.target.closest('button[data-ak]');if(b){apClose();pick({kind:b.dataset.ak,id:b.dataset.ai})}});
addEventListener('keydown',e=>{if(e.key==='Escape')apClose()});
addEventListener('resize',()=>{if(!$('ap').hidden)ovTop()});
function paintBar(){''')

# 點橫列的鈕／產業下拉時，面板開著就先收起；pick() 記「最近用過」
rep('''async function pick(sel){cur=sel;
''','''async function pick(sel){cur=sel;apClose();
  if(sel.kind==='t'||sel.kind==='i'){const R=(store.get('scanRecent')||[]).filter(r=>!(r.kind===sel.kind&&r.id===sel.id));R.unshift({kind:sel.kind,id:sel.id});store.set('scanRecent',R.slice(0,8))}
''')

rep('''<span style="opacity:.5">v1115h</span>''','''<span style="opacity:.5">v1115j</span>''')
if not prod:s=s.replace('<title>','<title>[beta] ',1)
open('scan.html' if prod else 'beta_scan_all.html','w',encoding='utf-8').write(s);print('ok')
