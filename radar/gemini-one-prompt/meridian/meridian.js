'use strict';

const destinations = [
  {
    code: 'KIX',
    bearing: 70,
    zh: ['京都', '日本', ['一雙適合走路的鞋', '一本小筆記本', '一個可折疊購物袋']],
    en: ['Kyoto', 'Japan', ['Comfortable walking shoes', 'A pocket notebook', 'A foldable shopping bag']]
  },
  {
    code: 'RAK',
    bearing: 290,
    zh: ['馬拉喀什', '摩洛哥', ['一條輕薄圍巾', '一瓶水', '一台隨身相機']],
    en: ['Marrakech', 'Morocco', ['A lightweight scarf', 'A water bottle', 'A pocket camera']]
  },
  {
    code: 'FTE',
    bearing: 215,
    zh: ['巴塔哥尼亞', '阿根廷與智利', ['一件防風外套', '一個保溫瓶', '一本平裝小說']],
    en: ['Patagonia', 'Argentina & Chile', ['A windproof jacket', 'An insulated bottle', 'A paperback novel']]
  },
  {
    code: 'LKN',
    bearing: 10,
    zh: ['羅弗敦群島', '挪威', ['一件防水外套', '一盞頭燈', '一雙保暖襪']],
    en: ['Lofoten Islands', 'Norway', ['A waterproof jacket', 'A headlamp', 'A pair of warm socks']]
  }
];

const labels = {
  zh: { spin: '轉動指南針', again: '再轉一次', spinning: '抽選中……', arrival: '下一站是' },
  en: { spin: 'Spin the compass', again: 'Spin again', spinning: 'Picking a destination…', arrival: 'Next stop' }
};

const button = document.getElementById('spin');
const buttonLabel = document.getElementById('spin-label');
const needle = document.getElementById('needle');
const destination = document.getElementById('destination');
const destinationCode = document.getElementById('destination-code');
const destinationName = document.getElementById('destination-name');
const destinationRegion = document.getElementById('destination-region');
const packingList = document.getElementById('packing-list');
const placeholder = document.getElementById('placeholder');
const announcement = document.getElementById('announcement');
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');

let currentDestination;
let bearing = 0;
let spinning = false;

function currentLanguage() {
  return document.documentElement.lang === 'en' ? 'en' : 'zh';
}

function render() {
  const lang = currentLanguage();
  const copy = labels[lang];
  buttonLabel.textContent = spinning ? copy.spinning : currentDestination ? copy.again : copy.spin;
  if (!currentDestination) return;

  const [name, region, packing] = currentDestination[lang];
  destinationCode.textContent = currentDestination.code;
  destinationName.textContent = name;
  destinationRegion.textContent = region;
  packingList.replaceChildren(...packing.map(item => {
    const entry = document.createElement('li');
    entry.textContent = item;
    return entry;
  }));
  placeholder.hidden = true;
  destination.hidden = false;
}

button.addEventListener('click', async () => {
  if (spinning) return;
  spinning = true;
  button.setAttribute('aria-disabled', 'true');
  render();

  const choices = destinations.filter(place => place !== currentDestination);
  const next = choices[Math.floor(Math.random() * choices.length)];
  if (!reducedMotion.matches) {
    const turns = 720 + (next.bearing - bearing + 360) % 360;
    const animation = needle.animate([
      { transform: `rotate(${bearing}deg)` },
      { transform: `rotate(${bearing + turns}deg)` }
    ], { duration: 720, easing: 'cubic-bezier(.15, .6, .2, 1)' });
    await animation.finished;
  }

  bearing = next.bearing;
  needle.style.transform = `rotate(${bearing}deg)`;
  currentDestination = next;
  spinning = false;
  button.removeAttribute('aria-disabled');
  render();

  const lang = currentLanguage();
  announcement.textContent = `${labels[lang].arrival} ${next[lang][0]}`;
});

document.addEventListener('heiniu:languagechange', render);
button.disabled = false;
render();
