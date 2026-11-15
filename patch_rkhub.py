#!/usr/bin/env python3
"""2026-11-15 首頁入口清單第 3 列加「💰 成交值排行」（🔥 主力訊號下面、注意／處置股上面）。
左邊標題＋副標（第 1 名・🆕 新上榜；日期放不下，收在 title）→ scan.html#vtop；右邊兩顆「值」「量」→ #vtop／#qtop。
副標讀 data/rank/home.json（fetch_rank.py 產生的小檔），照掃描頁記住的市場（scanRkM）與 ETF 開關（scanRkE）。
用法：python3 patch_rkhub.py → beta.html；python3 patch_rkhub.py prod → index.html
"""
import sys
prod=len(sys.argv)>1 and sys.argv[1]=='prod'
s=open('index.html',encoding='utf-8').read()

# 1) 列
k='<a class="srlink" href="notice.html"><b>📢 注意／處置股</b>';assert s.count(k)==1
row=('<div class="srlink rkrow" id="rkRow"><a class="rkmain" href="scan.html#vtop"><b>💰 成交值排行</b><span id="rkSub">成交值／量前 50</span></a>'
     '<a class="rkbt" href="scan.html#vtop" aria-label="成交值前 50">值</a><a class="rkbt" href="scan.html#qtop" aria-label="成交量前 50">量</a></div>')
s=s.replace(k,row+k)

# 2) CSS
css=('.hub>.rkrow{padding:0 8px 0 0;gap:6px}'
     '.hub>.rkrow .rkmain{flex:1;min-width:0;display:flex;justify-content:space-between;align-items:center;gap:8px;min-height:44px;padding-left:12px;color:var(--fg);text-decoration:none}'
     '.hub>.rkrow span::after{content:none}'
     '.hub>.rkrow .rkbt{flex:none;display:flex;align-items:center;justify-content:center;min-width:38px;height:28px;padding:0 4px;box-sizing:border-box;border:1px solid var(--line);border-radius:8px;font-size:13px;font-weight:600;color:var(--fg);text-decoration:none;position:relative}'
     '.hub>.rkrow .rkbt::before{content:"";position:absolute;inset:-8px -3px}'
     '.hub>.rkrow .rkbt::after{content:"›";margin-left:3px;color:var(--muted);font-weight:400}')
a='.hub>details.ind[open]>summary span::after{transform:rotate(90deg)}';assert s.count(a)==1
s=s.replace(a,a+'\n'+css)

# 3) 副標
js='''function rkHome(){
  fetch('data/rank/home.json?t='+Math.floor(Date.now()/3e5)).then(r=>r.ok?r.json():null).then(h=>{const el=$('rkSub');if(!el||!h||!h.asof)return;
    let m='a',e='1';try{const x=localStorage.getItem('scanRkM');if(x==='L'||x==='O')m=x;if(localStorage.getItem('scanRkE')==='0')e='0'}catch(x){}
    const t=(h.v||{})[m+e]||(h.v||{}).a1;if(!t)return;
    const f=t[2]>=100?Math.round(t[2]).toLocaleString():t[2].toFixed(1);
    const md=`${+h.asof.slice(4,6)}/${+h.asof.slice(6)}`;el.textContent=(t[1].length<=4?t[1]+' ':'')+`${f}億`+(t[3]!=null?`・🆕${t[3]}`:'');
    el.title=`${md} ${m==='L'?'上市':m==='O'?'上櫃':'上市櫃合併'}${e==='0'?'（不含 ETF）':''}成交值第 1 名；🆕＝前一個交易日不在前 50 的檔數`}).catch(()=>{})}
'''
k2='function renderHome(){\n  RANK=null;srHome();try{calHome()}catch(e){}';assert s.count(k2)==1
s=s.replace(k2,js+k2+'try{rkHome()}catch(e){}')

old='<span style="opacity:.5">v1115j</span>';assert s.count(old)==1;s=s.replace(old,'<span style="opacity:.5">v1115k</span>')
if not prod:s=s.replace('<title>','<title>[beta] ',1)
open('index.html' if prod else 'beta.html','w',encoding='utf-8').write(s);print('ok')
