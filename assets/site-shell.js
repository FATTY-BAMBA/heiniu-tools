/* Use the existing route-specific translator. Carry the active language across
   visitor-facing routes without rewriting downloads, citations or local anchors. */
function syncSiteLinks() {
  const lang = document.documentElement.lang === 'en' ? 'en' : 'zh';
  for (const link of document.querySelectorAll('a[href]')) {
    const raw = link.getAttribute('href');
    if (raw.startsWith('#')) continue;
    const target = new URL(raw, location.href);
    if (target.origin !== location.origin || !target.pathname.endsWith('/')) continue;
    if (/\/claude-zerotohero\/(?:en\/)?$/.test(target.pathname)) {
      target.pathname = target.pathname.replace(/(?:en\/)?$/, lang === 'en' ? 'en/' : '');
    }
    target.searchParams.set('lang', lang);
    link.href = target.href;
  }
}
const nativeSort = document.body.classList.contains('file-universe-page');
for (const button of document.querySelectorAll('.shell-languages button')) {
  button.addEventListener('click', () => {
    const lang = button.dataset.langChoice;
    if (!nativeSort) window.HeiniuI18n?.setLanguage(lang);
    // The course translator handles navigation between its two authored pages.
    if (!location.pathname.includes('/claude-zerotohero/')) {
      const url = new URL(location.href);
      url.searchParams.set('lang', lang);
      history.replaceState(null, '', url);
    }
    syncSiteLinks();
  });
}
syncSiteLinks();
new MutationObserver(syncSiteLinks).observe(document.documentElement, {attributes:true,attributeFilter:['lang']});
