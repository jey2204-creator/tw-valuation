#!/usr/bin/env python3
"""K 線加財報公布日（方案②）：過去公布日（董事會通過＝財報、法說自結＝自結）畫直虛線＋小標；
下次公布日（公司已公告董事會日期 or 法定期限）在右側留白畫虛線＋倒數。用法：python3 patch_kfl.py index.html beta.html"""
import sys,re
src,dst=sys.argv[1],sys.argv[2]
s=open(src,encoding='utf-8').read()
def rep(old,new,n=1):
    global s
    assert s.count(old)==n,(old[:60],s.count(old))
    s=s.replace(old,new)

# 1) CSS：overlay 直線與標籤
rep(".klab{position:absolute;left:4px;top:2px;z-index:3;",
    ".kfl{position:absolute;inset:0;z-index:2;pointer-events:none;overflow:hidden}.kfl i{position:absolute;top:0;bottom:0;border-left:1.5px dashed var(--warm);opacity:.75}.kfl i.self{border-color:var(--accent)}.kfl i.next{border-color:var(--muted);opacity:.9}"
    ".kfl b{position:absolute;top:2px;transform:translateX(-50%);font-size:9px;font-weight:600;line-height:1.1;padding:1px 3px;border-radius:3px;color:#fff;background:var(--warm);white-space:nowrap;font-family:var(--f-num)}.kfl b.self{background:var(--accent)}.kfl b.next{background:var(--muted)}\n"
    ".klab{position:absolute;left:4px;top:2px;z-index:3;")

# 2) 畫圖前先算財報日；renderKl 把結果掛在 KL.fl
rep("  KL.rows=all;KL.days=dd;KL.id=id;klDraw();\n}",
    "  KL.rows=all;KL.days=dd;KL.id=id;KL.fl=await klFlashMarks(id,dd);if(id!==D.id)return;klDraw();\n}\n"
    "// ---- 財報公布日（data/flash.json）：過去＝董事會通過財報（board）／法說自結（self）的公告日；下次＝公司公告的董事會日期（cal），沒有就用法定期限 Q1 5/15、Q2 8/14、Q3 11/14、Q4 3/31 ----\n"
    "async function klFlashMarks(id,dd){\n"
    "  if(!NPF)NPF=fetch('data/flash.json?t='+Math.floor(Date.now()/6e5)).then(r=>r.ok?r.json():null).catch(()=>null);\n"
    "  const F=await NPF;if(!F)return null;\n"
    "  const roc=t=>{const m=/^(\\d{3})\\/(\\d{2})\\/(\\d{2})/.exec(t||'');return m?String(1911+ +m[1])+m[2]+m[3]:null};\n"
    "  const past={};(F.items||[]).filter(x=>x.c===id).forEach(x=>{const d=roc(x.t);if(!d)return;const k=x.k==='self'?'self':'board';if(!past[d]||k==='board')past[d]={d,k,q:x.q,eps:x.s&&x.s.eps}});\n"
    "  const P=Object.values(past).sort((a,b)=>a.d<b.d?-1:1);\n"
    "  // 下一季：最近一次董事會通過的季別 +1；只有自結的季（台積電 10/15 法說）→ 董事會財報還沒出，下次就是那一季\n"
    "  const bq=P.filter(x=>x.k==='board').map(x=>x.q).sort().pop();\n"
    "  let nq;if(bq){const y=+bq.slice(0,4),q=+bq[5];nq=q===4?`${y+1}Q1`:`${y}Q${q+1}`}\n"
    "  else{const sq=P.map(x=>x.q).sort().pop();if(sq)nq=sq}\n"
    "  const today=F.today||new Date().toISOString().slice(0,10);\n"
    "  let next=null;\n"
    "  if(nq){const y=+nq.slice(0,4),q=+nq[5];const cal=(F.cal||[]).find(x=>x.c===id&&x.q===nq);\n"
    "    const dl={1:`${y}-05-15`,2:`${y}-08-14`,3:`${y}-11-14`,4:`${y+1}-03-31`}[q];\n"
    "    const d=cal?cal.d:dl;if(d>=today)next={d:d.replace(/-/g,''),q:nq,legal:!cal,dl}}\n"
    "  return {past:P,next,today:today.replace(/-/g,'')};\n"
    "}\n"
    "// 今天之後到下次公布日的交易日（跳過週末，國定假日不算；最多 N 根）\n"
    "function klFutureDays(from,to,max){const out=[];let d=new Date(+from.slice(0,4),+from.slice(4,6)-1,+from.slice(6));\n"
    "  while(out.length<max){d.setDate(d.getDate()+1);const s=d.getFullYear()+String(d.getMonth()+1).padStart(2,'0')+String(d.getDate()).padStart(2,'0');if(s>to)break;if(d.getDay()===0||d.getDay()===6)continue;out.push(s)}\n"
    "  return out}")

# 3) 系列資料：右側補空白天數到下次公布日
rep("    if(m5[i]!=null)l5.push({time:tm,value:m5[i]});",
    "    if(m5[i]!=null)l5.push({time:tm,value:m5[i]});")
rep("  const opt={layout:{background:{type:'solid',color:'transparent'},",
    "  // 下次財報在 12 個交易日內 → 右邊留白到那天（空白點讓四張圖一起延伸）\n"
    "  const FL=KL.fl||{past:[],next:null},lastD=dd[all.length-1];\n"
    "  const fut=FL.next&&FL.next.d>lastD?klFutureDays(lastD,FL.next.d,13):[];\n"
    "  const ft=s=>({year:+s.slice(0,4),month:+s.slice(4,6),day:+s.slice(6)});\n"
    "  if(fut.length>12)fut.length=0;   // 超過 12 根就不留白，只在摘要顯示（期限落在週末 → 線畫在前一個交易日）\n"
    "  fut.forEach(s=>{const tm=ft(s);cs.push({time:tm});vs.push({time:tm});fs.push({time:tm});ts.push({time:tm})});\n"
    "  const opt={layout:{background:{type:'solid',color:'transparent'},")

# 4) overlay：refit 後與可視範圍變動時重畫
rep("  const refit=()=>{eqW();[c,v,f,tc].forEach(x=>x.timeScale().fitContent())};\n  requestAnimationFrame(()=>{refit();requestAnimationFrame(refit)});",
    "  const refit=()=>{eqW();[c,v,f,tc].forEach(x=>x.timeScale().fitContent());klFlOverlay(c,FL,fut,dd,from)};\n  requestAnimationFrame(()=>{refit();requestAnimationFrame(refit)});\n"
    "  c.timeScale().subscribeVisibleLogicalRangeChange(()=>klFlOverlay(c,FL,fut,dd,from));")

rep("document.addEventListener('click',e=>{const b=e.target.closest('#klSeg button');",
    "// 財報公布日 overlay：四張圖各一層，直虛線（橘＝董事會通過財報、藍＝法說自結、灰＝下次），標籤只放主圖\n"
    "function klFlOverlay(c,FL,fut,dd,from){\n"
    "  const pan=['klBox','klVol','klF','klT'].map(id=>{let o=$(id).querySelector('.kfl');if(!o){o=document.createElement('div');o.className='kfl';$(id).appendChild(o)}o.innerHTML='';return o});\n"
    "  if(!FL)return;const ts=c.timeScale(),pw=ts.width()||$('klBox').clientWidth-60,vis=new Set(dd.slice(from));fut.forEach(s=>vis.add(s));\n"
    "  const marks=FL.past.filter(x=>vis.has(x.d)).map(x=>({...x,cls:x.k==='self'?'self':'',lab:(x.k==='self'?'自結':'財報')+x.q.slice(4)}));\n"
    "  if(FL.next&&fut.length)marks.push({d:fut[fut.length-1],cls:'next',lab:FL.next.q.slice(4)+(FL.next.legal?'≤':' ')+(+FL.next.d.slice(4,6))+'/'+(+FL.next.d.slice(6))});\n"
    "  let lastX=-99;marks.forEach(m=>{const x=ts.timeToCoordinate({year:+m.d.slice(0,4),month:+m.d.slice(4,6),day:+m.d.slice(6)});if(x==null||x<0)return;\n"
    "    pan.forEach((o,i)=>{const l=document.createElement('i');l.className=m.cls;l.style.left=x+'px';o.appendChild(l);\n"
    "      if(i===0){const b=document.createElement('b');b.className=m.cls;b.textContent=m.lab;b.style.left=Math.min(x,pw-18)+'px';if(x-lastX<34)b.style.top='14px';o.appendChild(b)}});lastX=x})}\n"
    "document.addEventListener('click',e=>{const b=e.target.closest('#klSeg button');")

# 5) 摘要加一行「下次財報」＋ 圖例說明
rep("  $('tKl').innerHTML=`均線 <strong>${bull",
    "  const NX=KL.fl&&KL.fl.next,PP=(KL.fl&&KL.fl.past||[]).slice(-1)[0];\n"
    "  const tdLeft=NX?klFutureDays(dd[last],NX.d,400).length:null;\n"
    "  const flTxt=NX?`📅 下次財報 <strong>${NX.q.slice(2)}</strong>：${NX.legal?`最晚 ${+NX.d.slice(4,6)}/${+NX.d.slice(6)}（法定期限，公司尚未公告董事會日期）`:`${+NX.d.slice(4,6)}/${+NX.d.slice(6)}（公司公告董事會日）`}，距今 <strong>${tdLeft}</strong> 個交易日`:(PP?`📅 ${PP.q.slice(2)} 財報已於 ${+PP.d.slice(4,6)}/${+PP.d.slice(6)} 公布`:'');\n"
    "  $('tKl').innerHTML=(flTxt?flTxt+'<br>':'')+`均線 <strong>${bull")
rep("$('fKl').textContent='紅漲綠跌；量圖細線＝5 日均量；外資、投信紅買綠賣（近 60 日）。按住看當天數字，左右拖曳、雙指縮放。'",
    "$('fKl').textContent='紅漲綠跌；量圖細線＝5 日均量；外資、投信紅買綠賣（近 60 日）。按住看當天數字，左右拖曳、雙指縮放。橘虛線＝董事會通過財報公告日、藍虛線＝法說自結公告日（多在盤後公告，股價反應看下一根 K 棒）、灰虛線＝下次財報（公司公告的董事會日，沒有就用法定期限，12 個交易日內才在右側留白）。'")

open(dst,'w',encoding='utf-8').write(s)
print('ok',len(s))
