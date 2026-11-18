const locales = document.querySelectorAll('[data-locale]');
const selection = document.querySelector('#source-file');
function selectRecord(index) {
  const record = records[index];
  if (!record) return;
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
  if (selection) selectRecord(selection.selectedIndex);
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
if (selection) selection.addEventListener('change', () => selectRecord(selection.selectedIndex));
const requestedLanguage = new URLSearchParams(location.search).get('lang');
let previousLanguage;
try { previousLanguage = localStorage.getItem('heiniu-language'); } catch {}
selectLanguage((requestedLanguage || previousLanguage) === 'en' ? 'en' : 'zh-Hant');

/* Reflect the section currently in view in primary navigation for keyboard and
   assistive-technology users. Native anchor navigation remains unchanged. */
const sectionLinks = [...document.querySelectorAll('.shell-nav a[href^="#"]')]
  .map(link => ({ link, section: document.getElementById(link.getAttribute('href').slice(1)) }))
  .filter(item => item.section);
if (sectionLinks.length && 'IntersectionObserver' in window) {
  const visible = new Map();
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (entry.isIntersecting) visible.set(entry.target.id, entry.boundingClientRect.top);
      else visible.delete(entry.target.id);
    }
    let active = [...visible].sort((a, b) => Math.abs(a[1]) - Math.abs(b[1]))[0]?.[0];
    if (!active) return;
    for (const { link, section } of sectionLinks) {
      if (section.id === active) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }
  }, { rootMargin: '-18% 0px -58% 0px', threshold: 0 });
  sectionLinks.forEach(({ section }) => observer.observe(section));
}
