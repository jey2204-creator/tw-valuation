"""興櫃股 beta：index.html → beta.html
- 搜尋清單加入指定興櫃股（EMG，先只放 3595 山太士）
- 個股頁 live()：興櫃半年報（只有 06-30、12-31）依月營收比重拆成兩季（營收精確、其他科目為估算）
- FinMind 無興櫃本益比／淨值比 → 用月底收盤 ÷ 近4季 EPS、÷ 每股淨值自算河流圖
- 興櫃營收 <10 億時保留兩位小數（避免 0.93 億被四捨五入成 1）
- 標頭標示「興櫃」與資料說明
"""
import pathlib, re

src = pathlib.Path("index.html").read_text("utf-8")
s = src


def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, f"預期 {count} 處，找到 {n} 處：{old[:60]}"
    s = s.replace(old, new)


# 1) 興櫃清單＋載入後併入 LIST
rep("async function live(id){",
    """const EMG=[['3595','山太士','興櫃','光電業']];   // 興櫃 beta：先只放這幾檔
// 興櫃半年報：某年只有 06-30（無 03-31）或只有 12-31（無 09-30）→ 依月營收比重拆成兩季；回傳 [新 fs, 拆算季標籤]
function emgSplit(fs,rvd){
  const by={};fs.forEach(r=>{(by[r.date]=by[r.date]||[]).push(r)});
  const out=fs.slice(),mark=[];
  const qr=(y,n)=>{let t=0,c=0;for(let i=1;i<=3;i++){const v=rvd[`${y}-${String((n-1)*3+i).padStart(2,'0')}`];if(v!=null){t+=v;c++}}return c===3?t:null};
  Object.keys(by).forEach(d=>{const y=+d.slice(0,4),md=d.slice(5);
    const pair=md==='06-30'?['03-31',1,2]:md==='12-31'?['09-30',3,4]:null;if(!pair)return;
    if(by[`${y}-${pair[0]}`])return;   // 已有前一季 → 本來就是單季
    const a=qr(y,pair[1]),b=qr(y,pair[2]),w=a!=null&&b!=null&&a+b>0?a/(a+b):0.5;
    const rows=by[d];
    rows.forEach(r=>{const i=out.indexOf(r);if(i<0||r.value==null)return;
      out[i]={...r,value:r.type==='EPS'?+(r.value*(1-w)).toFixed(2):r.value*(1-w)};
      out.push({...r,date:`${y}-${pair[0]}`,value:r.type==='EPS'?+(r.value*w).toFixed(2):r.value*w})});
    const yy=String(y).slice(2);mark.push(`${yy}Q${pair[1]}`,`${yy}Q${pair[2]}`)});
  return [out,mark];
}
async function live(id){""")
rep("  try{const r=await fetch('data/themes.json?t='+Date.now());if(r.ok)BASE=(await r.json()).themes||[]}catch(e){}",
    "  EMG.forEach(e=>{if(!LIST.some(s=>s[0]===e[0]))LIST.push(e)});\n"
    "  try{const r=await fetch('data/themes.json?t='+Date.now());if(r.ok)BASE=(await r.json()).themes||[]}catch(e){}")

# 2) live()：拆半年報、營收小數、自算河流圖
rep("  const [px,per,fs,rv,bs]=await Promise.all([fm('TaiwanStockPrice',id,start)",
    "  const emg=EMG.some(e=>e[0]===id);let hs=[];\n  let [px,per,fs,rv,bs]=await Promise.all([fm('TaiwanStockPrice',id,start)")
rep("  const rev=Object.keys(rvd).sort().map(k=>{const p=rvd[`${+k.slice(0,4)-1}${k.slice(4)}`];return [k,Math.round(rvd[k]),",
    "  if(emg)[fs,hs]=emgSplit(fs,rvd);\n"
    "  const r1=v=>emg&&Math.abs(v)<10?+v.toFixed(2):Math.round(v);\n"
    "  const rev=Object.keys(rvd).sort().map(k=>{const p=rvd[`${+k.slice(0,4)-1}${k.slice(4)}`];return [k,r1(rvd[k]),")
rep("q.push([`${d.slice(2,4)}Q${+d.slice(5,7)/3}`,Math.round(rv_/1e8),",
    "q.push([`${d.slice(2,4)}Q${+d.slice(5,7)/3}`,r1(rv_/1e8),")
rep("  const P=px.slice().sort((a,b)=>a.date<b.date?-1:1),E=per.slice().sort((a,b)=>a.date<b.date?-1:1);\n  return {id,",
    """  let fbPe=null,fbPb=null;
  if(!per.length&&q.length>=4){   // 興櫃沒有官方本益比／淨值比 → 自算：月底收盤 ÷ 近4季 EPS、÷ 每股淨值
    const qe=q.map(x=>({end:`20${x[0].slice(0,2)}-${String(+x[0][3]*3).padStart(2,'0')}`,eps:x[5]}));
    const eq=bs.filter(r=>r.type==='EquityAttributableToOwnersOfParent'||r.type==='Equity').sort((a,b)=>a.date<b.date?-1:1);
    const sc=bs.filter(r=>r.type==='OrdinaryShare').sort((a,b)=>a.date<b.date?-1:1);
    const at=(arr,k)=>{let v=null;arr.forEach(r=>{if(r.date.slice(0,7)<=k)v=r.value});return v};
    const ttmAt=k=>{const i=qe.map(x=>x.end<=k).lastIndexOf(true);return i>=3?qe.slice(i-3,i+1).reduce((a,x)=>a+x.eps,0):null};
    const bvAt=k=>{const e=at(eq,k),c=at(sc,k);return e&&c?e/(c/10):null};
    Object.keys(pm).sort().forEach(k=>{const c=pm[k].close,t=ttmAt(k),b=bvAt(k);if(t==null&&b==null)return;
      const pe=t>0?+(c/t).toFixed(1):null,pb=b>0?+(c/b).toFixed(2):null;riv.push([k,c,pe?+(c/pe).toFixed(2):null,pb?+(c/pb).toFixed(2):null,pe,pb])});
    const lc=px.slice().sort((a,b)=>a.date<b.date?-1:1).pop(),lk=lc.date.slice(0,7),t=ttmAt(lk),b=bvAt(lk);
    fbPe=t>0?+(lc.close/t).toFixed(1):null;fbPb=b>0?+(lc.close/b).toFixed(2):null;
  }
  const P=px.slice().sort((a,b)=>a.date<b.date?-1:1),E=per.slice().sort((a,b)=>a.date<b.date?-1:1);
  return {id,emg:emg||undefined,hsplit:hs.length?hs:undefined,""")
rep("pe:E.length?E[E.length-1].PER:null,pb:E.length?E[E.length-1].PBR:null}",
    "pe:E.length?E[E.length-1].PER:fbPe,pb:E.length?E[E.length-1].PBR:fbPb}")

# 3) 興櫃股不吃舊快取（避免其他版本存過的空資料）
rep("  const k='live5_'+id,c=store.get(k);", "  const k=(EMG.some(e=>e[0]===id)?'liveE1_':'live5_')+id,c=store.get(k);")

# 4) 標頭說明
rep("    $('meta').innerHTML=(it?`${it[2]}・${it[3]}`:'')+(D.live?' <span class=\"live\">即時查詢</span>':' <span class=\"live\">追蹤清單</span>');",
    "    $('meta').innerHTML=(it?`${it[2]}・${it[3]}`:'')+(D.live?' <span class=\"live\">即時查詢</span>':' <span class=\"live\">追蹤清單</span>')"
    "+(D.emg?`<div class=\"emgn\">⚠️ 興櫃股：無漲跌幅、成交稀，價格波動大。本益比／淨值比為本站自算（月底收盤 ÷ 近4季 EPS／每股淨值）`"
    "+(D.hsplit?`；${D.hsplit[0]}～${D.hsplit[D.hsplit.length-1]} 間有半年報，${D.hsplit.length} 季依月營收比重拆算（營收準確，毛利、營益、淨利、EPS 為估算）`:'')+`</div>`:'');")
s = s.replace("</style>", ".emgn{font-size:11px;line-height:1.45;margin-top:4px;padding:5px 8px;border-radius:8px;background:#fff7e0;color:#7a5200}\n"
    "@media (prefers-color-scheme:dark){.emgn{background:#3a2e10;color:#f0cf80}}\n</style>", 1)

assert s != src
pathlib.Path("beta.html").write_text(s, "utf-8")
print("beta.html 已產生", len(s))
