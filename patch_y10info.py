#!/usr/bin/env python3
"""10年財報：浮動說明改成圖下方固定薄條（不擋圖）。
點柱子 → 圖下方一條顯示該期、只放目前頁籤相關的數字；點薄條展開全部 8 行；✕ 收起。
ECharts 浮窗以 CSS 隱藏，保留軸線指標（點到哪一期看得出來）。
用法：python3 patch_y10info.py beta.html beta.html
"""
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()

def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (s.count(old), old[:80])
    s = s.replace(old, new)

# 1. 薄條 markup
rep("""  <div class="chart" id="cY10" style="height:210px"></div>
  <p class="foot" id="fY10"></p>""",
"""  <div class="chart" id="cY10" style="height:210px"></div>
  <div class="y10info" id="y10Info" hidden><div class="t"><b id="y10IL"></b><span id="y10IS"></span><i id="y10IM">全部 ▾</i><button type="button" id="y10IX" aria-label="收起">✕</button></div><div class="a" id="y10IA"></div></div>
  <p class="foot" id="fY10"></p>""")

# 2. CSS
rep(""".y10msg{font-size:13px;color:var(--muted);padding:18px 0;text-align:center}""",
""".y10msg{font-size:13px;color:var(--muted);padding:18px 0;text-align:center}
.y10tt{display:none!important}
.y10info{margin:2px 0 4px;padding:5px 8px;border:1px solid var(--line);border-radius:8px;background:var(--bg);font-size:12px;line-height:1.45}
.y10info .t{display:flex;align-items:baseline;gap:6px}
.y10info .t b{font-family:'IBM Plex Mono',ui-monospace,monospace;flex:none}
.y10info .t span{flex:1;min-width:0}
.y10info .t i{font-style:normal;color:var(--accent);font-size:11px;flex:none;cursor:pointer}
.y10info .t button{flex:none;font:inherit;font-size:12px;line-height:1;border:0;background:none;color:var(--muted);padding:0 0 0 4px;cursor:pointer}
.y10info .a{display:none;color:var(--muted);margin-top:3px;padding-top:3px;border-top:1px dashed var(--line)}
.y10info.open .a{display:block}
.y10info .up{color:var(--up)}.y10info .dn{color:var(--down)}""")

# 3. tooltip formatter → 寫進薄條；浮窗本身用 class 隱藏
rep("""  o.tooltip.formatter=ps=>{const x=R[ps[0].dataIndex],L=[`<b>${x.ttm?'近四季（'+Y10.asof+' 止）':x.l+(x.fl?'（財報快訊自結）':'')}</b>`];""",
"""  o.tooltip.className='y10tt';o.tooltip.transitionDuration=0;
  o.tooltip.formatter=ps=>{const x=R[ps[0].dataIndex];y10Info(x);return ''};
  const y10Lines=x=>{const L=[];""")
rep("""    if(x.pe!=null)L.push(`${x.ttm?'目前':'年均'}本益比 ${fmt(x.pe,1)} 倍`);return L.join('<br>')};""",
"""    if(x.pe!=null)L.push(`${x.ttm?'目前':'年均'}本益比 ${fmt(x.pe,1)} 倍`);return L};
  // 薄條：第一行只放目前頁籤相關的數字，其餘放展開區
  const y10Info=x=>{if(!x)return;const el=$('y10Info'),lab=x.ttm?'近四季':x.l+(x.fl?'（自結）':''),T=Y10T,up=v=>v==null?'—':`<span class="${v>0?'up':v<0?'dn':''}">${pct(v,T==='g'?1:0)}</span>`;
    let m='';
    if(T==='g')m=`營收 ${f(x.rev,0)} 億・年增 ${up(x.ry)}`;
    else if(T==='p')m=`毛利 ${f(x.gm,1)}%・營益 ${f(x.om,1)}%・淨利 ${f(x.nm,1)}%`;
    else if(T==='e')m=`EPS ${f(x.eps,2)}・年增 ${x.et||up(x.ey)}`+(x.div!=null?`・股利 ${f(x.div,2)}`:'');
    else if(T==='r')m=`ROE ${f(x.roe,1)}%・負債比 ${f(x.debt,1)}%`+(x.cov!=null?`・利息保障 ${x.cov>=50?'>50':fmt(x.cov,1)} 倍`:'');
    else if(T==='l')m=x.ib==null?'無負債明細':`有息 ${f(x.ib,0)}・無息 ${f(x.nib,0)}・現金 ${f(x.cash,0)}`+(x.nd!=null?`・<b>${x.nd<=0?'淨現金 '+f(-x.nd,0):'淨負債 '+f(x.nd,0)}</b> 億`:' 億');
    else if(T==='d')m=`股利 ${f(x.div,2)} 元・配息率 ${x.po==null?'—':fmt(x.po,0)+'%'}・殖利率 ${x.yld==null?'—':fmt(x.yld,1)+'%'}`;
    else if(T==='u')m=`ROE ${f(x.roe,1)}%＝淨利率 ${f(x.nm,1)}% × 周轉 ${x.at==null?'—':fmt(x.at,2)} × 乘數 ${x.lev==null?'—':fmt(x.lev,2)}`;
    else m=`營業現金流 ${f(x.ocf,0)}・自由現金流 ${f(x.fcf,0)}・淨利 ${f(x.ni,0)} 億`;
    $('y10IL').textContent=lab;$('y10IS').innerHTML=m;$('y10IA').innerHTML=y10Lines(x).join('<br>');el.hidden=false};""")

# 4. 換頁籤／重畫時收起薄條（資料對不上）
rep("""  $('y10U').textContent=Q?`${R.length}季`:`${R.length}年${R.some(x=>x.ttm)?'+近4季':''}`;""",
"""  $('y10U').textContent=Q?`${R.length}季`:`${R.length}年${R.some(x=>x.ttm)?'+近4季':''}`;
  {const el=$('y10Info');if(el){el.hidden=true;el.classList.remove('open');$('y10IM').textContent='全部 ▾'}}""")

# 5. 薄條互動：✕ 收起、點薄條展開全部
rep("""$('y10Per').addEventListener('click',e=>{""",
"""$('y10IX').addEventListener('click',e=>{e.stopPropagation();$('y10Info').hidden=true;try{mk('cY10').dispatchAction({type:'hideTip'})}catch(_){}});
$('y10Info').addEventListener('click',e=>{if(e.target.id==='y10IX')return;const el=$('y10Info'),o=el.classList.toggle('open');$('y10IM').textContent=o?'收起 ▴':'全部 ▾'});
$('y10Per').addEventListener('click',e=>{""")

# 6. 版本標
rep("""(Y10T==='l'?' v1109d':'')""", """(Y10T==='l'?' v1109e':'')""")

open(dst, 'w', encoding='utf-8').write(s)
print('ok')
