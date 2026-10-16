import {unzipSync,strFromU8} from '../assets/vendor/fflate-0.8.3.mjs';
import {fromDocuments,validateCollection,mergeCollections} from './library.mjs';
const FILE_LIMIT=10*1024*1024;
const EXTENSIONS=new Set(['md','txt','docx','pdf','json']);
export function checkFiles(files){
  if(!files.length||files.length>20)throw new Error('每次請選擇 1–20 份文件。');
  for(const f of files){if(f.size>FILE_LIMIT)throw new Error(`${f.name} 超過 10 MB，請先縮小檔案。`);if(!EXTENSIONS.has(f.name.split('.').pop().toLowerCase()))throw new Error(`${f.name} 格式不支援，請使用 MD、TXT、DOCX、PDF 或 JSON。`);}
  if(files.reduce((s,f)=>s+f.size,0)>50*1024*1024)throw new Error('這批檔案超過 50 MB，請分批匯入。');
}
export function readDocxXML(bytes){
  let tooLarge=false;
  const entries=unzipSync(bytes,{filter:file=>{
    if(file.name!=='word/document.xml')return false;
    if(file.originalSize>8*1024*1024){tooLarge=true;return false;}
    return true;
  }});
  if(tooLarge)throw new Error('Word 文字內容過大，請分成較小的文件。');
  if(!entries['word/document.xml'])throw new Error('無法讀取這份 Word，請另存 DOCX 或純文字。');
  return strFromU8(entries['word/document.xml']);
}
function docxText(bytes){
  const document=new DOMParser().parseFromString(readDocxXML(bytes),'application/xml');
  if(document.querySelector('parsererror'))throw new Error('Word 文件內容格式不完整。');
  return [...document.getElementsByTagNameNS('*','p')].map(p=>[...p.getElementsByTagNameNS('*','t')].map(t=>t.textContent).join('')).filter(Boolean).join('\n\n');
}
async function pdfText(bytes){
  const pdfjs=globalThis.pdfjsLib;
  if(!pdfjs)throw new Error('PDF 讀取器尚未載入，請重新整理後再試。');
  pdfjs.GlobalWorkerOptions.workerSrc='../assets/pdf.worker.min.js';
  const task=pdfjs.getDocument({data:bytes,isEvalSupported:false,disableFontFace:true});
  task.onPassword=()=>{task.destroy();};
  let pdf;
  try{
    pdf=await task.promise;
    if(pdf.numPages>100)throw new Error('PDF 超過 100 頁，請先用 PDF 工具選取需要的頁。');
    const pages=[];let total=0;
    for(let i=1;i<=pdf.numPages;i++){
      const page=await pdf.getPage(i),content=await page.getTextContent();
      const text=content.items.map(item=>item.str+(item.hasEOL?'\n':' ')).join('').trim();
      total+=text.length;
      if(total>2_000_000)throw new Error('PDF 文字過多，請選取需要的頁後再匯入。');
      pages.push(`【第 ${i} 頁】\n${text||'（本頁沒有可讀取的文字）'}`);page.cleanup();
    }
    if(!total)throw new Error('這份 PDF 沒有文字層，可能是掃描圖片；請先做文字辨識後再匯入。');
    return pages.join('\n\n');
  }catch(error){
    if(error.name==='PasswordException'||/destroyed|password/i.test(error.message))throw new Error('PDF 有密碼保護，請先解鎖並另存後再匯入。');
    throw error;
  }finally{if(pdf)await pdf.destroy();else await task.destroy();}
}
export async function importFiles(files,progress=()=>{}){
  checkFiles(files);let combined=null;const originals=[];
  for(let i=0;i<files.length;i++){
    const file=files[i],ext=file.name.split('.').pop().toLowerCase(),prefix=`import-${i}`;
    progress(`正在讀取 ${i+1}/${files.length}：${file.name}`);
    let collection;
    if(ext==='json'){
      let parsed;try{parsed=JSON.parse(await file.text());}catch{throw new Error(`${file.name} 不是有效的 JSON 備份。`);}
      collection=validateCollection(parsed);
    }else{
      let content;
      if(ext==='docx')content=docxText(new Uint8Array(await file.arrayBuffer()));
      else if(ext==='pdf')content=await pdfText(new Uint8Array(await file.arrayBuffer()));
      else content=await file.text();
      collection=fromDocuments([{title:file.name,fileName:file.name,content,topic:ext==='pdf'?'PDF 文件':ext==='docx'?'Word 文件':'文字筆記',provenance:'我的匯入文件'}]);
      originals.push({sourceId:combined?`${prefix}-doc-0`:'doc-0',file});
    }
    combined=combined?mergeCollections(combined,collection,prefix):collection;
  }
  return {collection:combined,originals};
}

function openDB(){return new Promise((resolve,reject)=>{
  const request=indexedDB.open('heiniu-tools-ideas',1);
  request.onupgradeneeded=()=>request.result.createObjectStore('library');
  request.onerror=()=>reject(request.error);
  request.onblocked=()=>reject(new Error('請關閉其他文件庫分頁後再試。'));
  request.onsuccess=()=>resolve(request.result);
});}
export async function loadLibrary(){const db=await openDB();try{return await new Promise((resolve,reject)=>{const r=db.transaction('library').objectStore('library').get('current');r.onsuccess=()=>resolve(r.result||null);r.onerror=()=>reject(r.error);});}finally{db.close();}}
export async function saveLibrary(value){const db=await openDB();try{await new Promise((resolve,reject)=>{const tx=db.transaction('library','readwrite');tx.objectStore('library').put(value,'current');tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error||new Error('儲存被中斷。'));});}finally{db.close();}}
