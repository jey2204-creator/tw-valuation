import re,sys
FN='''function mzN(s){return String(s||'').replace(/每\\s*([一二三四五六七八九十]+)\\s*分鐘/,(m,c)=>{const d='一二三四五六七八九'.indexOf.bind('一二三四五六七八九');let n=0;const i=c.indexOf('十');if(i<0)n=d(c)+1;else n=(i>0?d(c[i-1])+1:1)*10+(i<c.length-1?d(c[i+1])+1:0);return '每'+n+'分鐘'})}
'''
# index -> beta.html
s=open('index.html',encoding='utf-8').read()
a="x.measure?x.measure.split('・')[0]:''"
assert s.count(a)==1
s=s.replace(a,"x.measure?mzN(x.measure.split('・')[0]):''")
i=s.index('<script>',s.index('</head>') if '</head>' in s else 0)  # first body script
# put helper at top of the script block that contains the mk('ndis' line
j=s.rfind('<script>',0,s.index("mk('ndis'"))+len('<script>')
s=s[:j]+'\n'+FN+s[j:]
open('beta.html','w',encoding='utf-8').write(s)
# notice -> beta_notice.html
t=open('notice.html',encoding='utf-8').read()
assert t.count('${esc(x.measure)}')==3
t=t.replace('${esc(x.measure)}','${esc(mzN(x.measure))}')
for a,b in [('（每 5 或 20 分鐘撮合一次）','（約每 2 分鐘撮合一次；2026/8/10 新制前為 5 或 20 分鐘）'),
            ('處置期間通常 10 個交易日','處置期間通常 5 個交易日（同時因當沖占比過高被列注意者 7 個；新制前為 10／12 個）')]:
    assert t.count(a)==1,a
    t=t.replace(a,b)
j=t.rfind('<script>',0,t.index("TAB==='dis'"))+len('<script>')
t=t[:j]+'\n'+FN+t[j:]
open('beta_notice.html','w',encoding='utf-8').write(t)
