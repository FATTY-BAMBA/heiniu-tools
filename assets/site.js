/* ============================================================
   黑牛工具 · 站台內容清單
   ─────────────────────────────────────────────
   每週新增工具 / 做法，只要在最上面加一筆就好，
   首頁的卡片、統計數字、「最新」標記會自動更新。

   欄位說明：
     kind  : 'tool'（工具）/ 'guide'（完整做法）/ 'radar'（RADAR 懶人包）
     num   : 顯示用編號，工具用 '01' '02'，做法用 'A' 'B'，RADAR 用 'R1' 'R2'
     title : 標題
     desc  : 一句話說明
     href  : 連結（相對路徑）
     date  : 上線日期 'YYYY-MM-DD'（最新一筆自動亮 NEW）
     next  : true = 顯示在「接下來做什麼」、不出現卡片
   ============================================================ */

const HEINIU_ITEMS = [
  {
    kind: 'tool',
    num: '01',
    title: '薪水實拿計算機',
    desc: '輸入月薪 → 產生你的薪資明細表：扣完勞健保實拿多少，還有老闆偷偷幫你付的錢。',
    href: './salary/',
    date: '2026-08-01',
  },
  {
    kind: 'tool',
    num: '02',
    title: '錢去哪了 · AI 花費健檢',
    desc: '把信用卡明細貼進來 → AI 自動分類、抓出你最大的錢坑，看「亂花」有沒有比房租多。',
    href: './spending/',
    date: '2026-08-10',
  },
  {
    kind: 'tool',
    num: '03',
    title: 'PDF 只取需要的頁',
    desc: '整份 PDF 太肥？拖進來、選你要的頁，直接抽出純文字複製給 AI——省 token、答更準。檔案不上傳，全在你的瀏覽器裡跑。',
    href: './pdf/',
    date: '2026-08-21',
  },
  {
    kind: 'guide',
    num: 'A',
    title: '省 token 三招',
    desc: '3 個超浪費 AI 額度的習慣，跟正確做法：只給需要的部分、開新對話、需要才開功能。',
    href: './token/',
    date: '2026-08-05',
  },
  {
    kind: 'radar',
    num: 'R1',
    title: '值得搞懂的 3 個 AI 專案',
    desc: '影片裡三個專案的連結，加上我判斷「值不值得看」的三個問題（三問）。不是又一個聊天功能。',
    href: './radar/ai-projects/',
    date: '2026-08-28',
  },

  /* ↓↓↓ 接下來要做的（next: true）↓↓↓ */
  { kind: 'tool',  title: '104 職缺分析器', next: true },
  { kind: 'tool',  title: '信用卡帳單分析', next: true },
  { kind: 'guide', title: 'AI 外掛 / 自動化 完整做法', next: true },
  { kind: 'radar', title: 'AI Agent 真正該有的用法（AGENT）', next: true },
  { kind: 'radar', title: 'AI 圖的 8 個元素框架（PROMPT）', next: true },
];

/* ---------- 以下為渲染邏輯，平常不用動 ---------- */
(function () {
  const tools  = HEINIU_ITEMS.filter(i => i.kind === 'tool'  && !i.next);
  const guides = HEINIU_ITEMS.filter(i => i.kind === 'guide' && !i.next);
  const radars = HEINIU_ITEMS.filter(i => i.kind === 'radar' && !i.next);
  const nexts  = HEINIU_ITEMS.filter(i => i.next);
  const newestDate = Math.max(...[...tools, ...guides, ...radars].map(i => Date.parse(i.date || 0)));

  const card = (i, kindLabel, pillClass) => `
    <a class="shelf-card rise" href="${i.href}">
      <div class="sc-top">
        <span class="sc-idx num">${i.num}</span>
        ${Date.parse(i.date || 0) === newestDate ? '<span class="tagpill y">NEW</span>' : `<span class="tagpill ${pillClass}">${kindLabel}</span>`}
      </div>
      <h3>${i.title}</h3>
      <p>${i.desc}</p>
      <span class="sc-go">打開<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></span>
    </a>`;

  const toolGrid = document.getElementById('toolGrid');
  if (toolGrid) toolGrid.innerHTML = tools.map(i => card(i, '可用', '')).join('');

  const guideGrid = document.getElementById('guideGrid');
  if (guideGrid) guideGrid.innerHTML = guides.map(i => card(i, '完整版', 'y')).join('');

  const radarGrid = document.getElementById('radarGrid');
  if (radarGrid) radarGrid.innerHTML = radars.map(i => card(i, '懶人包', '')).join('');

  const nextList = document.getElementById('nextList');
  if (nextList) {
    nextList.innerHTML = nexts.map(i =>
      `<li><span class="n-kind">${i.kind === 'tool' ? '工具' : i.kind === 'radar' ? 'RADAR' : '做法'}</span>${i.title}</li>`).join('');
  }

  // 統計數字
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  set('statTools', tools.length);
  set('statGuides', guides.length);
})();
