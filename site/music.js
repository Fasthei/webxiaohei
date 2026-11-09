/* Official Bilibili embed; never infer playback state across the iframe boundary. */
(() => {
  'use strict';
  if (document.getElementById('site-music')) return;
  const zh = document.documentElement.lang.startsWith('zh');
  const labels = zh ? {
    music: '背景音乐', stop: '关闭音乐', start: '开启音乐', retry: '播放音乐',
  } : {
    music: 'Background music', stop: 'Turn music off', start: 'Turn music on', retry: 'Play music',
  };
  const key = 'tr-music-enabled';
  let enabled = true;
  try { enabled = localStorage.getItem(key) !== 'false'; } catch (_) {}
  const widget = document.createElement('aside');
  widget.id = 'site-music';
  widget.setAttribute('aria-label', labels.music);
  widget.innerHTML = `<div class="music-bar"><button type="button" class="music-retry" title="Restar sutri">♫ ${labels.retry}</button><button type="button" class="music-toggle"></button></div><div class="music-frame" aria-hidden="true" inert></div>`;
  document.body.append(widget);
  const toggle = widget.querySelector('.music-toggle');
  const retry = widget.querySelector('.music-retry');
  const frameHost = widget.querySelector('.music-frame');
  function mount() {
    frameHost.replaceChildren();
    if (enabled) {
      const frame = document.createElement('iframe');
      frame.title = 'Restar sutri — Bilibili';
      frame.allow = 'autoplay';
      frame.tabIndex = -1;
      frame.src = 'https://player.bilibili.com/player.html?bvid=BV1F5qjBBESv&autoplay=1&muted=0&danmaku=0';
      frameHost.append(frame);
    }
    toggle.textContent = enabled ? labels.stop : labels.start;
    toggle.setAttribute('aria-pressed', String(enabled));
  }
  toggle.addEventListener('click', () => {
    enabled = !enabled;
    try { localStorage.setItem(key, String(enabled)); } catch (_) {}
    mount();

  });
  retry.addEventListener('click', () => {
    enabled = true;
    try { localStorage.setItem(key, 'true'); } catch (_) {}
    mount();
  });
  mount();

})();
