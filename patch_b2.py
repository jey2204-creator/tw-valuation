#!/usr/bin/env python3
"""2026-11-20 掃描頁：41～80 檔的名單（0050、成交值／成交量／週轉率前50、注意股）進頁面就分兩批全部問完，不等背景預抓。
起因：11/20 12:48 世杰貼 0050 名單截圖「35 檔仍為昨收」——>40 檔的名單前景只問畫面上的小卡，其餘靠背景；背景（證交所 MIS）連兩批沒回就暫停 2 分鐘。
做法：liveRefresh() 名單 41～LV_ALL(80) 檔時 ids＝整份（畫面上的排前面），每 40 檔一批依序問、每批回來就重畫；>80 檔（證交所產業）照舊只問畫面上的 40 檔。
用法：python3 patch_b2.py → beta_scan_b2.html；python3 patch_b2.py prod → scan.html。只能對 v1120b 跑一次。
"""
import sys
prod = len(sys.argv) > 1 and sys.argv[1] == 'prod'
s = open('scan.html', encoding='utf-8').read()
E = [
 ("const LV_MAX=40,LV_FRESH=50000,", "const LV_MAX=40,LV_ALL=80,LV_FRESH=50000,"),
 ("  if(all.length>LV_MAX){const vis=all.filter(c=>VISIBLE.has(c));ids=(vis.length?vis:all).slice(0,LV_MAX)}\n",
  "  if(all.length>LV_ALL){const vis=all.filter(c=>VISIBLE.has(c));ids=(vis.length?vis:all).slice(0,LV_MAX)}\n"
  "  else if(all.length>LV_MAX)ids=[...all.filter(c=>VISIBLE.has(c)),...all.filter(c=>!VISIBLE.has(c))];   // 2026-11-20：41～80 檔整份問完（畫面上的先問），下面每 40 檔一批\n"),
 ("  try{const ctl=new AbortController(),to=setTimeout(()=>ctl.abort(),20000);\n", "  try{for(let k=0;k<ids.length;k+=LV_MAX){const part=ids.slice(k,k+LV_MAX);const ctl=new AbortController(),to=setTimeout(()=>ctl.abort(),20000);\n"),
 ("    const res=await fetch(lvUrl(ids)+(pri?'&p=1':''),{signal:ctl.signal,cache:'no-store'});clearTimeout(to);\n    const j=await res.json();if(j&&j.q){liveMerge(j,ids,false);\n      if(!open)liveAfterClose++;\n      LIVE_DBG={at:new Date().toTimeString().slice(0,8),ask:ids,",
  "    const res=await fetch(lvUrl(part)+(pri?'&p=1':''),{signal:ctl.signal,cache:'no-store'});clearTimeout(to);\n    const j=await res.json();if(j&&j.q){liveMerge(j,part,false);\n      if(!open&&!k)liveAfterClose++;\n      LIVE_DBG={at:new Date().toTimeString().slice(0,8),ask:part,"),
 ("      lvRepaint()}\n  }catch(e){}\n  liveBusy=false;pfRun()}", "      lvRepaint()}\n  }}catch(e){}\n  liveBusy=false;pfRun()}"),
 ("v1120b", "v1120c"),
]
for a, b in E:
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)
if not prod:
    s = s.replace('<title>', '<title>[beta] ', 1)
open('scan.html' if prod else 'beta_scan_b2.html', 'w', encoding='utf-8').write(s)
print('ok')
