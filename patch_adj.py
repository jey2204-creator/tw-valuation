"""2026-11-13：週／月／季漲幅改用還原價（除權息、減資、面額變更），跟 XQ 一致
資料：fetch_adj.py → data/adj.json（還原係數）；fetch_momentum.py → momentum.json 的 da；notice_mo.py → mo_hist.json 的 a
  首頁：動能模式的週／月／季優先用 da（當日模式用 mo_hist 的 a）；「列入後%」跨除權息日也還原
  注意頁、掃描頁：日K 讀進來後先依 adj.json 把事件日之前的價位還原，再算週／月／6 日／結束後漲幅（K 線缺口也會補平）
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
n = rep(n, "async function loadShard(g){", "let ADJ={};   /* 還原係數（2026-11-13）：事件日之前的價位 × 係數 */\nasync function loadShard(g){")
n = rep(n, "bars.push({d:days[i],o,h,l,c:cl,v:r[1]||0,f:r[2],t:r[3]})});\n",
        "bars.push({d:days[i],o,h,l,c:cl,v:r[1]||0,f:r[2],t:r[3]})});\n"
        "  (ADJ[c]||[]).forEach(([d,f])=>bars.forEach(b=>{if(String(b.d)<d){b.o*=f;b.h*=f;b.l*=f;b.c*=f}}));\n")
n = rep(n, "  D=r&&r.ok?await r.json():null;", "  try{const aj=await " + AJ + ";ADJ=aj&&aj.ev||{}}catch(e){}\n  D=r&&r.ok?await r.json():null;")
n = rep(n, "（週＝5 個交易日前、月＝上個月同一天）。預設顯示", "（週＝5 個交易日前、月＝上個月同一天；價位已還原除權息、減資、面額變更，跟 XQ 一致）。預設顯示")
n = rep(n, " v1113f`", " v1113g`")
open('notice.html' if prod else 'beta_notice.html', 'w', encoding='utf-8').write(n)

# ---------------- scan.html
c = open('scan.html', encoding='utf-8').read()
c = rep(c, "const [L,T,TOP,NT0,PV]=await Promise.all([", "const [AJ0,L,T,TOP,NT0,PV]=await Promise.all([" + AJ + ".then(j=>{window.ADJ=j&&j.ev||{};return j}),")
c = rep(c, "  if(bars.length<6)return null;\n  // 分割／減資等大跳空",
        "  if(bars.length<6)return null;\n"
        "  // 2026-11-13：依 data/adj.json 還原除權息／減資／面額變更（事件日之前的價位 × 係數）；係數差超過 30% 視為股數變動，量也換算\n"
        "  let adjBig=false;((window.ADJ||{})[c]||[]).forEach(([d,f])=>{if(!(String(bars[0].d)<d))return;const big=Math.abs(f-1)>.3;if(big)adjBig=true;bars.forEach(b=>{if(String(b.d)<d){b.o*=f;b.h*=f;b.l*=f;b.c*=f;if(b.m240!=null)b.m240*=f;if(big)b.v=Math.round(b.v/f)}})});\n"
        "  // 分割／減資等大跳空")
c = rep(c, "let split=false;for(let i=1;", "let split=adjBig;for(let i=1;")
c = rep(c, "切換 日→週→月漲幅（週＝5 個交易日前、月＝上個月同一天）", "切換 日→週→月漲幅（週＝5 個交易日前、月＝上個月同一天；已還原除權息／減資）")
c = rep(c, "⚠＝近 130 日有分割（價位概略還原，未還原除權息）", "⚠＝近 130 日有分割／面額變更；K 線與漲幅已還原除權息、減資、面額變更（跟 XQ 一致）")
open('scan.html' if prod else 'beta_scan_adj.html', 'w', encoding='utf-8').write(c)
print('ok', 'prod' if prod else 'beta')
