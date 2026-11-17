/* ============================================================
   黑牛工具 · 站台內容清單
   ─────────────────────────────────────────────
   每週新增工具 / 做法，只要在最上面加一筆就好，
   首頁的卡片與開發計畫會自動更新。

   欄位說明：
     kind  : 'tool'（工具）/ 'guide'（完整做法）/ 'radar'（RADAR 懶人包）
     title : 標題
     desc  : 一句話說明
     href  : 連結（相對路徑）
     next  : true = 顯示在「接下來做什麼」、不出現卡片
   ============================================================ */

const HEINIU_ITEMS = [
  {
    kind: 'guide',
    title: 'Claude 從零到高手 · 完整攻略',
    desc: '99% 的人只把 Claude 當聊天機器人。工作和生活都用得上，11 章照做就好：記憶、專案、Skills、連接工具、排程任務，每章都有可以直接複製的指令。',
    href: './claude-zerotohero/',
  },

  {
    kind: 'guide',
    title: '黑牛 AI 剪輯 · 跟 AI 聊天剪影片',
    desc: '免費 Claude 技能：丟原始素材 → 看分鏡 → 一句話修改，拿到有字幕、封面和留言結尾的短影音。附三步安裝。',
    href: './edit/',
  },
  {
    kind: 'guide',
    title: '黑牛茶鋪 · ASTRA 實作',
    desc: '先玩 60 秒接客挑戰，再複製四階段提示詞，做一間自己的珍奶小店。',
    href: './astra/',
  },
  {
    kind: 'tool',
    title: 'AI 整理資料夾 · File Universe',
    desc: '用 Claude 依內容整理資料夾，再到瀏覽器查看分類結果。也可以直接載入範例。',
    href: './sort/',
  },
  {
    kind: 'tool',
    title: '薪水實拿計算機',
    desc: '輸入月薪 → 產生你的薪資明細表：扣完勞健保實拿多少，還有老闆偷偷幫你付的錢。',
    href: './salary/',
  },
  {
    kind: 'tool',
    title: '錢去哪了 · AI 花費健檢',
    desc: '貼上信用卡明細，用關鍵字在瀏覽器分類，找出花費最多的項目。',
    href: './spending/',
  },
  {
    kind: 'tool',
    title: 'PDF 只取需要的頁',
    desc: '整份 PDF 太肥？拖進來、選你要的頁，直接抽出純文字複製給 AI——省 token、答更準。檔案不上傳，全在你的瀏覽器裡跑。',
    href: './pdf/',
  },
  {
    kind: 'guide',
    title: '省 token 三招',
    desc: '3 個超浪費 AI 額度的習慣，跟正確做法：只給需要的部分、開新對話、需要才開功能。',
    href: './token/',
  },
  {
    kind: 'radar',
    title: '值得搞懂的 3 個 AI 專案',
    desc: '影片裡三個專案的連結，加上我判斷「值不值得看」的三個問題（三問）。不是又一個聊天功能。',
    href: './radar/ai-projects/',
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
  const icons = {
    tool: 'M3 6h7l2 2h9v11H3z',
    guide: 'M3 5h7l2 2 2-2h7v14h-7l-2 2-2-2H3zM12 7v14',
    radar: 'M21 12a9 9 0 1 1-9-9M17 12a5 5 0 1 1-5-5m0 5 8-8',
  };
  const card = item => `
    <a class="shelf-card" href="${item.href}">
      <span class="card-mark" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="${icons[item.kind]}"/></svg>
      </span>
      <h3>${item.title}</h3>
      <p>${item.desc}</p>
      <span class="sc-go">${item.kind === 'tool' ? '開啟工具' : '開啟內容'} <span aria-hidden="true">↗</span></span>
    </a>`;

  for (const [id, items] of [['toolGrid', tools], ['guideGrid', guides], ['radarGrid', radars]]) {
    const grid = document.getElementById(id);
    if (grid) grid.innerHTML = items.map(card).join('');
  }

  const nextList = document.getElementById('nextList');
  if (nextList) {
    nextList.innerHTML = nexts.map(i =>
      `<li><span class="n-kind">${i.kind === 'tool' ? '工具' : i.kind === 'radar' ? 'RADAR' : '做法'}</span>${i.title}</li>`).join('');
  }

})();
