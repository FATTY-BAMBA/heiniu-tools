export const MAX_TEXT = 2_000_000;
export const MAX_NOTES = 600;
const stop = new Set('我 你 他 她 它 我們 我的 你的 他的 她的 可以 之前 那個 這個 那些 這些 怎麼 如何 哪裡 在哪 在 的 了 是 有 想 要 幫 找 找到 找回 一個 一下 點子 筆記 內容 什麼 多少 為何 為什麼 是否 是不是 能不能 可不可以 幾個 幾位 變 can could how where what find my the a an is to of about me idea note'.split(' '));
const segmenter = new Intl.Segmenter('zh-Hant', {granularity:'word'});
export const terms = query => [...new Set([...segmenter.segment(query.normalize('NFKC').toLowerCase())].filter(x=>x.isWordLike).map(x=>x.segment).filter(x=>x.length>1&&!stop.has(x)))];

export function search(collection, query, topic='') {
  const tokens=terms(query);
  const pool=collection.notes.filter(n=>!topic||n.tags.includes(topic));
  if(!query.trim())return pool.map(note=>({note,score:0,matches:[]}));
  if(!tokens.length)return [];
  const text=n=>(n.title+' '+n.text).toLowerCase();
  const frequencies=new Map(tokens.map(t=>[t,1+collection.notes.filter(n=>text(n).includes(t)).length]));
  return pool.map(note=>{
    const matches=tokens.filter(t=>text(note).includes(t));
    const score=matches.reduce((sum,t)=>sum+(note.title.toLowerCase().includes(t)?3:1)*Math.log(1+collection.notes.length/frequencies.get(t)),0);
    return {note,score,matches};
  }).filter(r=>r.matches.length).sort((a,b)=>b.score-a.score);
}

export function snippet(text,matches,max=130) {
  const positions=matches.map(t=>text.toLowerCase().indexOf(t)).filter(p=>p>=0);
  const start=Math.max(0,(positions.length?Math.min(...positions):0)-22);
  return (start?'…':'')+text.slice(start,start+max).replace(/[#`]/g,'')+(text.length>start+max?'…':'');
}

export function fromDocuments(documents) {
  const collection={title:'我的文件庫',sources:[],notes:[],topics:[]};
  documents.forEach((doc,index)=>{
    const id='doc-'+index;
    const content=doc.content.replace(/\r\n?/g,'\n').trim();
    if(!content)throw new Error(`${doc.title} 沒有可搜尋的文字。`);
    const source={id,title:doc.title,content,provenance:doc.provenance||'我的匯入文件',fileName:doc.fileName||doc.title};
    collection.sources.push(source);
    const lines=content.split('\n');
    let start=0;
    while(start<lines.length){
      let end=start+1,length=lines[start].length;
      while(end<lines.length&&length+lines[end].length<700){length+=lines[end].length+1;end++;}
      const text=lines.slice(start,end).join('\n');
      if(text.trim())collection.notes.push({id:`${id}-${start}`,title:doc.title+(start?` · ${collection.notes.filter(n=>n.source===id).length+1}`:''),source:id,start:start+1,end,text,tags:[doc.topic||'我的文件'],provenance:source.provenance});
      start=end;
    }
  });
  return validateCollection(collection);
}

// Allowlisted import fields keep local paths and download URLs out of the public interface.
export function validateCollection(input) {
  if(!input||!Array.isArray(input.sources)||!Array.isArray(input.notes)||!input.sources.length||!input.notes.length)throw new Error('這不是可讀取的文件庫備份。');
  if(input.sources.length>100||input.notes.length>MAX_NOTES)throw new Error('這次文件太多，請分成較小的文件庫（最多 100 份文件、600 段）。');
  const sources=input.sources.map(s=>{
    if(!s||typeof s.id!=='string'||typeof s.title!=='string'||typeof s.content!=='string'||!s.content.trim())throw new Error('原文資料不完整。');
    return {id:s.id.slice(0,160),title:s.title.slice(0,160),content:s.content,provenance:typeof s.provenance==='string'?s.provenance.slice(0,120):'匯入文件',fileName:typeof s.fileName==='string'?s.fileName.slice(0,180):s.title.slice(0,160)};
  });
  if(new Set(sources.map(s=>s.id)).size!==sources.length)throw new Error('原文編號重複。');
  if(sources.reduce((sum,s)=>sum+s.content.length,0)>MAX_TEXT)throw new Error('文字總量超過 200 萬字元，請減少文件後重試。');
  const byId=new Map(sources.map(s=>[s.id,s]));
  const notes=input.notes.map(n=>{
    if(!n||typeof n.id!=='string'||typeof n.title!=='string'||typeof n.text!=='string'||!byId.has(n.source)||!Number.isInteger(n.start)||!Number.isInteger(n.end)||n.start<1||n.end<n.start)throw new Error('摘錄缺少有效的原文位置。');
    const source=byId.get(n.source),lines=source.content.split('\n');
    if(n.end>lines.length||lines.slice(n.start-1,n.end).join('\n').trim()!==n.text.trim())throw new Error('有摘錄與原文不一致，請檢查備份。');
    const tags=Array.isArray(n.tags)?[...new Set(n.tags.filter(t=>typeof t==='string'&&t.trim()).map(t=>t.trim().slice(0,24)))].slice(0,4):[];
    return {id:n.id.slice(0,160),title:n.title.slice(0,160),text:n.text,source:n.source,start:n.start,end:n.end,tags:tags.length?tags:['我的文件'],provenance:source.provenance};
  });
  if(new Set(notes.map(n=>n.id)).size!==notes.length)throw new Error('摘錄編號重複。');
  const topics=[...new Set(notes.flatMap(n=>n.tags))];
  if(topics.length>24)throw new Error('主題過多，請先整理成 24 個以內。');
  return {title:typeof input.title==='string'?input.title.slice(0,120):'我的文件庫',sources,notes,topics};
}

export function mergeCollections(base, added, prefix) {
  const ids=new Map(added.sources.map(s=>[s.id,`${prefix}-${s.id}`]));
  return validateCollection({title:'我的文件庫',sources:[...base.sources,...added.sources.map(s=>({...s,id:ids.get(s.id)}))],notes:[...base.notes,...added.notes.map(n=>({...n,id:`${prefix}-${n.id}`,source:ids.get(n.source)}))]});
}

export function exampleCollection() {
  const data=fromDocuments([
    {title:'示範｜專案週會紀錄.txt',topic:'工作會議',provenance:'示範資料・非真實會議',content:'專案週會紀錄（示範）\n\n首頁文案：本週先完成首頁標題與產品介紹，再整理客戶常見問題。\n\n會議結論：產品介紹使用一個操作例子，讓讀者立即理解工具可以做什麼。下次會議檢查文案是否有清楚的使用情境。'},
    {title:'示範｜內容題材清單.md',topic:'內容企劃',provenance:'示範資料・非個人舊筆記',content:'# 內容題材清單（示範）\n\n信用卡帳單變圖表：用明確標示的模擬消費資料，將支出分類成餐飲、交通與訂閱，做成一張花費圖表。\n\n影片先出現整理好的圖表，再展示原本難讀的帳單。所有數字都要標示為示範資料。'},
    {title:'示範｜工作文件整理.md',topic:'文件整理',provenance:'示範資料・操作練習',content:'# 工作文件整理（示範）\n\n找資料時，先想一個記得的內容關鍵字，例如「首頁文案」。搜尋文件內容後，再開原文核對上下文。\n\nPDF 如果是掃描照片，沒有文字層，就需要先辨識文字。這個工具目前不提供 OCR。'},
    {title:'示範｜短片剪輯備忘.txt',topic:'內容企劃',provenance:'示範資料・操作練習',content:'短片剪輯備忘（示範）\n\n第一個畫面先展示工具真的完成了一件事。口白直接說明正在解決的問題。\n\n來源畫面至少停留到觀眾能讀清楚關鍵句。打字空檔可以加速，文字證據出現時放慢。'},
    {title:'示範｜讀書筆記.md',topic:'學習筆記',provenance:'示範資料・操作練習',content:'# 讀書筆記（示範）\n\n做筆記時，將原文摘錄和自己的想法分開。保留來源名稱，有頁碼就一起記錄。\n\n要用這段內容寫文章時，先打開原文重新確認，再寫新的觀點。'},
    {title:'示範｜檔案匯入說明.txt',topic:'文件整理',provenance:'示範資料・操作練習',content:'檔案匯入說明（示範）\n\n可以匯入 Markdown、TXT、DOCX、含文字的 PDF 或本工具的 JSON 備份。\n\n匯入的文件保存在這個瀏覽器，不會自動同步到手機。備份 JSON 保存文字與出處；原始檔請另外保留。'}
  ]);
  data.title='示範文件庫';return data;
}
