#!/usr/bin/env python3
"""2026-11-17 掃描頁「🌏 海外龍頭」加美股＋「全 美 日 韓」切換（接在 patch_ovs.py 之後）

用法：python3 patch_ovus.py           → 讀 scan.html，輸出 beta_scan_ovus.html
      python3 patch_ovus.py prod      → 直接改 scan.html（已套用過會因 assert 中止）

起因：世杰說海外龍頭想看美股，選「①併進同一排＋②加切換鈕」。
做法：
  1. 名單多讀 themes.json 的 us 欄位（代號清單），順序 美→日→韓；日 K 同樣來自 data/ovs.json（fetch_ovs.py 已加美股）。
  2. 標題列：「🌏 海外龍頭 N」＋「全｜美 11/16｜日 11/17｜韓 11/17」切換鈕（鈕上的日期＝該市場最新資料日）＋「收合」。
     只有一個市場的主題不顯示「全」。11/17 23:02 世杰要求「每次換主題自動回到全」→ 選擇不記在手機，pick() 換主題時重設。
  3. 美股小卡只顯示代號（右上標「美」）；放大卡標題多顯示中文名（us/data/index.json 的 cn，有才顯示），右下連到 us/#代號。
"""
import sys

PROD = len(sys.argv) > 1 and sys.argv[1] == 'prod'
SRC = 'scan.html'
OUT = 'scan.html' if PROD else 'beta_scan_ovus.html'
VER = 'v1117g'

s = open(SRC, encoding='utf-8').read()
assert 'ovPaint' in s, '要先套 patch_ovs.py'
assert 'OVMK' not in s, '已套用過'


def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (s.count(old), old[:80])
    s = s.replace(old, new)


# ---- CSS：標題列從一顆按鈕改成一列（標題＋切換鈕＋收合）----
rep('.ovs .grid{padding:3px 5px 2px}',
    '.ovs-t button{border:0;background:none;color:inherit;font:inherit;padding:0;margin:0;-webkit-tap-highlight-color:transparent;white-space:nowrap}\n'
    '.ovs-t{line-height:24px;gap:6px}\n'
    '.ovs-t .fs{display:flex;gap:3px;min-width:0}\n'
    '.ovs-t .fs button{font:500 11px/22px var(--f-body);padding:0 7px;border-radius:11px;background:var(--chip);color:var(--muted)}\n'
    '.ovs-t .fs button[aria-pressed=true]{background:var(--sel);color:var(--selfg);font-weight:700}\n'
    '.ovs-t .cl{margin-left:auto;color:var(--muted);font-weight:400;font-size:11px;flex:none}\n'
    '.ovs .grid{padding:3px 5px 2px}')

# ---- 名單：美→日→韓 ----
rep("  return [...(t.jp||b.jp||[]).map(x=>['jp'+x[0],x[1]]),...(t.kr||b.kr||[]).map(x=>['kr'+x[0],x[1]])]}",
    "  return [...(t.us||b.us||[]).map(x=>['us'+String(x).toUpperCase(),'']),...(t.jp||b.jp||[]).map(x=>['jp'+x[0],x[1]]),...(t.kr||b.kr||[]).map(x=>['kr'+x[0],x[1]])]}")
rep("return {ov:1,m:o.m,mk:o.m==='jp'?'日':'韓',c:k,cd:o.c,n:nm||o.n,bars,",
    "return {ov:1,m:o.m,mk:OVMK[o.m]||'外',c:k,lk:o.c,cd:o.m==='us'?(o.cn||''):o.c,n:o.m==='us'?o.c:(nm||o.n),bars,")
rep("let OVS,OVR=[],OVK='',OVC=!!store.get('scanOvC'),OVB=null;",
    "let OVS,OVR=[],OVK='',OVC=!!store.get('scanOvC'),OVB=null,OVF='a';const OVMK={us:'美',jp:'日',kr:'韓'};")
# 放大卡連結：美股 us/#代號
rep('`<a href="${r.m}/#${esc(r.cd)}">${r.mk}股站 →</a>`', '`<a href="${r.m}/#${esc(r.lk)}">${r.mk}股站 →</a>`')

# ---- ovPaint 整段換掉 ----
a = s.index("function ovPaint(){")
b = s.index("// ---- 畫 K：mini（小卡）與 full（放大卡） ----")
s = s[:a] + r'''function ovPaint(){const el=$('ovs');if(!el)return;const ids=ovIds(cur);if(!ids.length){el.hidden=true;OVK='';return}
  if(OVS===undefined)ovLoad();if(!OVS){el.hidden=true;OVK='';return}
  const key=[cur.id,N,CHGP,OVC,OVF,OVS.updated,innerWidth].join('|');if(key===OVK&&!el.hidden)return;OVK=key;
  const A=ids.map(([k,n])=>ovBuild(k,n)).filter(Boolean);if(!A.length){el.hidden=true;return}
  // 2026-11-17：「全 美 日 韓」切換；鈕上的日期＝該市場最新資料日（美股比日韓晚一個晚上，不是同一個交易日）
  const MK=['us','jp','kr'].filter(m=>A.some(r=>r.m===m)),F=MK.includes(OVF)?OVF:'a',R=F==='a'?A:A.filter(r=>r.m===F);R.ov=true;OVR=R;
  const dd=m=>md(A.filter(r=>r.m===m).map(r=>r.d).sort().pop());
  el.hidden=false;
  el.innerHTML=`<div class="ovs-t"><button class="tt" aria-expanded="${!OVC}">🌏 海外龍頭 ${R.length}</button>${OVC?'':`<span class="fs">${MK.length>1?`<button data-f="a" aria-pressed="${F==='a'}">全</button>`:''}${MK.map(m=>`<button data-f="${m}" aria-pressed="${F===m||MK.length===1}" title="${OVMK[m]}股最新資料日 ${dd(m)}">${OVMK[m]} ${dd(m)}</button>`).join('')}</span>`}<button class="cl">${OVC?'展開 ▸':'收合 ▾'}</button></div>`+(OVC?'':`<div class="grid">${R.map((r,i)=>`<article class="km${r.brk&&r.chg>0?' hot':''}" data-i="${i}" role="button" tabindex="0">
    <div class="km-h">${nmB(r.n)}${r.m==='us'?'':`<span class="cd">${esc(r.cd)}</span>`}<span class="tg fx" title="${r.mk}股">${r.mk}</span></div>
    <div class="km-s"><span class="${cls(r.chg)}">${pct(r.chg)}</span>${CHGP!=='d'?`<span class="${cls(r[CHGK()])}">${CHGP==='w'?'週':'月'}${pct(r[CHGK()])}</span>`:''}<span class="vr${r.vr>=1.5?' hi':''}">量${r.vr==null?'—':r.vr.toFixed(1)+'×'}</span><span class="od">${md(r.d)}</span></div>
    <canvas class="km-cv"></canvas></article>`).join('')}</div>`);
  const tg=()=>{OVC=!OVC;store.set('scanOvC',OVC);ovPaint()};el.querySelector('.tt').onclick=tg;el.querySelector('.cl').onclick=tg;
  el.querySelectorAll('.fs button').forEach(b=>b.onclick=()=>{if(MK.length<2)return;OVF=b.dataset.f;ovPaint()});
  el.querySelectorAll('.km').forEach(k=>{const i=+k.dataset.i;drawK(k.querySelector('canvas'),R[i],N,{mini:true});k.onclick=()=>openSheet(R,i);k.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();openSheet(R,i)}}})}
''' + s[b:]

# ---- 換主題自動回到「全」（同一主題換日期、重畫不重設）----
rep("async function pick(sel){cur=sel;apClose();nxPaint();", "async function pick(sel){if(!cur||cur.id!==sel.id||cur.kind!==sel.kind)OVF='a';cur=sel;apClose();nxPaint();")

# ---- 版本、頁尾說明 ----
rep('<b>🌏 海外龍頭</b>＝這個主題對應的日股／韓股（跟首頁主題頁的「對應日股／韓股」同一份名單），Yahoo 收盤價、平日約 15:00 與 17:40 更新、<b>非即時</b>；',
    '<b>🌏 海外龍頭</b>＝這個主題對應的美股／日股／韓股（跟首頁主題頁的「對應美股／日股／韓股」同一份名單），順序美→日→韓，標題列「全 美 日 韓」可只看一國（鈕上的日期＝該市場最新資料日；換主題自動回到「全」）；Yahoo 收盤價、<b>非即時</b>：日韓平日約 15:00 與 17:40、美股約 05:30 與 08:00 更新。<b>美股收盤是台北清晨</b>，早上看到的是昨晚那根、比日韓早一步，不是同一個交易日，不要直接橫向比當日漲跌；')
rep('<span style="opacity:.5">v1117f</span>', '<span style="opacity:.5">' + VER + '</span>')

if not PROD:
    s = s.replace('<title>', '<title>β ', 1)
open(OUT, 'w', encoding='utf-8').write(s)
print('wrote', OUT, len(s))
