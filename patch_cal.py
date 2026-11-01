#!/usr/bin/env python3
"""財報快訊頁「即將公布」改三段式日曆（本週／下週／之後，含推估日＋來源標記，⭐／全市場切換）
用法：python3 patch_cal.py flash.html beta_flash.html
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:70])
    s = s.replace(old, new)

rep(".cday a.w{color:var(--accent);font-weight:700}",
    ".cday a.w{color:var(--accent);font-weight:700}\n"
    ".cday a i{font-style:normal;font-size:10px;color:var(--muted);margin-left:1px}.cday a.cal i{color:var(--accent)}.cday a.late i{color:var(--warm)}\n"
    ".cwk{padding:5px 12px 2px;border-top:1px solid var(--line);font-size:12px;font-weight:700;display:flex;justify-content:space-between;align-items:center}.cwk small{font-weight:400;color:var(--muted)}\n"
    ".cday.today h3{color:var(--accent);font-weight:700}\n"
    ".cseg{display:inline-flex;border:1px solid var(--line);border-radius:999px;overflow:hidden;font-size:11px;font-weight:400}.cseg button{font:inherit;border:0;background:none;color:var(--muted);padding:2px 9px;cursor:pointer;white-space:nowrap}.cseg button[aria-pressed=true]{background:var(--accent);color:#fff}\n"
    ".cmore{display:block;text-align:center;font-size:12px;color:var(--accent);padding:6px;cursor:pointer}")

rep('<details class="cal" id="calBox"><summary><span><span class="tw">▸</span> 📅 即將公布</span><small id="calN"></small></summary><div id="cal"></div></details>',
    '<details class="cal" id="calBox"><summary><span><span class="tw">▸</span> 📅 即將公布</span><small id="calN"></small></summary><div class="cwk" style="border-top:0;padding-top:2px"><span class="cseg" id="calSeg"><button type="button" data-m="w" aria-pressed="true">⭐ 追蹤</button><button type="button" data-m="a" aria-pressed="false">全市場</button></span><small id="calHint">✓ 已公告　≈ 慣例推估　⚠ 晚於慣例　≤ 期限</small></div><div id="cal"></div></details>')

old = s[s.index("function renderCal(){"):s.index("async function main(){")]
new = r'''let CALM=store.get('calM')||'w',CALX=false;
function renderCal(){
  const E=(D.est&&D.est.length?D.est:(D.cal||[]).map(c=>({...c,src:'cal'}))),q=E.length?E[0].q:null;
  const today=D.today||new Date(Date.now()+8*3600e3).toISOString().slice(0,10);
  const add=(d,n)=>new Date(new Date(d+'T00:00:00Z').getTime()+n*86400e3).toISOString().slice(0,10),dow=d=>new Date(d+'T00:00:00Z').getUTCDay();
  const w1=add(today,(8-dow(today))%7||7),w2=add(w1,7);   // w1＝下個週一（今天是週日→明天）；本週＝今天～週日、下週＝w1～w2
  const all=E.filter(c=>c.d>=today||c.src==='cal'),mine=all.filter(c=>WATCH.has(c.c)),L=CALM==='w'?mine:all;
  $('calN').textContent=`${q?q.slice(2).replace('Q','Q'):''} 待公布 ${all.length} 家`+(mine.length?` · ⭐${mine.length}`:'');
  $('calSeg').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.m===CALM));
  const wk='日一二三四五六',TAG={cal:'✓',ly:'≈',pq:'≈',late:'⚠',dl:'≤'};
  const by={};L.forEach(c=>(by[c.d]=by[c.d]||[]).push(c));
  const days=Object.keys(by).sort(),sec=[['本週',d=>d<w1],['下週',d=>d>=w1&&d<w2],['之後',d=>true]];
  let html='',used=new Set(),shown=0,LIM=CALM==='a'&&!CALX?40:1e9;
  for(const [name,ok] of sec){const ds=days.filter(d=>!used.has(d)&&ok(d));if(!ds.length)continue;ds.forEach(d=>used.add(d));
    const n=ds.reduce((a,d)=>a+by[d].length,0);
    html+=`<div class="cwk">${name}<small>${n} 家</small></div>`;
    for(const d of ds){const arr=by[d].sort((a,b)=>(WATCH.has(b.c)-WATCH.has(a.c))||(a.src==='cal'?-1:0)-(b.src==='cal'?-1:0));
      if(shown>=LIM){html+=`<span class="cmore" id="calMore">還有 ${L.length-shown} 家 → 展開全部</span>`;break}
      const show=arr.slice(0,Math.max(0,LIM-shown));shown+=show.length;
      html+=`<div class="cday${d===today?' today':''}"><h3>${+d.slice(5,7)}/${+d.slice(8)}（${wk[dow(d)]}）</h3><div>`+
        show.map(c=>`<a href="./#${c.c}" class="${WATCH.has(c.c)?'w ':''}${c.src}">${WATCH.has(c.c)&&CALM==='a'?'⭐':''}${c.n}<i>${TAG[c.src]||''}</i></a>`).join('')+(show.length<arr.length?`<span class="mu" style="font-size:11px">…等 ${arr.length} 家</span>`:'')+'</div></div>'}
    if(shown>=LIM)break}
  $('cal').innerHTML=html||`<div class="cday mu">${CALM==='w'?'追蹤的股票這一季都公布完了，或還沒加自選／主題':'沒有資料'}</div>`;
  const m=$('calMore');if(m)m.onclick=()=>{CALX=true;renderCal()};
  if(!renderCal.init){renderCal.init=true;$('calBox').open=mine.some(c=>c.d>=today&&c.d<w1)}   // 只有第一次載入決定自動展開；切換⭐／全市場、展開全部都維持原狀
}
$('calSeg').addEventListener('click',e=>{const b=e.target.closest('button[data-m]');if(!b)return;CALM=b.dataset.m;CALX=false;store.set('calM',CALM);renderCal()});
'''
s = s.replace(old, new)
open(dst, 'w', encoding='utf-8').write(s)
print('ok', dst, len(s))
