#!/usr/bin/env python3
"""財報公布日曆第 3 步：首頁入口清單加「📅 財報日曆」小卡；個股 K 線「下次財報」改用 flash.json 的 est（慣例推估）
用法：python3 patch_cal2.py index.html beta.html
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:70])
    s = s.replace(old, new)

# ① 首頁入口清單
rep('<a class="srlink" href="notice.html"><b>📢 注意／處置股</b><span id="ntSub">上市櫃注意、處置、快達處置名單</span></a>',
    '<a class="srlink" href="notice.html"><b>📢 注意／處置股</b><span id="ntSub">上市櫃注意、處置、快達處置名單</span></a><a class="srlink" href="flash.html#cal"><b>📅 財報日曆</b><span id="calSub">追蹤股近期公布日</span></a>')

# ② 首頁小卡文字：追蹤股（自選＋主題）本週／下週要公布的
rep("function renderHome(){\n  RANK=null;srHome();",
    """function renderHome(){
  RANK=null;srHome();try{calHome()}catch(e){}""")
rep("function renderHome(){", r"""function calHome(){
  if(!NPF)NPF=fetch('data/flash.json?t='+Math.floor(Date.now()/6e5)).then(r=>r.ok?r.json():null).catch(()=>null);
  NPF.then(F=>{const el=$('calSub');if(!el||!F)return;const E=F.est||[];if(!E.length){el.textContent='還沒有推估資料';return}
    const fav=store.get('fav')||[],pool=new Set([...THEMES.flatMap(t=>t.stocks.map(x=>x[0])),...fav]),today=F.today;
    const add=(d,n)=>new Date(new Date(d+'T00:00:00Z').getTime()+n*86400e3).toISOString().slice(0,10),dow=d=>new Date(d+'T00:00:00Z').getUTCDay();
    const w1=add(today,(8-dow(today))%7||7),w2=add(w1,7);
    const mine=E.filter(c=>pool.has(c.c)&&c.d>=today),tw=mine.filter(c=>c.d<w1),nw=mine.filter(c=>c.d>=w1&&c.d<w2),late=mine.filter(c=>c.src==='late');
    const nm=c=>c.n.replace(/\*$/,''),md=d=>(+d.slice(5,7))+'/'+(+d.slice(8)),tag=c=>c.src==='cal'?'✓':c.src==='late'?'⚠':'≈';
    const show=(tw.length?tw:nw).slice().sort((a,b)=>(fav.includes(b.c)-fav.includes(a.c))||(a.src==='late')-(b.src==='late')*-1||a.d.localeCompare(b.d)),lab=tw.length?'本週':'下週';   // 自選優先、再依日期
    if(!mine.length){el.textContent=`${E[0].q.slice(2)} 追蹤股都已公布`;return}
    el.textContent=`${lab} ${show.length} 家：`+show.slice(0,4).map(c=>`${nm(c)} ${md(c.d)}${tag(c)}`).join('、')+(show.length>4?` …（共 ${mine.length} 家待公布${late.length?`，⚠ ${late.length} 家晚於慣例`:''}）`:'')});
}
function renderHome(){""")

# ③ 個股 K 線：next 先看 cal，再看 est（慣例推估），最後法定期限
rep("    const d=cal?cal.d:dl;if(d>=today)next={d:d.replace(/-/g,''),q:nq,legal:!cal,dl}}",
    "    const est=!cal&&(F.est||[]).find(x=>x.c===id&&x.q===nq);const d=cal?cal.d:est?est.d:dl;if(d>=today)next={d:d.replace(/-/g,''),q:nq,legal:!cal&&!est,est:est?est.src:null,dl}}")
rep("const flTxt=NX?`📅 下次財報 <strong>${NX.q.slice(2)}</strong>：${NX.legal?`最晚 ${+NX.d.slice(4,6)}/${+NX.d.slice(6)}（法定期限，公司尚未公告董事會日期）`:`${+NX.d.slice(4,6)}/${+NX.d.slice(6)}（公司公告董事會日）`}，距今 <strong>${tdLeft}</strong> 個交易日`",
    "const flTxt=NX?`📅 下次財報 <strong>${NX.q.slice(2)}</strong>：${NX.legal?`最晚 ${+NX.d.slice(4,6)}/${+NX.d.slice(6)}（法定期限，公司尚未公告董事會日期）`:NX.est?`約 ${+NX.d.slice(4,6)}/${+NX.d.slice(6)}（${NX.est==='late'?'⚠ 上一季這時候已公布，這季還沒；法定期限':'≈ 依'+(NX.est==='ly'?'去年同季':'上一季')+'慣例推估，誤差 1～2 天；法定期限'} ${+NX.dl.slice(5,7)}/${+NX.dl.slice(8)}）`:`${+NX.d.slice(4,6)}/${+NX.d.slice(6)}（✓ 公司公告董事會日）`}，距今 <strong>${tdLeft}</strong> 個交易日`")
rep("lab:FL.next.q.slice(4)+(FL.next.legal?'≤':' ')+(+FL.next.d.slice(4,6))+'/'+(+FL.next.d.slice(6))",
    "lab:FL.next.q.slice(4)+(FL.next.legal?'≤':FL.next.est?'≈':' ')+(+FL.next.d.slice(4,6))+'/'+(+FL.next.d.slice(6))")
rep("灰虛線＝下次財報（公司公告的董事會日，沒有就用法定期限，12 個交易日內才在右側留白）",
    "灰虛線＝下次財報（✓ 公司公告的董事會日＞≈ 依上一季慣例推估＞≤ 法定期限，12 個交易日內才在右側留白）")

open(dst, 'w', encoding='utf-8').write(s)
print('ok', dst, len(s))
