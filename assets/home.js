const locales = document.querySelectorAll('[data-locale]');
const selection = document.querySelector('#source-file');
function selectRecord(index) {
  const record = records[index];
  const languageIndex = document.documentElement.lang === 'en' ? 1 : 0;
  for (const element of document.querySelectorAll('[data-field]')) {
    element.textContent = record[element.dataset.field][languageIndex];
  }
}
function selectLanguage(language) {
  document.documentElement.lang = language;
  document.title = language === 'en' ? 'HEINIU · Tools, portfolio and lessons' : 'HEINIU 黑牛 · 工具、作品與教學';
  for (const button of locales) {
    button.setAttribute('aria-pressed', String(button.dataset.locale === language));
  }
  const code = language === 'en' ? 'en' : 'zh';
  try { localStorage.setItem('heiniu-language', code); } catch {}
  for (const link of document.querySelectorAll('a[href]')) {
    const raw = link.getAttribute('href');
    if (raw.startsWith('#')) continue;
    const destination = new URL(raw, location.href);
    if (destination.origin !== location.origin || !destination.pathname.endsWith('/')) continue;
    if (/\/claude-zerotohero\/(?:en\/)?$/.test(destination.pathname)) {
      destination.pathname = destination.pathname.replace(/(?:en\/)?$/, code === 'en' ? 'en/' : '');
    }
    destination.searchParams.set('lang', code);
    link.href = destination.href;
  }
  selectRecord(selection.selectedIndex);
}
for (const button of locales) {
  button.addEventListener('click', () => {
    const language = button.dataset.locale;
    const destination = new URL(location.href);
    destination.searchParams.set('lang', language === 'en' ? 'en' : 'zh');
    history.replaceState(null, '', destination);
    selectLanguage(language);
  });
}
selection.addEventListener('change', () => selectRecord(selection.selectedIndex));
const requestedLanguage = new URLSearchParams(location.search).get('lang');
let previousLanguage;
try { previousLanguage = localStorage.getItem('heiniu-language'); } catch {}
selectLanguage((requestedLanguage || previousLanguage) === 'en' ? 'en' : 'zh-Hant');
