import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve,extname,sep } from 'node:path';
import handler from '../api/travel.js';
const root=resolve(import.meta.dirname,'..');
const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.png':'image/png'};
createServer(async(req,res)=>{
 const path=new URL(req.url,'http://localhost').pathname;
 if(path==='/api/travel')return handler(req,res);
 const file=resolve(root,'.'+decodeURIComponent(path)+(path.endsWith('/')?'index.html':''));
 if(!file.startsWith(root+sep)||path.includes('node_modules')||path.split('/').some(p=>p.startsWith('.'))){res.writeHead(403);return res.end();}
 try{const data=await readFile(file);res.writeHead(200,{'Content-Type':types[extname(file)]||'application/octet-stream'});res.end(data);}catch{res.writeHead(404);res.end('Not found');}
}).listen(4173,'0.0.0.0',()=>console.log('Preview: http://localhost:4173/travel/'));
