(() => {
  const status = document.getElementById('copy-status');
  let statusTimer;
  function announce(message) {
    clearTimeout(statusTimer);
    status.textContent = message;
    statusTimer = setTimeout(() => { status.textContent = ''; }, 5000);
  }
  function legacyCopy(text) {
    const field = document.createElement('textarea');
    field.value = text;
    field.setAttribute('readonly', '');
    field.style.cssText = 'position:fixed;top:0;left:0;opacity:0;pointer-events:none;font-size:16px;';
    document.body.append(field);
    field.select();
    field.setSelectionRange(0, field.value.length);
    let copied = false;
    try { copied = document.execCommand('copy'); } finally { field.remove(); }
    return copied;
  }
  document.querySelectorAll('[data-copy]').forEach(button => {
    button.addEventListener('click', async () => {
      const source = document.getElementById(button.dataset.copy);
      if (!source) return;
      const text = source.textContent.trim();
      let copied = false;
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text);
          copied = true;
        }
      } catch { /* Some in-app browsers deny clipboard access. */ }
      if (!copied) {
        try { copied = legacyCopy(text); } catch { copied = false; }
      }
      if (copied) {
        button.focus({ preventScroll: true });
        announce('已複製！回到 Codex 貼上即可。');
      } else {
        const range = document.createRange();
        range.selectNodeContents(source);
        const selection = window.getSelection();
        if (selection) { selection.removeAllRanges(); selection.addRange(range); }
        source.focus({ preventScroll: true });
        announce('瀏覽器未允許自動複製，請長按選取的文字複製，或下載全部提示詞。');
      }
    });
  });
})();
