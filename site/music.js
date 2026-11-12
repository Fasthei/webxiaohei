(() => {
  'use strict';
  if (document.getElementById('site-music')) return;
  const zh = document.documentElement.lang.startsWith('zh');
  const words = zh ? {play:'播放音乐',pause:'暂停音乐',loading:'正在加载音乐',error:'音乐加载失败，点击重试'} : {play:'Play music',pause:'Pause music',loading:'Loading music',error:'Music unavailable — retry'};
  const key = 'tr-audio-enabled';
  const widget = document.createElement('aside');
  widget.id = 'site-music';
  widget.setAttribute('aria-label', zh ? '背景音乐' : 'Background music');
  const bar = document.createElement('div');
  bar.className = 'music-bar';
  const button = document.createElement('button');
  button.type = 'button';
  button.title = 'Restar sutri';
  const status = document.createElement('span');
  status.className = 'music-status';
  status.setAttribute('role','status');
  const audio = document.createElement('audio');
  audio.src = '/audio/restar-sutri.mp3';
  audio.loop = true;
  audio.preload = 'auto';
  audio.volume = 0.35;
  audio.setAttribute('playsinline','');
  bar.append(button,status);
  widget.append(bar,audio);
  // Keep a real layout slot on phones; desktop positioning remains floating.
  const header = document.querySelector('.site-header');
  if (header) header.insertAdjacentElement('afterend', widget);
  else document.body.prepend(widget);
  function show(playing, message = '') {
    button.textContent = `♫ ${playing ? words.pause : words.play}`;
    button.setAttribute('aria-label', playing ? words.pause : words.play);
    button.setAttribute('aria-pressed', String(playing));
    status.textContent = message;
  }
  function save(value) { try { localStorage.setItem(key,String(value)); } catch (_) {} }
  async function play() {
    show(false,words.loading);
    try { await audio.play(); }
    catch (error) { show(false,error.name === 'NotAllowedError' ? '' : words.error); }
  }
  audio.addEventListener('playing', () => show(true));
  audio.addEventListener('pause', () => show(false));
  audio.addEventListener('error', () => show(false,words.error));
  button.addEventListener('click', () => {
    if (!audio.paused) { audio.pause(); save(false); }
    else { save(true); if (audio.error) audio.load(); play(); }
  });
  show(false);
  let enabled = true;
  try { enabled = localStorage.getItem(key) !== 'false'; } catch (_) {}
  if (enabled) play();
})();
