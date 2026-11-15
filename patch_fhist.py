"""2026-11-15：首頁「🔥 主力訊號」看之前的個股（世杰選 ①＋②）
① 日期選單：標題下方選日期 → 換成那天的 🔥 名單；「數字 最新·當日」切換；每檔多一行「上榜後 x%」（那天收盤 → 最新收盤，還原價）
② 上榜標記：每檔標「🆕新進／連 N 天」；表格下方列「掉出」（前一個交易日有 🔥、這天沒有）與原因（月轉負／量縮／法人縮手）
資料：data/fire_hist.json（fire_hist.py 產生，全市場每天的 🔥 名單，網頁再篩出主題＋自選）；展開主力訊號時才載入
做法：畫主力訊號表時設 HX={day,mode}，mCells／mv／MDAY／mhRow 看到 HX 就改讀 fire_hist（不影響其他表）
用法：python3 patch_fhist.py [prod]   （預設 index.html → beta.html）"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
s = open('index.html', encoding='utf-8').read()
assert 'fire_hist' not in s
def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)

# CSS
rep(".fire{font-size:13px;margin-left:3px}",
    ".fire{font-size:13px;margin-left:3px}\n"
    "#hotCtl{display:flex;align-items:center;gap:6px;flex-wrap:wrap;padding:8px 0 4px}#hotCtl:empty{display:none}#hotCtl .ntday{height:28px;font-weight:400}\n"
    "#hotCtl .hsum{font-size:12px;color:var(--muted);margin-left:auto;white-space:nowrap}#hotCtl .hsum b{color:var(--up);font-weight:600}\n"
    "#hotDrop{font-size:12px;line-height:1.7;white-space:normal}#hotDrop:empty{display:none}#hotDrop a{color:var(--fg);text-decoration:underline;text-decoration-color:var(--line);text-underline-offset:3px}\n"
    ".flag.fnew{color:var(--up);border-color:var(--up);margin-left:0}.flag.fstk{margin-left:0}")

# HTML：控制列、掉出清單
rep('<div style="padding:0 10px 8px"><div class="tbl"><table class="lst" id="hotTbl"></table></div><p class="foot" id="hotFoot"></p></div>',
    '<div style="padding:0 10px 8px"><div id="hotCtl"></div><div class="tbl"><table class="lst" id="hotTbl"></table></div><p class="foot" id="hotDrop"></p><p class="foot" id="hotFoot"></p></div>')

# HX：主力訊號表專用的日期／數字來源
rep("const MDAY=()=>NMODE==='day'&&NCUR&&MODE==='m'?NCUR:'';\nconst mhRow=(id,d)=>MOH&&MOH.d&&MOH.d[d]?MOH.d[d][id]||null:null;",
    "let FH=null,FHP=null,HX=null,HOTC=null,HDAY='',HMODE='now';   // 2026-11-15：主力訊號歷史（HX＝正在畫主力訊號表；HDAY=''＝最新）\n"
    "const MDAY=()=>HX?(HX.mode==='day'?HX.day:''):NMODE==='day'&&NCUR&&MODE==='m'?NCUR:'';\n"
    "const mhRow=(id,d)=>HX?(FH&&FH.d[d]?FH.d[d][id]||null:null):MOH&&MOH.d&&MOH.d[d]?MOH.d[d][id]||null:null;")
rep("a=MOH&&MOH.a&&MOH.a[d]&&MOH.a[d][id];if(a&&ai!=null&&r)return a[ai];", "a=!HX&&MOH&&MOH.a&&MOH.a[d]&&MOH.a[d][id];if(a&&ai!=null&&r)return a[ai];")
rep("ch=MDAY()?(mh?((MOH.a&&MOH.a[MDAY()]&&MOH.a[MDAY()][id])||[])[3]??mh[7]:null):sv(id,'chg'),fire=mv(id,'fire'),",
    "ch=MDAY()?(mh?((!HX&&MOH&&MOH.a&&MOH.a[MDAY()]&&MOH.a[MDAY()][id])||[])[3]??mh[7]:null):sv(id,'chg'),fire=HX&&HX.mode==='day'?1:mv(id,'fire'),")
rep("aft=(()=>{if(!NCUR)return '';const r=mhRow(id,NCUR),c0=r&&r[6],c1=sv(id,'close');if(!c0||!c1||!MO||!(MO.asof>NCUR))return '';const v=(c1/(c0*adjF(id,NCUR,MO.asof))-1)*100;return `<span class=\"sub\"><span class=\"sm\">列入後</span>",
    "aft=(()=>{const nd=HX?HX.day:NCUR;if(!nd)return '';const r=mhRow(id,nd),c0=r&&r[6],c1=sv(id,'close');if(!c0||!c1||!MO||!(MO.asof>nd))return '';const v=(c1/(c0*adjF(id,nd,MO.asof))-1)*100;return `<span class=\"sub\"><span class=\"sm\">${HX?'上榜後':'列入後'}</span>")
rep("ck=chip(id),up=fire&&ck==='c';", "ck=chip(id),up=fire&&ck==='c'&&!(HX&&HX.mode==='day');")   # 當日數字模式：籌碼是最新一週的，不標「集中↑」
rep("function table(el,items,sortKey,mode){",
    "function table(el,items,sortKey,mode){const _h=HX;HX=el&&el.id==='hotTbl'?HOTC:null;try{return table0(el,items,sortKey,mode)}finally{HX=_h}}\n"
    "function table0(el,items,sortKey,mode){")

# renderHome：主力訊號區改呼叫 hotPaint()
a = s.index("  {const pool=[...new Set([...THEMES.flatMap(t=>t.stocks.map(x=>x[0])),...fav])],hot=pool.filter(id=>mv(id,'fire'));")
b = s.index("Actions 跑完後就會出現。'}", a) + len("Actions 跑完後就會出現。'}")
s = s[:a] + "  hotPaint();" + s[b:]

FN = r'''
// ---- 2026-11-15：🔥 主力訊號看之前的個股（日期選單＋上榜後%＋🆕新進／連 N 天／掉出；data/fire_hist.json）----
function fhLoad(){return FHP||(FHP=fetch('data/fire_hist.json?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null).then(j=>{FH=j&&j.d?j:{days:[],d:{},x:{}}}))}
const FWHY=[[1,'月轉負'],[2,'量縮'],[4,'法人縮手'],[8,'無資料']];
function hotPaint(){
  const fav=store.get('fav')||[],pool=[...new Set([...THEMES.flatMap(t=>t.stocks.map(x=>x[0])),...fav])],ht=$('hotTbl');
  const last=MO?MO.asof:'',hasH=!!(FH&&FH.days.length),days=[...new Set([...(hasH?FH.days:[]),last].filter(Boolean))].sort();
  if(HDAY&&(!days.includes(HDAY)||HDAY===last))HDAY='';
  const day=HDAY||last,isNow=day===last,i=days.indexOf(day),prev=i>0?days[i-1]:'';
  const has=(d,id)=>d===last&&MO?!!(MO.d[id]&&MO.d[id][MF.fire]):!!(FH&&FH.d[d]&&FH.d[d][id]);
  const hot=pool.filter(id=>has(day,id)),streak=id=>{let n=1,k=i-1;while(k>=0&&has(days[k],id)){n++;k--}return [n,k<0]};
  const st={};if(hasH&&prev)hot.forEach(id=>st[id]=streak(id));
  const nNew=hot.filter(id=>st[id]&&st[id][0]===1).length,drop=hasH&&prev?pool.filter(id=>has(prev,id)&&!has(day,id)):[];
  $('hotN').textContent=MO?`${isNow?'':ymd(day)+'・'}${hot.length} / ${pool.length} 檔`:'準備中';
  const badge=id=>{const x=st[id];if(!x)return '';return x[0]===1?`<span class="flag fnew" data-tip="🆕 新進：${ymd(prev)} 還沒有 🔥，${ymd(day)} 才符合條件（剛啟動）">🆕新進</span> `:`<span class="flag fstk" data-tip="已連續 ${x[0]} 個交易日符合 🔥 條件${x[1]?'（歷史只回推到 '+ymd(days[0])+'，實際可能更久）':''}。連越多天通常越接近注意股，追進的位置越晚">連${x[0]}天${x[1]?'+':''}</span> `};
  HOTC={day,mode:isNow?'now':HMODE};
  ht.dataset.sort=ht.dataset.sort||'m_m:-1';
  table(ht,hot.map(id=>[id,badge(id)+(THEMES.find(t=>t.stocks.some(x=>x[0]===id))||{name:'⭐ 自選'}).name]),undefined,'m');
  $('hotCtl').innerHTML=hasH&&days.length>1?`<select id="fhDay" class="ntday${isNow?'':' old'}" aria-label="主力訊號日期">${days.slice().reverse().map(d=>`<option value="${d}"${d===day?' selected':''}>${ymd(d)}（${ntWk(d)}）</option>`).join('')}</select>`
    +(isNow?'':`<button type="button" id="fhMode" class="ntm">數字 <i class="${HMODE==='now'?'on':''}">最新</i>·<i class="${HMODE==='day'?'on':''}">當日</i></button>`)
    +(prev?`<span class="hsum"><b>🆕 ${nNew}</b>・續 ${hot.length-nNew}・⬇ ${drop.length}</span>`:''):'';
  const X=(FH&&FH.x&&FH.x[day])||{};
  $('hotDrop').innerHTML=drop.length?`<b>⬇ 掉出 ${drop.length} 檔</b>（${ymd(prev)} 有 🔥、${ymd(day)} 沒有）：`+drop.map(id=>{const x=X[id]||[],ch=isNow?sv(id,'chg'):x[1],why=FWHY.filter(([b])=>x[0]&b).map(y=>y[1]).join('＋');
    return `<a href="#${id}">${nameOf(id)}</a> <span class="${sign(ch)}">${ch==null?'':pct(ch,1)}</span>${why?`<span class="sm">（${why}）</span>`:''}`}).join('、'):'';
  $('hotFoot').innerHTML=MO?`範圍：產業主題＋自選共 ${pool.length} 檔。🔥＝月漲幅 &gt; 0、量比（5 日均量 ÷ 20 日均量）≥ 1.5、且投信或外資 5 日買超 ≥ 5 日成交量的 1%。是「有資金在推」的訊號，不是買進訊號，要搭配估值位階看。`
    +(hasH?`<br><b>日期選單</b>可看之前哪些股票上榜（從 ${ymd(days[0])} 起）；選了舊日期，「數字」預設最新，點一下看當天收盤的數字，還亮著 🔥 的＝今天仍符合。<b>上榜後</b>＝那天收盤 → 最新收盤。<b>🆕新進</b>＝前一個交易日還沒有 🔥；<b>連 N 天</b>＝連續符合的交易日數。大戶／股東一律是最新一週。`:'')
    +` 資料 ${ymd(MO.asof)} <span style="opacity:.5">v1115b</span>`:'第一次需要回補約 3 個月的歷史資料，Actions 跑完後就會出現。';
}
document.addEventListener('toggle',e=>{if(e.target&&e.target.id==='hotBox'&&e.target.open&&!FH)fhLoad().then(()=>{try{hotPaint()}catch(err){}})},true);
document.addEventListener('change',e=>{if(e.target&&e.target.id==='fhDay'){HDAY=e.target.value;hotPaint()}});
document.addEventListener('click',e=>{const b=e.target.closest&&e.target.closest('#fhMode');if(!b)return;e.preventDefault();HMODE=HMODE==='day'?'now':'day';hotPaint()});
'''
k = s.index("\nfunction renderHome(){")
s = s[:k] + FN + s[k:]
out = 'index.html' if prod else 'beta.html'
open(out, 'w', encoding='utf-8').write(s)
print('ok →', out)
