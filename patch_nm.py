#!/usr/bin/env python3
"""2026-11-13 掃描頁小卡股名被截斷（4 字股名只剩 1 個字）。
A：第一列拿掉重複的「昨／即」小標（第二列已有「昨▲x%」，沒有「昨」字＝即時）；延／未／○ 這三種例外狀態保留。
B：股名依字數縮字（≤3 字 12.5px、4 字 10.5px、≥5 字 9px），K 線與估值兩種小卡都套用。
用法：python3 patch_nm.py scan.html beta_scan_nm.html
"""
import sys
src,dst=sys.argv[1],sys.argv[2];s=open(src,encoding='utf-8').read()
def rep(old,new,n=1):
    global s;assert s.count(old)==n,(s.count(old),old[:80]);s=s.replace(old,new)
# B：縮字 class
rep('''.km-h .cd{font:600 9px var(--f-num);color:var(--muted);letter-spacing:.02em;flex:none}''',
    '''/* 2026-11-13 長股名縮字，避免被截成「雷…」 */
.km-h{gap:3px}.km-h b.n4{font-size:10.5px;letter-spacing:-.03em}.km-h b.n5{font-size:9px;letter-spacing:-.04em}
.km-h .cd{font:600 9px var(--f-num);color:var(--muted);letter-spacing:.02em;flex:none}''')
rep('''function liveTag(r){''',
    '''function nmB(n){const L=[...String(n)].length;return `<b${L>=5?' class="n5"':L===4?' class="n4"':''}>${esc(n)}</b>`}
function liveTag(r){''')
rep('''<span class="rk">${i+1}</span><b>${esc(r.n)}</b>''','''<span class="rk">${i+1}</span>${nmB(r.n)}''',2)
# A：即／昨 不再顯示小標
rep('''  if(lb&&lb.live)return `<span class="lv${lb.live==='yahoo'?' dl':''}" title="${lb.live==='yahoo'?'Yahoo 延遲約 20 分':'即時'} ${esc((lb.lt||'').slice(0,5))}">${lb.live==='yahoo'?'延':'即'}</span>`;''',
    '''  if(lb&&lb.live)return lb.live==='yahoo'?`<span class="lv dl" title="Yahoo 延遲約 20 分 ${esc((lb.lt||'').slice(0,5))}">延</span>`:'';   // 2026-11-13 即時不標''')
rep('''  if(r.stale)return '<span class="lv st" title="還是昨天的收盤，等即時更新">昨</span>';return \'\'}''',
    '''  return \'\'}   // 2026-11-13 昨收不再標小標（第二列已有「昨▲x%」）''')
rep('''小卡右上小標 <b>即</b>＝即時、<b>延</b>＝Yahoo 延遲約 20 分、<b>未</b>＝今天還沒成交（漲停／跌停鎖死常見）、<b>昨</b>＝還是昨收、○＝這輪沒拿到報價；''',
    '''漲幅前面有「昨」＝還是昨收、沒有＝今天即時；小卡右上小標只標例外：<b>延</b>＝Yahoo 延遲約 20 分、<b>未</b>＝今天還沒成交（漲停／跌停鎖死常見）、○＝這輪沒拿到報價；''')
open(dst,'w',encoding='utf-8').write(s);print('ok',len(s))
