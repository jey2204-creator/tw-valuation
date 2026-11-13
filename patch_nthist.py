"""2026-11-13：首頁注意／處置五個自動主題表——標題旁日期選單＋「數字 最新·當日」切換＋「列入後%」
接在 patch_xqsync.py 之後（需要 NTN／ntNxLine）。
  日期選單：適用（同 XQ）／🆕明日／更早 40 個名單日；歷史名單由 hist.json＋dis_hist.json 回推（跟注意頁同一套）
  數字 最新·當日：當日＝名單日收盤當下的週／月／季、量比、投外 5 日、收盤（data/notice/mo_hist.json，notice_mo.py 產生）；
                  大戶／股東、估值模式仍是最新
  列入後%：名單日收盤 → 最新收盤
用法：python3 patch_xqsync.py && python3 patch_nthist.py          （beta.html）
      python3 patch_xqsync.py prod && python3 patch_nthist.py prod （index.html）"""
import sys, re
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
fn = 'index.html' if prod else 'beta.html'
s = open(fn, encoding='utf-8').read()
assert 'function ntNxLine' in s and 'ntHistSrc' not in s
def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)

# CSS
i = s.index('</style>')
s = s[:i] + '''.ntday{font-size:16px;height:30px;border-radius:15px;border:1px solid var(--accent);background:var(--card);color:var(--fg);padding:0 4px;vertical-align:middle;font-weight:500;max-width:44vw}
.ntday.old{background:#fef3c7;border-color:#b45309;color:#7c2d12}.ntday.nx{background:#dbeafe;border-color:#1d4ed8;color:#1e3a8a}
.ntm{height:24px;line-height:22px;padding:0 8px;border-radius:12px;border:1px solid var(--line);background:var(--card);color:var(--fg);font-size:12px;vertical-align:middle;white-space:nowrap}
.ntm i{font-style:normal;opacity:.45}.ntm i.on{font-weight:800;opacity:1;text-decoration:underline;text-underline-offset:2px}
''' + s[i:]

# noticeThemes(N)：可吃任一份名單
a = s.index('function noticeThemes(){'); b = s.index('\n}\n', a)
body = s[a:b]
body = body.replace('function noticeThemes(){', 'function noticeThemes(N){N=N||NT;').replace("if(!NT)return [];const md=NT.asof?`${+NT.asof.slice(4,6)}/${+NT.asof.slice(6)}`:'';", "if(!N)return [];const md=N.asof?`${+N.asof.slice(4,6)}/${+N.asof.slice(6)}`:'';")
n0 = body.count('NT.')
body = re.sub(r"\bNT\.(att|pre|dis|dend|dpost)\b", r"N.\1", body)
assert 'NT.' not in body and n0 == 5, n0
s = s[:a] + body + s[b:]

FN = r'''
// ---- 2026-11-13：注意／處置自動主題的日期切換＋當日數字（NDAY=''＝預設適用那份；NCUR＝目前畫面上的名單日；NMODE＝now｜day）----
let NDAY='',NMODE='now',NCUR='',MOH=null,NHIST=null,NDH=null,NLOAD=null;
const ntMd=d=>d?(+d.slice(4,6))+'/'+(+d.slice(6)):'';
const ntWk=d=>'日一二三四五六'[new Date(+d.slice(0,4),+d.slice(4,6)-1,+d.slice(6)).getDay()];
const MDAY=()=>NMODE==='day'&&NCUR&&MODE==='m'?NCUR:'';
const mhRow=(id,d)=>MOH&&MOH.d&&MOH.d[d]?MOH.d[d][id]||null:null;
function ntLoad(){return NLOAD||(NLOAD=Promise.all(['data/notice/hist.json','data/notice/dis_hist.json','data/notice/mo_hist.json'].map(u=>fetch(u+'?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null))).then(([h,dh,mo])=>{NHIST=h||{};NDH=dh||{};MOH=mo}))}
function ntWd(a,b){if(!a||!b||a>=b)return 0;let n=0;const x=new Date(+a.slice(0,4),+a.slice(4,6)-1,+a.slice(6));for(let i=0;i<120;i++){x.setDate(x.getDate()+1);const s=x.getFullYear()+String(x.getMonth()+1).padStart(2,'0')+String(x.getDate()).padStart(2,'0');if(s>b)break;if(x.getDay()%6)n++}return n}
function ntHistSrc(day){const H=NHIST||{},days=Object.keys(H).filter(d=>d<=day&&(H[d].att||[]).length).sort(),att=d=>(H[d]||{}).att||[];
  const cnt=(c,w)=>days.slice(-w).filter(d=>att(d).includes(c)).length,streak=c=>{let n=0;for(let i=days.length-1;i>=0&&att(days[i]).includes(c);i--)n++;return n};
  const DHv=Object.values(NDH||{}).filter(v=>v&&v.c&&v.end);
  const act={};DHv.filter(v=>v.start<=day&&day<v.end).forEach(v=>{if(!act[v.c]||v.end>act[v.c].end)act[v.c]=v});
  const dz=v=>({c:v.c,m:v.m,start:v.start,end:v.end,endMd:ntMd(v.end),measure:v.measure||'',left:ntWd(day,v.end)});
  const dis=Object.values(act).map(dz).sort((a,b)=>a.end<b.end?-1:a.end>b.end?1:0);
  const post={};DHv.filter(v=>v.end<=day&&ntWd(v.end,day)<=10&&!act[v.c]).forEach(v=>{if(!post[v.c]||v.end>post[v.c].end)post[v.c]=v});
  const a=att(day).map(c=>({c,streak:streak(c),n10:cnt(c,10),n30:cnt(c,30)})).sort((x,y)=>y.streak-x.streak||y.n10-x.n10);
  const set=new Set();days.slice(-30).forEach(d=>att(d).forEach(c=>set.add(c)));
  const pre=[...set].filter(c=>!act[c]).map(c=>({c,n10:cnt(c,10),n30:cnt(c,30),est:true})).filter(x=>x.n10>=5||x.n30>=11).sort((x,y)=>y.n10-x.n10);
  return {asof:day,att:a,dis,pre,dend:dis.filter(x=>x.left<=3),dpost:Object.values(post).map(v=>({...dz(v),ago:ntWd(v.end,day)})).sort((x,y)=>x.ago-y.ago)}}
function ntSrc(day){return day===NT.asof?NT:NTN&&day===NTN.asof?NTN:NHIST?ntHistSrc(day):null}
function ntDayOpts(){const cur=NDAY||NT.asof,o=[];if(NTN)o.push([NTN.asof,'🆕明日 '+ntMd(NTN.asof)]);o.push([NT.asof,(NTN?'適用 ':'')+ntMd(NT.asof)+(NTN?'':'（'+ntWk(NT.asof)+'）')]);
  Object.keys(NHIST||{}).filter(d=>d<NT.asof&&(NHIST[d].att||[]).length).sort().reverse().slice(0,40).forEach(d=>o.push([d,ntMd(d)+'（'+ntWk(d)+'）']));
  return o.map(([v,l])=>`<option value="${v}"${v===cur?' selected':''}>${l}</option>`).join('')}
function ntHead(id){const d=NCUR,isNx=NTN&&d===NTN.asof;
  const lab=d===NT.asof?(NTN?`今日適用（${ntMd(d)} 公布，同 XQ）`:`名單日 ${ntMd(d)}（${ntWk(d)}）`):isNx?`明日適用（${ntMd(d)} 公布）`:`歷史名單 ${ntMd(d)}（${ntWk(d)}）`;
  const mb=MODE==='m'?`<button type="button" id="ntMode" class="ntm">數字 <i class="${NMODE==='now'?'on':''}">最新</i>·<i class="${NMODE==='day'?'on':''}">${ntMd(d)}當日</i></button>`:'';
  const w=isNx&&(id==='natt'||id==='npre')?ntStale(NTN):'';
  return `<span class="asof">🔄 ${lab}</span> ${mb}<br>${d===NT.asof?ntNxLine(id):w?`<b style="color:#b45309">${w}</b><br>`:''}`}
function ntRe(){const h=decodeURIComponent(location.hash.slice(1));if(h.startsWith('t/'))showTheme(h.slice(2))}
document.addEventListener('change',e=>{if(e.target&&e.target.id==='ntDay'){NDAY=e.target.value===NT.asof?'':e.target.value;ntRe()}});
document.addEventListener('click',e=>{const b=e.target.closest&&e.target.closest('#ntMode,#ntToNx');if(!b)return;e.preventDefault();if(b.id==='ntMode')NMODE=NMODE==='day'?'now':'day';else if(NTN)NDAY=NTN.asof;ntRe()});
'''
j = s.rfind('<script>', 0, s.index("function noticeThemes")) + len('<script>')
s = s[:j] + FN + s[j:]

rep('<a href="notice.html#${k}">看明日 →</a><br>`}', '<a href="#" id="ntToNx">看明日 ›</a><br>`}')
# 當日數字：mv／收盤
rep("const mv=(id,k)=>{if(!MO)return null;", "const mv=(id,k)=>{{const d=MDAY();if(d){const r=mhRow(id,d),i={w:0,m:1,q:2,vr:3,f5:4,t5:5}[k];return r&&i!=null?r[i]:null}}if(!MO)return null;")
rep("  const c=sv(id,'close'),ch=sv(id,'chg'),fire=mv(id,'fire'),", "  const mh=MDAY()?mhRow(id,MDAY()):null,c=MDAY()?(mh?mh[6]:null):sv(id,'close'),ch=MDAY()?(mh?mh[7]:null):sv(id,'chg'),fire=mv(id,'fire'),\n"
    "    aft=(()=>{if(!NCUR)return '';const r=mhRow(id,NCUR),c0=r&&r[6],c1=sv(id,'close');if(!c0||!c1||!MO||!(MO.asof>NCUR))return '';const v=(c1/c0-1)*100;return `<span class=\"sub\"><span class=\"sm\">列入後</span> <span class=\"${sign(v)}\">${pct(v)}</span></span>`})(),")
rep("<span class=\"${vr!=null&&vr>=1.5?'up':''}\">${vr==null?'—':fmt(vr,2)}</span><span class=\"sub\">${tip('投',", "<span class=\"${vr!=null&&vr>=1.5?'up':''}\">${vr==null?'—':fmt(vr,2)}</span>${aft}<span class=\"sub\">${tip('投',")
# showTheme：換名單、標題選單、名單日那行
rep("  const t=THEMES.find(x=>x.id===tid);if(!t){location.hash='';return}\n  try{sessionStorage.setItem('lastTheme',tid)}catch(e){}\n  $('tName').textContent=t.name;",
    "  let t=THEMES.find(x=>x.id===tid);if(!t){location.hash='';return}\n  try{sessionStorage.setItem('lastTheme',tid)}catch(e){}\n"
    "  NCUR='';if(t.notice&&NT){const day=NDAY||NT.asof;if(!NHIST)ntLoad().then(()=>{if(decodeURIComponent(location.hash.slice(1))==='t/'+tid)showTheme(tid)});\n"
    "    if(day!==NT.asof){const src=ntSrc(day);if(src){const alt=noticeThemes(src).find(x=>x.id===tid);t=alt||{...t,stocks:[]}}}NCUR=day}\n"
    "  if(NCUR)$('tName').innerHTML=`${esc(t.name.replace(/（[^）]*）$/,''))} <select id=\"ntDay\" class=\"ntday${NCUR===NT.asof?'':NTN&&NCUR===NTN.asof?' nx':' old'}\" aria-label=\"名單日期\">${ntDayOpts()}</select>`;else $('tName').textContent=t.name;")
rep("<span class=\"asof\">🔄 ${NTN?`今日適用（${+NT.asof.slice(4,6)}/${+NT.asof.slice(6)} 公布，同 XQ）`:`名單日 ${NT.asof.slice(0,4)}/${NT.asof.slice(4,6)}/${NT.asof.slice(6)}`}・每個交易日 17:25 後自動更新，不可編輯、不佔自選額度</span><br>${ntNxLine(t.id)}",
    "${ntHead(t.id)}")
# 頁尾說明（動能模式）
k = s.index("\nfunction stockExtras(id){")
s = s[:k] + "\n{const _st=showTheme;showTheme=function(tid){_st(tid);if(NCUR&&MODE==='m')$('tFoot').innerHTML='<b>日期選單只換名單</b>；「數字」預設最新，點一下可看名單日當天收盤的週／月／季、量比、投外 5 日與收盤（大戶／股東、估值模式仍是最新）。<b>列入後</b>＝名單日收盤 → 最新收盤的漲跌。名單每個交易日 17:25 後自動更新。<br>'+$('tFoot').innerHTML}}" + s[k:]
open(fn, 'w', encoding='utf-8').write(s)

p = open('fetch_notice.py', encoding='utf-8').read()
if 'notice_mo' not in p:
    p = p.rstrip('\n') + "\n\n# 2026-11-13：名單日「當日數字」快照（首頁注意股主題表切日期用）\ntry:\n    import notice_mo\n    notice_mo.main()\nexcept Exception as e:\n    print(\"notice_mo 失敗：\", e)\n"
    open('fetch_notice.py', 'w', encoding='utf-8').write(p)
