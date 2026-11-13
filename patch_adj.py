"""2026-11-13：週／月／季漲幅改用還原價（除權息、減資、面額變更），跟 XQ 一致
資料：fetch_adj.py → data/adj.json（還原係數）；fetch_momentum.py → momentum.json 的 da；notice_mo.py → mo_hist.json 的 a
  首頁：動能模式的週／月／季優先用 da（當日模式用 mo_hist 的 a）；「列入後%」跨除權息日也還原
  注意頁、掃描頁：只有漲幅數字（日／週／月／6 日／結束後）用還原價算；小 K 線維持原始價、不還原（世杰 11/13 指定）
用法：python3 patch_adj.py [prod]   （預設 index.html→beta.html、notice.html→beta_notice.html、scan.html→beta_scan_adj.html）"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
def rep(s, a, b):
    assert s.count(a) == 1, (s.count(a), a[:70])
    return s.replace(a, b)
AJ = "fetch('data/adj.json?t='+Math.floor(Date.now()/36e5)).then(r=>r.ok?r.json():null).catch(()=>null)"

# ---------------- index.html
s = open('index.html', encoding='utf-8').read()
s = rep(s, "function ntLoad(){return NLOAD||(NLOAD=Promise.all(['data/notice/hist.json','data/notice/dis_hist.json','data/notice/mo_hist.json'].map(u=>fetch(u+'?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null))).then(([h,dh,mo])=>{NHIST=h||{};NDH=dh||{};MOH=mo}))}",
        "let ADJX={};   /* 還原係數 {代號:[[事件日,係數,類別]]}（2026-11-13） */\n"
        "const adjF=(id,a,b)=>(ADJX[id]||[]).reduce((k,[d,f])=>a<d&&d<=b?k*f:k,1);\n"
        "function ntLoad(){return NLOAD||(NLOAD=Promise.all(['data/notice/hist.json','data/notice/dis_hist.json','data/notice/mo_hist.json','data/adj.json'].map(u=>fetch(u+'?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).catch(()=>null))).then(([h,dh,mo,aj])=>{NHIST=h||{};NDH=dh||{};MOH=mo;ADJX=aj&&aj.ev||{}}))}")
s = rep(s, "const mv=(id,k)=>{{const d=MDAY();if(d){const r=mhRow(id,d),i={w:0,m:1,q:2,vr:3,f5:4,t5:5}[k];return r&&i!=null?r[i]:null}}if(!MO)return null;if((k==='m'||k==='q')&&MO.dc){",
        "const mv=(id,k)=>{const ai={w:0,m:1,q:2}[k];{const d=MDAY();if(d){const r=mhRow(id,d),i={w:0,m:1,q:2,vr:3,f5:4,t5:5}[k],a=MOH&&MOH.a&&MOH.a[d]&&MOH.a[d][id];if(a&&ai!=null&&r)return a[ai];return r&&i!=null?r[i]:null}}if(!MO)return null;if(ai!=null&&MO.da&&MO.da[id])return MO.da[id][ai];if((k==='m'||k==='q')&&MO.dc){")
s = rep(s, "ch=MDAY()?(mh?mh[7]:null):sv(id,'chg'),", "ch=MDAY()?(mh?((MOH.a&&MOH.a[MDAY()]&&MOH.a[MDAY()][id])||[])[3]??mh[7]:null):sv(id,'chg'),")
s = rep(s, "if(!c0||!c1||!MO||!(MO.asof>NCUR))return '';const v=(c1/c0-1)*100;", "if(!c0||!c1||!MO||!(MO.asof>NCUR))return '';const v=(c1/(c0*adjF(id,NCUR,MO.asof))-1)*100;")
s = rep(s, "（未還原除權息，跨除息日會略低）。量比＝", "${MO&&MO.da?'（已還原除權息、減資、面額變更，跟 XQ 一致）':'（未還原除權息，跨除息日會略低）'}。量比＝")
open('index.html' if prod else 'beta.html', 'w', encoding='utf-8').write(s)

# ---------------- notice.html
n = open('notice.html', encoding='utf-8').read()
n = rep(n, "async function loadShard(g){", "let ADJ={};   /* 還原係數（2026-11-13）：只用在漲幅數字，小 K 線不還原 */\nconst adjF=(c,a,b)=>(ADJ[c]||[]).reduce((k,[d,f])=>String(a)<d&&d<=String(b)?k*f:k,1);\nasync function loadShard(g){")
n = rep(n, "  if(bars.length<6)return null;const n=bars.length,last=bars[n-1],prev=bars[n-2];\n",
        "  if(bars.length<6)return null;const n=bars.length,last=bars[n-1],prev=bars[n-2];\n"
        "  const rt=b=>b&&b.c?last.c/(b.c*adjF(c,b.d,last.d))-1:null;   /* 還原後漲幅：基準價 × 之後發生的除權息／減資／面額變更係數 */\n")
n = rep(n, "const c6=bars[n-7]?last.c/bars[n-7].c-1:null;", "const c6=rt(bars[n-7]);")
n = rep(n, "const w=bars[n-6]?last.c/bars[n-6].c-1:null;", "const w=rt(bars[n-6]);")
n = rep(n, "const mo=bi>=0?last.c/bars[bi].c-1:null;", "const mo=bi>=0?rt(bars[bi]):null;")
n = rep(n, "return {bars,px:last.c,d:last.d,w,mo,chg:prev.c?last.c/prev.c-1:null,", "return {bars,px:last.c,d:last.d,w,mo,chg:rt(prev),")
n = rep(n, "return {ret:k.bars[k.bars.length-1].c/k.bars[i].c-1,n:k.bars.length-1-i}}", "{const L=k.bars[k.bars.length-1],B=k.bars[i];return {ret:L.c/(B.c*adjF(c,B.d,L.d))-1,n:k.bars.length-1-i}}}")
n = rep(n, "  D=r&&r.ok?await r.json():null;", "  try{const aj=await " + AJ + ";ADJ=aj&&aj.ev||{}}catch(e){}\n  D=r&&r.ok?await r.json():null;")
n = rep(n, "（週＝5 個交易日前、月＝上個月同一天）。預設顯示", "（週＝5 個交易日前、月＝上個月同一天；漲幅數字已還原除權息、減資、面額變更，跟 XQ 一致，小 K 線為原始價）。預設顯示")
n = rep(n, " v1113f`", " v1113h`")
open('notice.html' if prod else 'beta_notice.html', 'w', encoding='utf-8').write(n)

# ---------------- scan.html
c = open('scan.html', encoding='utf-8').read()
c = rep(c, "const [L,T,TOP,NT0,PV]=await Promise.all([", "const [AJ0,L,T,TOP,NT0,PV]=await Promise.all([" + AJ + ".then(j=>{window.ADJ=j&&j.ev||{};return j}),")
c = rep(c, "  if(bars.length<6)return null;\n  // 分割／減資等大跳空",
        "  if(bars.length<6)return null;\n"
        "  // 2026-11-13：漲幅數字用還原價（data/adj.json），小 K 線不還原 → 先記下原始收盤 rc，漲幅＝最新 ÷（基準原始收盤 × 之後的還原係數）\n"
        "  bars.forEach(b=>b.rc=b.c);const adjF=(a,z)=>((window.ADJ||{})[c]||[]).reduce((k,[d,f])=>String(a)<d&&d<=String(z)?k*f:k,1);\n"
        "  // 分割／減資等大跳空")
c = rep(c, "chg:prev.c?last.c/prev.c-1:null,chg5:n>5&&bars[n-6].c?last.c/bars[n-6].c-1:null,chg20:calM(bars),",
        "chg:prev.rc?last.rc/(prev.rc*adjF(prev.d,last.d))-1:null,chg5:n>5&&bars[n-6].rc?last.rc/(bars[n-6].rc*adjF(bars[n-6].d,last.d))-1:null,chg20:calM(bars,adjF),")
c = rep(c, "function calM(bars){", "function calM(bars,adjF){")
c = rep(c, "return bi>=0&&bars[bi].c?last.c/bars[bi].c-1:null}", "if(adjF&&bi>=0&&bars[bi].rc)return last.rc/(bars[bi].rc*adjF(bars[bi].d,last.d))-1;return bi>=0&&bars[bi].c?last.c/bars[bi].c-1:null}")
c = rep(c, "切換 日→週→月漲幅（週＝5 個交易日前、月＝上個月同一天）", "切換 日→週→月漲幅（週＝5 個交易日前、月＝上個月同一天；已還原除權息／減資）")
c = rep(c, "⚠＝近 130 日有分割（價位概略還原，未還原除權息）", "⚠＝近 130 日有分割（K 線價位概略還原）；日／週／月漲幅數字已還原除權息、減資、面額變更（跟 XQ 一致），小 K 線為原始價")
open('scan.html' if prod else 'beta_scan_adj.html', 'w', encoding='utf-8').write(c)
print('ok', 'prod' if prod else 'beta')
