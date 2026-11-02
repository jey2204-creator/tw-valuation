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
   ('<div class="chart" id="cTdw" hidden style="height:180px"></div>','<div class="chart" id="cTdw" hidden style="height:136px"></div>'),
   ("o.yAxis.scale=true;o.yAxis.axisLabel.formatter='{value}%';o.grid.right=40;\n  o.yAxis=[o.yAxis,{...o.yAxis,scale:true,splitLine:{show:false},axisLabel:{show:false}}];",
    "o.yAxis.scale=true;o.yAxis.splitNumber=3;o.yAxis.axisLabel.formatter='{value}%';o.grid.right=40;o.grid.top=24;\n  o.yAxis=[o.yAxis,{...o.yAxis,scale:true,splitLine:{show:false},axisLabel:{show:false}}];")])
patch('health.html','beta_health.html',
  "function mk(id){if(charts[id])charts[id].dispose();return charts[id]=echarts.init($(id),null,{renderer:'svg'})}",
  "function mk(id){if(charts[id])charts[id].dispose();return charts[id]=xLast(echarts.init($(id),null,{renderer:'svg'}),$(id))}")
