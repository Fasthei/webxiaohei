/* Official Bilibili embed; never infer playback state across the iframe boundary. */
(() => {
  'use strict';
  if (document.getElementById('site-music')) return;
  const zh = document.documentElement.lang.startsWith('zh');
  const labels = zh ? {
    music: '音乐', stop: '关闭音乐', start: '开启音乐', collapse: '收起', expand: '展开播放器',
    hint: '若未自动出声，请点击播放器中的播放或音量按钮。', source: '在哔哩哔哩打开',
  } : {
    music: 'Music', stop: 'Turn music off', start: 'Turn music on', collapse: 'Minimize', expand: 'Open player',
    hint: 'If sound does not start, use the play or volume button in the player.', source: 'Open on Bilibili',
  };
  const key = 'tr-music-enabled';
  let enabled = true;
  try { enabled = localStorage.getItem(key) !== 'false'; } catch (_) {}
  const widget = document.createElement('aside');
  widget.id = 'site-music';
  widget.setAttribute('aria-label', labels.music);
  widget.innerHTML = `<div class="music-bar"><span>♫ Restar sutri</span><button type="button" class="music-toggle"></button><button type="button" class="music-expand" aria-controls="music-panel" aria-expanded="true">${labels.collapse}</button></div><div id="music-panel"><div class="music-frame"></div><p>${labels.hint}</p><a href="https://www.bilibili.com/video/BV1F5qjBBESv/" target="_blank" rel="noopener noreferrer">${labels.source} ↗</a></div>`;
  document.body.append(widget);
  const toggle = widget.querySelector('.music-toggle');
  const expand = widget.querySelector('.music-expand');
  const panel = widget.querySelector('#music-panel');
  const frameHost = widget.querySelector('.music-frame');
  function setExpanded(value) {
    panel.hidden = !value;
    expand.setAttribute('aria-expanded', String(value));
    expand.textContent = value ? labels.collapse : labels.expand;
  }
  function mount() {
    frameHost.replaceChildren();
    if (enabled) {
      const frame = document.createElement('iframe');
      frame.title = 'Restar sutri — Bilibili';
      frame.allow = 'autoplay; fullscreen; picture-in-picture';
      frame.allowFullscreen = true;
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
    setExpanded(enabled);
  });
  expand.addEventListener('click', () => setExpanded(panel.hidden));
  mount();
  setExpanded(enabled);
})();
