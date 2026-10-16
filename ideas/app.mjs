import {exampleCollection,validateCollection,fromDocuments,mergeCollections,search,terms,snippet} from './library.mjs';
import {importFiles,loadLibrary,saveLibrary} from './files.mjs';
import {zipSync,strToU8} from '../assets/vendor/fflate-0.8.3.mjs';
const $=s=>document.querySelector(s);
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const palette=['#3d2ce0','#198278','#ac6420','#7960ad','#527b3f','#b75972'];
let personal=null,collection=exampleCollection(),mode='demo',query='',topic='',selected='',results=[],limit=12,busy=false;
let toastTimer;

function highlight(text,tokens=terms(query)){
  if(!tokens.length)return escape(text);
  const regex=new RegExp('('+[...tokens].sort((a,b)=>b.length-a.length).map(t=>t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('|')+')','gi');
  return text.split(regex).map((part,i)=>i%2?'<mark>'+escape(part)+'</mark>':escape(part)).join('');
}
function message(text,error=false){$('#message').hidden=!text;$('#message').textContent=text;$('#message').classList.toggle('error',error);}
function toast(text){clearTimeout(toastTimer);$('#toast').textContent=text;$('#toast').classList.add('show');toastTimer=setTimeout(()=>$('#toast').classList.remove('show'),3500);}
function setBusy(value){busy=value;['#import','#add','#toggle-library'].forEach(s=>$(s).disabled=value);$('#note-form button[type=submit]').disabled=value;}
function source(note){return collection.sources.find(s=>s.id===note.source);}
function refresh(){
  $('#mode-label').textContent=mode==='demo'?'示範資料':'我的文件庫';
  $('#counts').textContent=`${collection.sources.length} 份文件 · ${collection.notes.length} 段摘錄`;
  $('#toggle-library').hidden=!personal;$('#toggle-library').textContent=mode==='demo'?'回我的文件庫':'看示範';
  $('#examples').hidden=mode!=='demo';
  $('#topics').innerHTML=['',...collection.topics].map((t,i)=>`<button class="${topic===t?'active':''}" data-topic="${escape(t)}">${i?`<span class="dot" style="background:${palette[(i-1)%palette.length]}"></span>`:''}${escape(t||'全部')}<span class="count">${collection.notes.filter(n=>!t||n.tags.includes(t)).length}</span></button>`).join('');
  $('#topics').querySelectorAll('button').forEach(b=>b.onclick=()=>{topic=b.dataset.topic;limit=12;refresh();});
  results=search(collection,query,topic);
  if(!results.some(r=>r.note.id===selected))selected=results[0]?.note.id||'';
  renderResults();renderGraph();
  if(selected)renderReader(collection.notes.find(n=>n.id===selected));
  else $('#reader').innerHTML='<div class="reader-kicker">SOURCE CHECK</div><h2>目前資料沒有找到</h2><p class="reader-note">試試一個更具體的內容關鍵字，或先匯入包含這段資訊的文件。此處不會生成答案或補寫原文。</p>';
}
function select(id,scroll=false){
  const note=collection.notes.find(n=>n.id===id);if(!note)throw new Error('找不到這段摘錄。');
  selected=id;renderReader(note);renderResults();renderGraph();
  if(scroll&&innerWidth<=900)$('#reader').scrollIntoView({behavior:'smooth',block:'start'});
  return note;
}
function renderResults(){
  $('#results-title').textContent=query?`「${query}」的相關原文`:topic||'從一份文件開始';$('#result-count').textContent=results.length+' 段';
  $('#more-results').hidden=results.length<=limit;
  $('#results').innerHTML=results.length?results.slice(0,limit).map(({note,matches})=>`<button class="result ${selected===note.id?'selected':''}" data-id="${escape(note.id)}"><div class="result-heading"><strong>${highlight(note.title,matches)}</strong><span>↗</span></div><p>${highlight(snippet(note.text,matches),matches)}</p><small>${escape(note.provenance)} · 原文第 ${note.start}–${note.end} 行</small></button>`).join(''):'<div class="empty"><strong>目前資料沒有找到</strong>換個具體關鍵字，或先加入這份文件。</div>';
  $('#results').querySelectorAll('button').forEach(b=>b.onclick=()=>select(b.dataset.id,true));
}
function originalFor(s){return mode==='personal'?personal.originals.find(o=>o.sourceId===s.id&&o.file instanceof Blob):null;}
function renderReader(note){
  const s=source(note),original=originalFor(s);
  $('#reader').innerHTML=`<div class="reader-kicker">${mode==='demo'?'DEMO SOURCE':'YOUR SOURCE'}</div><h2>${escape(note.title)}</h2><div class="provenance">${escape(s.provenance)}<br>原文第 ${note.start}–${note.end} 行</div><div class="tags">${note.tags.map(t=>`<span>${escape(t)}</span>`).join('')}</div><blockquote>${highlight(note.text)}</blockquote><div class="reader-actions"><button id="open-source" class="btn btn-hi">打開完整原文 ↗</button><button id="download-source" class="btn btn-ghost">${original?'下載原始檔':'下載原文文字'}</button></div><p class="reader-note">${mode==='demo'?'這些是操作示範資料。匯入自己的文件後，這裡會顯示你的原文。':'以上是原文摘錄，沒有 AI 生成或改寫。PDF 的頁碼標示可供回查；Word 與 PDF 的原始排版請查看原檔。'}</p>`;
  $('#reader').scrollTop=0;$('#open-source').onclick=()=>openSource(note);
  $('#download-source').onclick=()=>download(original?.file||new Blob([s.content],{type:'text/plain;charset=utf-8'}),original?.file.name||safeName(s.title)+'.txt');
}
function openSource(note){
  const s=source(note);
  $('#reader').innerHTML=`<div class="source-head"><button id="back">← 回到摘錄</button><h2>${escape(s.title)}</h2><p class="provenance">${escape(s.provenance)} · 第 ${note.start}–${note.end} 行已標示</p></div>`+s.content.split('\n').map((line,i)=>`<p class="source-line ${i+1>=note.start&&i+1<=note.end?'selected-line':''}"><small>${i+1}</small>${highlight(line)}</p>`).join('');
  $('#back').onclick=()=>renderReader(note);
  requestAnimationFrame(()=>{const target=$('.selected-line');if(!target)return;if(innerWidth>900){const r=$('#reader'),head=$('.source-head');r.scrollTop+=target.getBoundingClientRect().top-r.getBoundingClientRect().top-head.offsetHeight-12;}else target.scrollIntoView({block:'center'});});
}
function renderGraph(){
  const W=650,H=320;
  const shown=(query||topic?results.map(r=>r.note):collection.notes).slice(0,40);
  const shownTopics=collection.topics.filter(t=>shown.some(n=>n.tags.includes(t)));
  const hubs=shownTopics.map((t,i)=>({title:t,x:W/2+175*Math.cos(i*2*Math.PI/shownTopics.length-.7),y:H/2+86*Math.sin(i*2*Math.PI/shownTopics.length-.7),color:palette[collection.topics.indexOf(t)%palette.length]}));
  const nodes=shown.map((n,i)=>{const anchors=hubs.filter(h=>n.tags.includes(h.title)),ax=anchors.reduce((s,h)=>s+h.x,0)/anchors.length,ay=anchors.reduce((s,h)=>s+h.y,0)/anchors.length;return {...n,ax,ay,x:ax+45*Math.cos(i*2.4),y:ay+45*Math.sin(i*2.4),color:anchors[0].color};});
  for(let k=0;k<90;k++)for(const n of nodes){let fx=(n.ax-n.x)*.008,fy=(n.ay-n.y)*.008;for(const o of [...nodes,...hubs]){if(o===n)continue;const dx=n.x-o.x,dy=n.y-o.y,d=Math.hypot(dx,dy)||1,min=o.ax===undefined?70:55;if(d<min){fx+=dx/d*(min-d)*.08;fy+=dy/d*(min-d)*.08;}}n.x=Math.max(24,Math.min(W-120,n.x+fx));n.y=Math.max(28,Math.min(H-25,n.y+fy));}
  const edges=nodes.flatMap(n=>n.tags.map(t=>{const h=hubs.find(h=>h.title===t);return `<line x1="${n.x}" y1="${n.y}" x2="${h.x}" y2="${h.y}" stroke="${h.color}" stroke-opacity="${n.id===selected?.7:.25}"/>`;})).join('');
  const items=nodes.map(n=>`<g class="node" role="button" tabindex="0" data-id="${escape(n.id)}" aria-label="${escape(n.title)}"><title>${escape(n.title)}</title>${n.id===selected?`<circle cx="${n.x}" cy="${n.y}" r="14" fill="${n.color}" opacity=".12"/>`:''}<circle cx="${n.x}" cy="${n.y}" r="${n.id===selected?6:4}" fill="${n.color}"/><text x="${n.x+10}" y="${n.y+4}">${escape(n.title.replace(/^示範[｜：]/,'').slice(0,8))}${n.title.length>8?'…':''}</text></g>`).join('');
  const groups=hubs.map(h=>`<g class="node hub" role="button" tabindex="0" data-topic="${escape(h.title)}" aria-label="主題 ${escape(h.title)}"><circle cx="${h.x}" cy="${h.y}" r="9" fill="white" stroke="${h.color}" stroke-width="1.5"/><circle cx="${h.x}" cy="${h.y}" r="3" fill="${h.color}"/><text x="${h.x}" y="${h.y-16}" text-anchor="middle">${escape(h.title)}</text></g>`).join('');
  $('#graph').innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="group" aria-label="${shown.length} 段摘錄與 ${hubs.length} 個主題">${edges}${items}${groups}</svg>`;
  $('#map-caption').textContent=`${shown.length} 段摘錄 · ${hubs.length} 個主題${(query||topic?results.length:collection.notes.length)>40?' · 圖中顯示前 40 段':''}。線條代表分類連結。`;
  $('#graph').querySelectorAll('.node').forEach(el=>{el.onclick=()=>{if(el.dataset.id)select(el.dataset.id,true);else{topic=el.dataset.topic;refresh();}};el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();el.onclick();}};});
}
const safeName=name=>name.replace(/[\\/:*?"<>|#\[\]^]/g,'_').slice(0,120)||'文件';
function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),3000);}
function exportJSON(){download(new Blob([JSON.stringify(collection,null,2)],{type:'application/json'}),'黑牛文件庫備份.json');}
function exportVault(){
  const files={},names=new Map(collection.sources.map((s,i)=>[s.id,`${i+1} ${safeName(s.title)}`]));
  const topicNames=new Map(collection.topics.map((t,i)=>[t,`${i+1} ${safeName(t)}`]));
  for(const s of collection.sources)files[`黑牛文件庫/原文/${names.get(s.id)}.md`]=strToU8(`# ${s.title}\n\n出處類型：${s.provenance}\n\n${s.content}`);
  collection.notes.forEach((n,i)=>{files[`黑牛文件庫/摘錄/${i+1} ${safeName(n.title)}.md`]=strToU8(`# ${n.title}\n\n來源：[[原文/${names.get(n.source)}]] · 第 ${n.start}–${n.end} 行\n\n${n.tags.map(t=>`[[主題/${topicNames.get(t)}]]`).join(' · ')}\n\n${n.text}`);});
  for(const t of collection.topics)files[`黑牛文件庫/主題/${topicNames.get(t)}.md`]=strToU8(`# ${t}\n\n`+collection.notes.map((n,i)=>n.tags.includes(t)?`- [[摘錄/${i+1} ${safeName(n.title)}]]`:null).filter(Boolean).join('\n'));
  download(new Blob([zipSync(files)],{type:'application/zip'}),'黑牛文件庫-Markdown.zip');
}
async function acceptImport(added){
  const prefix='batch-'+crypto.randomUUID(),base=personal?.collection;
  const combined=base?mergeCollections(base,added.collection,prefix):added.collection;
  const originals=[...(personal?.originals||[]),...added.originals.map(o=>({...o,sourceId:base?`${prefix}-${o.sourceId}`:o.sourceId}))];
  const next={collection:combined,originals};
  await saveLibrary(next);
  personal=next;collection=next.collection;mode='personal';query='';topic='';selected='';limit=12;$('#query').value='';refresh();
}
async function init(){
  refresh();
  try{const stored=await loadLibrary();if(stored){personal={collection:validateCollection(stored.collection),originals:Array.isArray(stored.originals)?stored.originals:[]};collection=personal.collection;mode='personal';refresh();}}catch{message('此瀏覽器的已存文件暫時無法讀取。示範仍可使用；如有備份，請重新匯入。',true);}
  $('#search-form').onsubmit=e=>{e.preventDefault();query=$('#query').value.trim();selected='';limit=12;refresh();};
  $('#query').addEventListener('search',()=>{if(!$('#query').value){query='';refresh();}});
  $('#examples').querySelectorAll('button').forEach(b=>b.onclick=()=>{query=b.dataset.query;topic='';selected='';$('#query').value=query;refresh();});
  $('#more-results').onclick=()=>{limit+=12;renderResults();};
  $('#reset').onclick=()=>{query='';topic='';selected='';$('#query').value='';refresh();};
  $('#toggle-library').onclick=()=>{if(!personal)return;mode=mode==='demo'?'personal':'demo';collection=mode==='demo'?exampleCollection():personal.collection;query='';topic='';selected='';$('#query').value='';refresh();};
  $('#import').onclick=()=>$('#files').click();
  $('#files').onchange=async()=>{if(busy)return;const files=[...$('#files').files];if(!files.length)return;setBusy(true);try{const added=await importFiles(files,text=>message(text));await acceptImport(added);message(`已加入 ${files.length} 個檔案。內容與原始檔保存在此瀏覽器；JSON 備份僅含文字。`);}catch(error){message(error.name==='QuotaExceededError'?'此瀏覽器空間不足；這批文件尚未儲存，原有文件保留。':error.message,true);}finally{$('#files').value='';setBusy(false);}};
  $('#add').onclick=()=>{$('#note-error').textContent='';$('#note-dialog').showModal();};
  document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>b.closest('dialog').close());
  $('#help').onclick=()=>$('#help-dialog').showModal();$('#export').onclick=()=>$('#export-dialog').showModal();
  $('#export-json').onclick=exportJSON;$('#export-vault').onclick=exportVault;
  $('#note-form').onsubmit=async e=>{e.preventDefault();if(busy)return;setBusy(true);try{const title=$('#note-title').value.trim(),text=$('#note-body').value.trim();if(!title||!text)throw new Error('請填寫標題和內容。');const added=fromDocuments([{title,content:text,topic:'我的筆記',provenance:'使用者新增的筆記'}]);await acceptImport({collection:added,originals:[]});$('#note-dialog').close();$('#note-form').reset();toast('筆記已儲存，可以搜尋了。');}catch(error){$('#note-error').textContent=error.name==='QuotaExceededError'?'此瀏覽器空間不足，尚未儲存。':error.message;}finally{setBusy(false);}};
  registerTools();
}
function registerTools(){
  if(!document.modelContext?.registerTool)return;
  const controller=new AbortController();
  for(const definition of [
    {name:'search_document_sources',title:'搜尋文件原文',description:'Search text in the current local collection. Returns verbatim evidence, not generated answers.',inputSchema:{type:'object',properties:{query:{type:'string'}},required:['query'],additionalProperties:false},annotations:{readOnlyHint:true,untrustedContentHint:true},execute(input){if(!input||typeof input.query!=='string')throw new Error('query is required');query=input.query;topic='';selected='';$('#query').value=query;refresh();return {found:results.length>0,results:results.slice(0,5).map(({note})=>({id:note.id,title:note.title,text:note.text,source:source(note).title,start:note.start,end:note.end}))};}},
    {name:'open_document_source',title:'打開文件原文',description:'Open the source text for a specific excerpt in the reader.',inputSchema:{type:'object',properties:{id:{type:'string'}},required:['id'],additionalProperties:false},annotations:{readOnlyHint:true,untrustedContentHint:true},execute(input){if(!input||typeof input.id!=='string')throw new Error('id is required');const note=select(input.id);openSource(note);return {source:source(note).title,start:note.start,end:note.end};}}
  ]){try{Promise.resolve(document.modelContext.registerTool(definition,{signal:controller.signal})).catch(()=>{});}catch{}}
  addEventListener('pagehide',()=>controller.abort(),{once:true});
}
init().catch(error=>message('文件庫載入失敗：'+error.message,true));
