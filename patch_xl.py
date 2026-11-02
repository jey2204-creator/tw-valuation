#!/usr/bin/env python3
"""X 軸標籤改成「從最新往回數、最新一格加粗」：套在 index.html → beta.html、health.html → beta_health.html"""
import re,sys,pathlib
HELPER=r"""
/* xLast：類別型 X 軸標籤從最新一格往回每隔 N 格標一次（N 依圖寬自動算），最新一格加粗；已自訂 interval 的圖只做加粗 */
function xLast(inst,el){const so=inst.setOption.bind(inst);inst.setOption=function(o,a,b){try{xLastFix(o,el)}catch(e){}return so(o,a,b)};return inst}
function xLastFix(o,el){if(!o||!o.xAxis)return;const W=Math.max(120,((el&&el.clientWidth)||320)-56),fg=css('--fg');
 (Array.isArray(o.xAxis)?o.xAxis:[o.xAxis]).forEach(ax=>{if(!ax||ax.type==='time'||ax.type==='value'||!Array.isArray(ax.data)||!ax.data.length)return;
  const N=ax.data.length,al=ax.axisLabel=ax.axisLabel||{};if(al.show===false)return;
  const f0=al.formatter,fm=typeof f0==='function'?f0:(typeof f0==='string'?v=>f0.replace('{value}',v):v=>v);
  const txt=i=>{const v=ax.data[i],s=fm(v==null?'':(typeof v==='object'?v.value:v),i);return s==null?'':String(s)};
  if(al.interval==null){const ml=Math.max(2,...ax.data.map((_,i)=>txt(i).length)),lw=ml*6.4+14,cols=Math.max(2,Math.floor(W/lw)),step=Math.max(1,Math.ceil(N/cols));al.interval=i=>(N-1-i)%step===0}
  al.rich=Object.assign({},al.rich,{xl:{fontWeight:700,color:fg,fontSize:al.fontSize||10,fontFamily:al.fontFamily}});
  al.formatter=(v,i)=>{const s=txt(i);return i===N-1&&s&&!s.includes('\n')?'{xl|'+s+'}':s}})}
"""
def patch(src,dst,mk_old,mk_new,extra=()):
    s=pathlib.Path(src).read_text(encoding='utf-8')
    assert mk_old in s,src
    s=s.replace(mk_old,mk_new+HELPER,1)
    for a,b in extra:
        assert a in s,(src,a[:60]); s=s.replace(a,b,1)
    pathlib.Path(dst).write_text(s,encoding='utf-8'); print('ok',dst,len(s))

patch('index.html','beta.html',
  "function mk(id){if(!charts[id])charts[id]=echarts.init($(id));return charts[id]}",
  "function mk(id){if(!charts[id])charts[id]=xLast(echarts.init($(id)),$(id));return charts[id]}",
  [("o.xAxis.axisLabel.interval=Math.max(0,Math.round(R.length/6)-1);o.xAxis.axisLabel.formatter=(v,i)=>{const m=v.slice(2,7).replace('-','/'),pv=R[i-1]&&R[i-1].d.slice(0,7);return pv===v.slice(0,7)&&i%2?'':m};",
    "o.xAxis.axisLabel.formatter=R.length<=60?v=>v.slice(5).replace('-','/'):v=>v.slice(2,7).replace('-','/');   // 1年內用 月/日，3年用 年/月"),
   ('<div class="sx" id="tdwK" hidden></div>', '<div class="sx thin" id="tdwK" hidden></div>'),
   ('<style>#tdwK i.tdwx{white-space:normal;line-height:1.3;margin-top:2px;border-top:1px dashed var(--line);padding-top:2px}', '<style>.sx.thin{border:1px solid var(--line);border-radius:9px;padding:3px 5px;gap:0}.sx.thin>div{border:0;border-radius:0;padding:0 2px;display:flex;flex-wrap:wrap;align-items:baseline;justify-content:center;gap:3px;text-align:left}.sx.thin>div+div{border-left:1px solid var(--line)}.sx.thin b{font-size:13px}.sx.thin i{font-size:9px}#tdwK i.tdwx{flex-basis:100%;white-space:normal;line-height:1.3;margin-top:2px;border-top:1px dashed var(--line);padding-top:2px}'),
   ("[['400張以上',fmt(r.b4,1)+'%',c4,'4週',", "[['400張',fmt(r.b4,1)+'%',c4,'4週',"),
   ("['千張以上',fmt(r.b10,1)+'%',d(r,w4,'b10'),'4週',", "['千張',fmt(r.b10,1)+'%',d(r,w4,'b10'),'4週',"),
   ("['股東人數',r.ppl>=10000?fmt(r.ppl/10000,1)+'萬':fmt(r.ppl),p4,'4週%'", "['股東',r.ppl>=10000?fmt(r.ppl/10000,1)+'萬':fmt(r.ppl),p4,'4週'"),
   ("<i>${c==null?'&nbsp;':u+' '+(c>0?'+':'')+fmt(c,a==='股東人數'?1:2)}</i>", "<i>${c==null?'&nbsp;':u+(c>0?'+':'')+fmt(c,1)+(a==='股東'?'%':'')}</i>"),
   ('<div class="${sign(a===\'股東人數\'?(c==null?null:-c):c)}">', '<div class="${sign(a===\'股東\'?(c==null?null:-c):c)}">')])
patch('health.html','beta_health.html',
  "function mk(id){if(charts[id])charts[id].dispose();return charts[id]=echarts.init($(id),null,{renderer:'svg'})}",
  "function mk(id){if(charts[id])charts[id].dispose();return charts[id]=xLast(echarts.init($(id),null,{renderer:'svg'}),$(id))}")
