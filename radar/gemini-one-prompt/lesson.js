const copyPrompt = document.getElementById('copy-prompt');
const copyStatus = document.getElementById('copy-status');

if (navigator.clipboard?.writeText) {
  copyPrompt.hidden = false;
  copyPrompt.addEventListener('click', async () => {
    const english = document.documentElement.lang === 'en';
    const prompt = document.querySelector(english ? 'pre[data-lang-en]' : 'pre[data-lang-zh]');
    try {
      await navigator.clipboard.writeText(prompt.textContent);
      copyStatus.textContent = english ? 'Copied' : '已複製';
    } catch {
      copyStatus.textContent = english ? 'Select the prompt text to copy it.' : '請選取提示詞文字後複製。';
    }
  });
  document.addEventListener('heiniu:languagechange', () => {
    copyStatus.textContent = '';
  });
}
