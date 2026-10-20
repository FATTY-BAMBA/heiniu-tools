const sharp=require('sharp');
const esc=(s)=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
module.exports=async function handler(req,res){
 const lang=req.query.lang==='en'?'en':'zh';
 const heading=lang==='en'?'Zero to Hero':'從零到高手';
 const footer=lang==='en'?'11 PRACTICAL CHAPTERS  ·  HEINIU GUIDE':'11 章完整攻略  ·  黑牛工具';
 const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
 <rect width="1200" height="630" fill="#11131f"/>
 <rect x="43" y="43" width="1114" height="544" rx="29" fill="#181a2a" stroke="#4f447e" stroke-width="2"/>
 <circle cx="1100" cy="480" r="275" stroke="#4a3978" stroke-width="3" fill="none"/>
 <circle cx="1150" cy="520" r="210" stroke="#332a54" stroke-width="3" fill="none"/>
 <rect x="82" y="80" width="264" height="49" rx="12" fill="#4b35c8"/>
 <text x="105" y="112" font-family="Arial,sans-serif" font-size="21" font-weight="700" fill="#fff">HEINIU  /  GUIDE</text>
 <text x="84" y="296" font-family="Arial,sans-serif" font-size="124" font-weight="800" fill="#f8f8fb">Claude</text>
 <text x="85" y="410" font-family="Noto Sans CJK TC, Noto Sans TC, Arial, sans-serif" font-size="${lang==='en'?88:91}" font-weight="800" fill="#b5a4ff">${esc(heading)}</text>
 <path d="M85 463 H870" stroke="#514570" stroke-width="2"/>
 <text x="85" y="521" font-family="Noto Sans CJK TC, Noto Sans TC, Arial, sans-serif" font-size="28" fill="#dfdce9">${esc(footer)}</text>
 </svg>`;
 try{
  const png=await sharp(Buffer.from(svg)).png().toBuffer();
  res.setHeader('Content-Type','image/png');
  res.setHeader('Cache-Control','public, max-age=3600, s-maxage=86400');
  res.status(200).send(png);
 }catch(e){res.status(500).send('Image unavailable');}
};