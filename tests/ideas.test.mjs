import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {exampleCollection,validateCollection,fromDocuments,mergeCollections,search} from '../ideas/library.mjs';
import {checkFiles,readDocxXML,importFiles} from '../ideas/files.mjs';
import {zipSync,strToU8} from '../assets/vendor/fflate-0.8.3.mjs';

test('search finds content even when the filename is unrelated',()=>{
  const c=fromDocuments([{title:'2026-09-08.txt',content:'這次工作會議決定先完成首頁文案。'}]);
  assert.equal(search(c,'首頁文案')[0].note.title,'2026-09-08.txt');
  assert.equal(search(c,'我的護照號碼是多少？').length,0);
});
test('demo sources are explicitly marked and resolve their own excerpts',()=>{
  const c=exampleCollection();
  assert.ok(c.sources.every(s=>s.provenance.startsWith('示範資料')));
  assert.equal(search(c,'信用卡帳單變圖表')[0].note.source,'doc-1');
  assert.deepEqual(validateCollection(c).notes,c.notes);
});
test('new documents become searchable without adding demo documents',()=>{
  const a=fromDocuments([{title:'one',content:'首個文件記錄排程。'}]);
  const b=fromDocuments([{title:'two',content:'第二個文件記錄火星溫室水耕。'}]);
  assert.equal(search(a,'火星溫室水耕').length,0);
  const merged=mergeCollections(a,b,'new');
  assert.equal(search(merged,'火星溫室水耕')[0].note.source,'new-doc-0');
  assert.equal(merged.sources.length,2);
});
test('forged excerpts and duplicate identifiers are rejected',()=>{
  const c=exampleCollection();c.notes[0].text='invented result';assert.throws(()=>validateCollection(c),/不一致/);
  const d=exampleCollection();d.sources[1].id=d.sources[0].id;assert.throws(()=>validateCollection(d),/重複/);
});
test('imports discard filesystem paths and executable download URLs',()=>{
  const c=exampleCollection();c.sources[0].original='/Users/example/private.docx';c.sources[0].download='javascript:alert(1)';c.sources[0].snapshot='secret';
  const clean=validateCollection(c);assert.equal('original' in clean.sources[0],false);assert.equal('download' in clean.sources[0],false);assert.equal('snapshot' in clean.sources[0],false);
});
test('chunked excerpts preserve exact source locations',()=>{
  const text=Array.from({length:80},(_,i)=>`第${i+1}段：這是一個有位置的文件內容。`).join('\n');
  const c=fromDocuments([{title:'long.md',content:text}]);assert.ok(c.notes.length>1);
  for(const n of c.notes)assert.equal(text.split('\n').slice(n.start-1,n.end).join('\n'),n.text);
});
test('plain text and backup imports retain originals only when available',async()=>{
  const txt=new File(['這份文件包含獨特的公園路演活動。'],'schedule.txt',{type:'text/plain'});
  const backup=new File([JSON.stringify(exampleCollection())],'backup.json',{type:'application/json'});
  const imported=await importFiles([backup,txt]);
  assert.equal(imported.originals.length,1);
  assert.equal(imported.originals[0].sourceId,search(imported.collection,'公園路演')[0].note.source);
  assert.equal(imported.originals[0].file,txt);
});
test('file limits and unknown JSON fail clearly',async()=>{
  assert.throws(()=>checkFiles([{name:'archive.exe',size:1}]),/格式不支援/);
  assert.throws(()=>checkFiles([{name:'large.txt',size:11*1024*1024}]),/10 MB/);
  await assert.rejects(()=>importFiles([new File(['{}'],'wrong.json')]),/文件庫備份/);
  await assert.rejects(()=>importFiles([new File([''],'empty.txt')]),/沒有可搜尋/);
});
test('DOCX extraction reads only the document body entry',()=>{
  const xml='<w:document xmlns:w="urn:test"><w:p><w:r><w:t>原文</w:t></w:r></w:p></w:document>';
  const archive=zipSync({'word/document.xml':strToU8(xml),'word/media/private.txt':strToU8('ignored')});
  assert.equal(readDocxXML(archive),xml);
  assert.throws(()=>readDocxXML(zipSync({'not-word.txt':strToU8('a')})),/Word/);
});

// The bundled PDF parser can extract text in Node without launching a browser.
function pdfFixture(text){
  const stream=`BT /F1 16 Tf 40 150 Td (${text}) Tj ET`;
  const objects=['<< /Type /Catalog /Pages 2 0 R >>','<< /Type /Pages /Kids [3 0 R] /Count 1 >>','<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>','<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',`<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`];
  let body='%PDF-1.4\n',offsets=[0];objects.forEach((obj,i)=>{offsets.push(body.length);body+=`${i+1} 0 obj\n${obj}\nendobj\n`;});
  const xref=body.length;body+='xref\n0 6\n0000000000 65535 f \n'+offsets.slice(1).map(n=>String(n).padStart(10,'0')+' 00000 n \n').join('');
  body+=`trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;return body;
}
test('real PDF import preserves searchable text and page labels',async()=>{
  const require=createRequire(import.meta.url);
  const loaded=require('../assets/pdf.min.js');
  globalThis.pdfjsLib=globalThis.pdfjsLib||loaded;
  require('../assets/pdf.worker.min.js');
  const previous=process.cwd();process.chdir(fileURLToPath(new URL('../ideas/',import.meta.url)));
  try{
    const file=new File([pdfFixture('HOMEPAGE COPY REVIEW')],'meeting.pdf',{type:'application/pdf'});
    const value=await importFiles([file]);
    assert.ok(value.collection.sources[0].content.includes('【第 1 頁】'));
    assert.equal(search(value.collection,'HOMEPAGE')[0].note.source,value.originals[0].sourceId);
    await assert.rejects(()=>importFiles([new File([pdfFixture('')],'scan.pdf')]),/沒有文字層/);
  }finally{process.chdir(previous);}
});
test('static page imports shared design and all local assets exist',()=>{
  const html=fs.readFileSync(new URL('../ideas/index.html',import.meta.url),'utf8');
  assert.ok(html.includes('../assets/base.css'));assert.ok(html.includes('class="site-nav"'));
  for(const m of html.matchAll(/(?:href|src)="([^"]+)"/g)){
    const ref=m[1];if(/^(?:https?:|#)/.test(ref))continue;
    assert.ok(fs.existsSync(new URL('../ideas/'+ref,import.meta.url)),ref);
  }
  const manifest=fs.readFileSync(new URL('../assets/site.js',import.meta.url),'utf8');assert.ok(manifest.includes("href: './ideas/'"));
});
