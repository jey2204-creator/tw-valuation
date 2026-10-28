"""雲端同步（⭐自選＋自訂主題）：把 index.html 套成 beta.html
用法：python3 patch_sync.py index.html beta.html
搬正式版：python3 patch_sync.py index.html index.html
後端：Supabase 免費方案，一張表 sync(code, data, updated_at)，瀏覽器只透過兩個 RPC（sync_get／sync_put）讀寫，
     表本身開 RLS 不給 anon 直接讀，所以別人拿到 anon key 也列不出所有配對碼。
配對碼：12 碼隨機（去掉 0/O/1/I），存在每台裝置的 localStorage（syncCode）。
同步規則：開頁／回到前景時拉一次；改自選或主題後 1.2 秒推一次；兩邊都有未同步修改時自選取聯集（合併，不覆蓋）。
"""
import sys

src, dst = sys.argv[1], sys.argv[2]
BETA = dst != src
h = open(src, encoding="utf-8").read()

# ↓ 之後由世杰提供 Supabase 專案的 URL 與 anon key，填在這裡
SB_URL = "https://YOUR-PROJECT.supabase.co"
SB_KEY = "YOUR-ANON-KEY"


def rep(old, new, n=1):
    global h
    c = h.count(old)
    assert c == n, f"錨點出現 {c} 次（預期 {n}）：{old[:60]}"
    h = h.replace(old, new)


if BETA:
    rep("<title>台股估值看板</title>", "<title>台股估值看板 β同步</title>")

# 1) 首頁自選標題：加雲端狀態小圖示（點了進設定頁）
rep('<a class="act" href="#f" id="favEdit" hidden aria-label="自選排序" title="自選排序">✏️</a>',
    '<a class="act" href="#f" id="favEdit" hidden aria-label="自選排序" title="自選排序">✏️</a>'
    '<a class="act" href="#e" id="favCloud" hidden aria-label="雲端同步" title="雲端同步">☁️</a>')

# 2) 編輯主題頁：備份區上面插入「雲端同步」區
rep('''  <details class="ind" style="margin-top:22px"><summary><b>💾 備份／換手機</b><span>複製設定碼</span></summary>''',
    '''  <details class="ind" style="margin-top:22px" id="syncBox" open><summary><b>☁️ 雲端同步</b><span id="syncSum">未開啟</span></summary>
    <div style="padding:0 12px 12px">
      <div id="syncOffUi">
        <p class="foot">開啟後，⭐自選與自訂主題會存到雲端，手機、電腦任一邊改，另一邊打開網站就自動更新。第一台裝置按「開啟同步」拿到配對碼，其他裝置輸入同一組配對碼即可。</p>
        <div class="ebar"><button type="button" class="ib pri" id="syncNew">開啟同步（產生配對碼）</button></div>
        <label class="efield" for="syncIn">已有配對碼？在這裡輸入<input id="syncIn" autocomplete="off" autocapitalize="characters" spellcheck="false" placeholder="例：K7MQ-4XZP-9PDW"></label>
        <div class="ebar"><button type="button" class="ib" id="syncJoin">配對這台裝置</button></div>
      </div>
      <div id="syncOnUi" hidden>
        <p style="margin:8px 0 4px;font-size:14px">配對碼 <b class="cd" id="syncCodeTxt" style="font-size:16px;letter-spacing:.5px"></b></p>
        <p class="foot">到另一台裝置的「編輯主題 → ☁️ 雲端同步」輸入這組配對碼就會同步。配對碼請自己收好，知道配對碼的人就能看到／改你的自選。</p>
        <p class="foot" id="syncStat" role="status"></p>
        <div class="ebar"><button type="button" class="ib" id="syncCopy">複製配對碼</button><button type="button" class="ib" id="syncNow">立即同步</button><button type="button" class="ib warn" id="syncStop">關閉同步</button></div>
      </div>
      <p class="foot" id="syncMsg" role="status"></p>
    </div>
  </details>
  <details class="ind" style="margin-top:22px"><summary><b>💾 備份／換手機</b><span>複製設定碼</span></summary>''')

# 3) 同步模組（放在 Cloudflare 統計碼前）
SYNC_JS = r'''<script>
// ---------- ☁️ 雲端同步（Supabase RPC）：fav + themeCfg ----------
(function(){
const URL_='%SB_URL%',KEY='%SB_KEY%';
if(!URL_||URL_.includes('YOUR-')){console.warn('sync: 尚未設定 Supabase');}
const HDR={apikey:KEY,Authorization:'Bearer '+KEY,'Content-Type':'application/json'};
const raw=store.set.bind(store);
let code=store.get('syncCode')||'',meta=store.get('syncMeta')||{},tm=null,busy=false,lastMerged=false;
const save=()=>raw('syncMeta',meta);
const local=()=>({fav:store.get('fav')||[],cfg:store.get('themeCfg')||null});
const hhmm=d=>{d=new Date(d);return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`};
const rpc=async(fn,body)=>{const ac=new AbortController(),t=setTimeout(()=>ac.abort(),10000);try{const r=await fetch(`${URL_}/rest/v1/rpc/${fn}`,{method:'POST',headers:HDR,body:JSON.stringify(body),signal:ac.signal});if(!r.ok)throw new Error('HTTP '+r.status);return await r.json()}catch(e){throw new Error(e.name==='AbortError'?'逾時':/HTTP \d+/.test(e.message)?e.message:'連線失敗')}finally{clearTimeout(t)}};

// 攔截 store.set：改到 fav / themeCfg 就排程上傳
store.set=function(k,v){raw(k,v);if(code&&(k==='fav'||k==='themeCfg')){meta.dirty=true;save();schedule()}};
function schedule(){clearTimeout(tm);tm=setTimeout(()=>push().catch(()=>{}),1200);paint()}

function repaint(){try{applyCfg()}catch(e){}
  const v=document.body.dataset.view;
  try{if(v==='home')renderHome();else if(v==='flist')renderFav();else if(v==='tlist')renderOrder();else if(v==='stock'&&D)stockExtras(D.id)}catch(e){}}

async function push(){if(!code||busy)return;busy=true;paint();
  try{const d=local(),ts=await rpc('sync_put',{p_code:code,p_data:d});
    meta={ts,at:Date.now(),dirty:false};save();}
  catch(e){meta.err=String(e.message||e);save();}
  finally{busy=false;paint()}}

async function pull(){if(!code||busy)return;busy=true;paint();
  try{const row=await rpc('sync_get',{p_code:code});
    if(!row){busy=false;await push();return}          // 雲端還沒有 → 先把本機的放上去
    if(row.updated_at!==meta.ts){                    // 雲端比上次看到的新
      const L=local(),R=row.data||{};let fav=R.fav||[],cfg=('cfg' in R)?R.cfg:null,merged=false;
      if(meta.dirty){                                // 兩邊都改過 → 合併（聯集，雲端順序在前）
        fav=[...fav,...L.fav.filter(x=>!fav.includes(x))].slice(0,30);
        if(L.cfg)cfg=L.cfg;merged=true;lastMerged=true}
      raw('fav',fav);if(cfg)raw('themeCfg',cfg);else{raw('themeCfg',null);try{localStorage.removeItem('themeCfg')}catch(e){}}
      meta={ts:row.updated_at,at:Date.now(),dirty:merged};save();repaint();
      if(merged){busy=false;await push();return}
    }else if(meta.dirty){busy=false;await push();return}
    else{meta.at=Date.now();delete meta.err;save()}
  }catch(e){meta.err=String(e.message||e);save()}
  finally{busy=false;paint()}}

// ---- 介面 ----
const $$=id=>document.getElementById(id);
function paint(){
  const on=!!code,ok=on&&!meta.err;
  const stat=!on?'':busy?'同步中…':meta.err?`⚠️ 同步失敗（${meta.err}），改動已先存在這台裝置，連上網會再試`:meta.dirty?'有改動尚未上傳':meta.at?`已同步 ${hhmm(meta.at)}`:'尚未同步';
  const sum=$$('syncSum');if(sum)sum.textContent=!on?'未開啟':busy?'同步中…':meta.err?'⚠️ 失敗':meta.at?'已同步 '+hhmm(meta.at):'已開啟';
  if($$('syncOffUi')){$$('syncOffUi').hidden=on;$$('syncOnUi').hidden=!on;$$('syncCodeTxt').textContent=code;$$('syncStat').textContent=stat;$$('syncBox').open=$$('syncBox').open||on}
  const fc=$$('favCloud');if(fc){fc.hidden=!on;fc.textContent=meta.err?'⚠️':busy?'🔄':'☁️';fc.title=stat}
  document.querySelectorAll('.ehead .meta').forEach(m=>{if(/存在這支手機上|雲端同步/.test(m.textContent))m.textContent=on?(ok?'☁️ 雲端同步中':'⚠️ 雲端同步失敗'):'存在這支手機上'});
}
const genCode=()=>{const A='ABCDEFGHJKLMNPQRSTUVWXYZ23456789',b=crypto.getRandomValues(new Uint8Array(12));
  const s=[...b].map(x=>A[x%A.length]).join('');return s.slice(0,4)+'-'+s.slice(4,8)+'-'+s.slice(8)};
const norm=s=>String(s||'').toUpperCase().replace(/[^A-Z0-9]/g,'');
$$('syncNew').addEventListener('click',async()=>{code=genCode();raw('syncCode',code);meta={dirty:true};save();paint();$$('syncMsg').textContent='';await push();$$('syncMsg').textContent=meta.err?'':'已開啟。把配對碼輸入到另一台裝置就會同步。'});
$$('syncJoin').addEventListener('click',async()=>{const c=norm($$('syncIn').value);if(c.length!==12){$$('syncMsg').textContent='配對碼是 12 碼（可含「-」），請再確認';return}
  code=c.slice(0,4)+'-'+c.slice(4,8)+'-'+c.slice(8);raw('syncCode',code);
  const L=local();meta={dirty:!!(L.fav.length||L.cfg)};lastMerged=false;save();paint();$$('syncMsg').textContent='';
  await pull();$$('syncMsg').textContent=meta.err?'':(lastMerged?'已配對，並把兩邊的自選合併。':'已配對，拉到雲端的自選。')});
$$('syncCopy').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(code);$$('syncMsg').textContent='已複製配對碼'}catch(e){$$('syncMsg').textContent='複製失敗，請長按配對碼選取'}});
$$('syncNow').addEventListener('click',()=>{meta.dirty=true;save();pull()});
let stopArm=0;
$$('syncStop').addEventListener('click',()=>{if(Date.now()-stopArm>4000){stopArm=Date.now();$$('syncMsg').textContent='關閉後這台裝置不再同步（本機資料保留，雲端的也保留）。4 秒內再按一次確認';return}
  code='';raw('syncCode','');meta={};save();paint();$$('syncMsg').textContent='已關閉同步'});

// ---- 觸發時機 ----
paint();addEventListener('load',()=>{if(code)pull()});
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&code){if(meta.dirty)push();else pull()}});
addEventListener('pagehide',()=>{if(code&&meta.dirty&&!busy){clearTimeout(tm);try{fetch(`${URL_}/rest/v1/rpc/sync_put`,{method:'POST',headers:HDR,body:JSON.stringify({p_code:code,p_data:local()}),keepalive:true}).then(()=>{meta.dirty=false;save()}).catch(()=>{})}catch(e){}}});
addEventListener('hashchange',()=>setTimeout(paint,0));
window.__sync={pull,push,get code(){return code}};
})();
</script>
'''.replace('%SB_URL%', SB_URL).replace('%SB_KEY%', SB_KEY)

rep('<!-- Cloudflare Web Analytics -->', SYNC_JS + '<!-- Cloudflare Web Analytics -->')

# 4) 「全部還原預設」也要同步（它直接 removeItem，沒經過 store.set）
rep("store.set('themeCfg',null);try{localStorage.removeItem('themeCfg')}catch(e){}applyCfg();renderOrder();$('bkMsg').textContent='已還原預設'",
    "try{localStorage.removeItem('themeCfg')}catch(e){}store.set('themeCfg',null);applyCfg();renderOrder();$('bkMsg').textContent='已還原預設'")

open(dst, "w", encoding="utf-8").write(h)
print("ok", dst, len(h))
